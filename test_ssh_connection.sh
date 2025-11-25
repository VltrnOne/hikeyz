#!/bin/bash
# Test SSH connection to SiteGround - Use this to verify your SSH key works before adding to GitHub

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}==================================="
echo "SiteGround SSH Connection Test"
echo -e "===================================${NC}\n"

# SiteGround Details
SG_HOST="gcam1145.siteground.biz"
SG_USER="u2296-bzl1wdrk3lgl"
SG_PORT="18765"
KEY_PATH="$HOME/sg_key_new"

# Check if key exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}❌ SSH key not found at: $KEY_PATH${NC}"
    echo ""
    echo "Please provide the path to your SSH private key:"
    read -p "Key path: " KEY_PATH
    if [ ! -f "$KEY_PATH" ]; then
        echo -e "${RED}❌ Key file not found: $KEY_PATH${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}Using SSH key: $KEY_PATH${NC}\n"

# Check key format
echo -e "${YELLOW}✓ Checking key format...${NC}"
if grep -q "BEGIN.*PRIVATE KEY" "$KEY_PATH"; then
    echo -e "${GREEN}  ✓ Key format looks correct${NC}"
    head -1 "$KEY_PATH"
    tail -1 "$KEY_PATH"
else
    echo -e "${RED}  ✗ Key format error - missing BEGIN/END markers${NC}"
    exit 1
fi

# Check permissions
echo -e "\n${YELLOW}✓ Checking key permissions...${NC}"
chmod 600 "$KEY_PATH"
if [ $(stat -f %A "$KEY_PATH" 2>/dev/null || stat -c %a "$KEY_PATH" 2>/dev/null) = "600" ]; then
    echo -e "${GREEN}  ✓ Permissions correct (600)${NC}"
else
    echo -e "${YELLOW}  ⚠  Permissions may need adjustment${NC}"
fi

# Test SSH connection
echo -e "\n${YELLOW}✓ Testing SSH connection...${NC}"
echo "Connecting to: $SG_USER@$SG_HOST:$SG_PORT"
echo ""

if ssh -i "$KEY_PATH" -p $SG_PORT \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    $SG_USER@$SG_HOST "echo '✅ SSH connection successful!'" 2>&1; then
    
    echo -e "\n${GREEN}==================================="
    echo "✅ SSH CONNECTION SUCCESSFUL!"
    echo -e "===================================${NC}\n"
    echo "Your SSH key is working correctly."
    echo ""
    echo "Next steps:"
    echo "1. Copy your SSH key content:"
    echo "   cat $KEY_PATH"
    echo ""
    echo "2. Add to GitHub Secrets:"
    echo "   - Go to: GitHub Repo → Settings → Secrets → Actions"
    echo "   - Update: SITEGROUND_SSH_KEY"
    echo "   - Paste the COMPLETE key (all lines)"
    echo ""
    echo "3. Re-run GitHub Actions workflow"
    
else
    echo -e "\n${RED}==================================="
    echo "❌ SSH CONNECTION FAILED"
    echo -e "===================================${NC}\n"
    
    echo "Possible causes:"
    echo ""
    echo "1. SSH key not authorized on SiteGround:"
    echo "   - Log into SiteGround cPanel"
    echo "   - Go to: Site Tools → Dev → SSH Keys Manager"
    echo "   - Find your key and click 'Authorize'"
    echo ""
    echo "2. Wrong SSH credentials:"
    echo "   - Host: $SG_HOST"
    echo "   - User: $SG_USER"
    echo "   - Port: $SG_PORT"
    echo ""
    echo "3. SSH not enabled on SiteGround account"
    echo "   - Contact SiteGround support to enable SSH"
    echo ""
    echo "4. Key has passphrase:"
    echo "   - GitHub Actions cannot use passphrase-protected keys"
    echo "   - Generate a new key without passphrase in SiteGround cPanel"
    echo ""
    
    exit 1
fi

