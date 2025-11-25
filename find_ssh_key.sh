#!/bin/bash
# Helper script to find and set up SSH key for SiteGround

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================="
echo "SSH Key Finder for SiteGround"
echo -e "=========================================${NC}\n"

TARGET_KEY="$HOME/sg_key"

# Check if key already exists at target location
if [ -f "$TARGET_KEY" ]; then
    echo -e "${GREEN}✓ SSH key already exists at: $TARGET_KEY${NC}"
    ls -lh "$TARGET_KEY"
    echo ""
    echo "You're all set! Run the deployment script:"
    echo "  cd /Users/Morpheous/vltrndataroom/hitbot-agency"
    echo "  ./setup_ssh_and_deploy.sh"
    exit 0
fi

echo -e "${YELLOW}Looking for potential SSH keys...${NC}\n"

# Find potential SSH keys in Downloads
KEYS_FOUND=$(find ~/Downloads -name "*.key" -o -name "id_rsa" -o -name "id_ed25519" 2>/dev/null | grep -v ".pub")

if [ -z "$KEYS_FOUND" ]; then
    echo -e "${YELLOW}No SSH keys found in ~/Downloads${NC}"
    echo ""
    echo "To get your SSH key from SiteGround:"
    echo ""
    echo "1. Log into SiteGround cPanel"
    echo "2. Go to: Advanced → SSH Keys Manager"
    echo "3. If you don't have a key:"
    echo "   - Click 'Generate a New Key'"
    echo "   - Enter a name (e.g., 'hikeyz')"
    echo "   - Optional: Set a passphrase"
    echo "   - Click 'Generate'"
    echo ""
    echo "4. Download the PRIVATE key:"
    echo "   - Find your key in the list"
    echo "   - Click 'View/Download'"
    echo "   - Click 'Download Private Key'"
    echo "   - Save to Downloads folder"
    echo ""
    echo "5. Authorize the key (if not already):"
    echo "   - Click 'Manage' next to your key"
    echo "   - Click 'Authorize'"
    echo ""
    echo "After downloading, run this script again!"
    exit 0
fi

echo "Found potential SSH keys:"
echo ""

# List found keys with numbers
i=1
declare -a key_array
while IFS= read -r key; do
    echo "  $i) $key"
    key_array[$i]="$key"
    i=$((i+1))
done <<< "$KEYS_FOUND"

echo ""
echo -e "${BLUE}Which key would you like to use for SiteGround?${NC}"
echo "Enter the number (or 'q' to quit): "
read -r choice

if [ "$choice" = "q" ]; then
    exit 0
fi

# Validate choice
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -ge "$i" ]; then
    echo -e "${YELLOW}Invalid choice${NC}"
    exit 1
fi

SELECTED_KEY="${key_array[$choice]}"

echo ""
echo -e "${GREEN}Selected: $SELECTED_KEY${NC}"
echo ""
echo "Copying to: $TARGET_KEY"

# Copy the key
cp "$SELECTED_KEY" "$TARGET_KEY"
chmod 600 "$TARGET_KEY"

echo -e "${GREEN}✓ SSH key configured!${NC}"
echo ""
echo "Next steps:"
echo "  cd /Users/Morpheous/vltrndataroom/hitbot-agency"
echo "  ./setup_ssh_and_deploy.sh"
