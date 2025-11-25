#!/bin/bash
# Complete SSH Setup and Deployment for hikeyz.com on SiteGround

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================="
echo "hikeyz.com - SSH Setup & Deployment"
echo -e "=========================================${NC}\n"

# SiteGround Details
SG_HOST="gcam1145.siteground.biz"
SG_USER="u2296-bzl1wdrk3lgl"
SG_PORT="18765"
KEY_PATH="$HOME/sg_key_new"

# Step 1: Check if SSH key exists
echo -e "${YELLOW}Step 1: Checking for SSH key...${NC}"

if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}SSH key not found at: $KEY_PATH${NC}"
    echo ""
    echo "To get your SSH key from SiteGround:"
    echo "1. Log into SiteGround cPanel"
    echo "2. Go to: Advanced → SSH Keys Manager"
    echo "3. Generate a new key pair (if you haven't)"
    echo "4. Download the private key"
    echo "5. Save it as: $KEY_PATH"
    echo ""
    echo "Or if you already have the key file, move it:"
    echo "  mv /path/to/your/key $KEY_PATH"
    echo ""
    echo -e "${YELLOW}After saving the key, run this script again.${NC}"
    exit 1
fi

# Step 2: Set proper permissions
echo -e "${GREEN}✓ SSH key found${NC}"
echo -e "${YELLOW}Step 2: Setting proper permissions...${NC}"
chmod 600 "$KEY_PATH"
echo -e "${GREEN}✓ Permissions set to 600${NC}"

# Step 3: Test SSH connection
echo -e "\n${YELLOW}Step 3: Testing SSH connection...${NC}"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$KEY_PATH" -p $SG_PORT $SG_USER@$SG_HOST "echo 'SSH connection successful!'" 2>&1

if [ $? -ne 0 ]; then
    echo -e "\n${RED}SSH connection failed!${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Verify the key file is the PRIVATE key (not .pub)"
    echo "2. Check that the key is authorized in SiteGround cPanel → SSH Keys Manager"
    echo "3. Verify your internet connection"
    echo "4. Try connecting manually:"
    echo "   ssh -i $KEY_PATH -p $SG_PORT $SG_USER@$SG_HOST"
    exit 1
fi

echo -e "${GREEN}✓ SSH connection working${NC}"

# Step 4: Create directory structure
echo -e "\n${YELLOW}Step 4: Creating directory structure on server...${NC}"
ssh -i "$KEY_PATH" -p $SG_PORT $SG_USER@$SG_HOST << 'ENDSSH'
    mkdir -p ~/hikeyz/downloads
    mkdir -p ~/hikeyz/logs
    mkdir -p ~/virtualenv
    echo "✓ Directories created"
ENDSSH

# Step 5: Clone/update repository
echo -e "\n${YELLOW}Step 5: Setting up repository...${NC}"
ssh -i "$KEY_PATH" -p $SG_PORT $SG_USER@$SG_HOST << 'ENDSSH'
    cd ~
    if [ -d "hikeyz/.git" ]; then
        echo "Repository exists, pulling latest changes..."
        cd hikeyz
        git pull origin main
    else
        echo "Cloning repository..."
        git clone https://github.com/VltrnOne/hikeyz.git
    fi
    echo "✓ Repository ready"
ENDSSH

# Step 6: Setup Python environment
echo -e "\n${YELLOW}Step 6: Setting up Python virtual environment...${NC}"
ssh -i "$KEY_PATH" -p $SG_PORT $SG_USER@$SG_HOST << 'ENDSSH'
    cd ~/hikeyz

    # Create or update virtual environment
    if [ ! -d "~/virtualenv/hikeyz" ]; then
        python3 -m venv ~/virtualenv/hikeyz
    fi

    # Activate and install dependencies
    source ~/virtualenv/hikeyz/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    echo "✓ Python environment ready"
ENDSSH

# Step 7: Configuration reminder
echo -e "\n${GREEN}========================================="
echo "DEPLOYMENT SUCCESSFUL!"
echo -e "=========================================${NC}\n"

echo -e "${YELLOW}NEXT STEPS - Manual Configuration Required:${NC}\n"

echo "1. Setup Python Application in cPanel:"
echo "   • Go to: cPanel → Setup Python App"
echo "   • Python version: 3.9+"
echo "   • Application root: /home/$SG_USER/hikeyz"
echo "   • Application URL: hikeyz.com"
echo "   • Application startup file: api/app.py"
echo "   • Application Entry point: app"
echo ""

echo "2. Add Environment Variables in cPanel:"
echo "   • Go to: Python App → Environment Variables"
echo "   Required variables:"
echo "     - STRIPE_SECRET_KEY"
echo "     - STRIPE_WEBHOOK_SECRET"
echo "     - STRIPE_QUICK_PRICE_ID"
echo "     - STRIPE_PRO_PRICE_ID"
echo "     - DB_HOST=localhost"
echo "     - DB_USER=your_db_user"
echo "     - DB_PASSWORD=your_db_password"
echo "     - DB_NAME=hikeyz_db"
echo "     - APP_BASE_URL=https://hikeyz.com"
echo ""

echo "3. Setup MySQL Database:"
echo "   • Go to: cPanel → MySQL Databases"
echo "   • Create database: hikeyz_db"
echo "   • Create user with strong password"
echo "   • Grant ALL privileges"
echo "   • Import: database/schema.sql"
echo ""

echo "4. Enable SSL:"
echo "   • Go to: cPanel → SSL/TLS Status"
echo "   • Enable AutoSSL for hikeyz.com"
echo ""

echo -e "${GREEN}Code deployed successfully!${NC}"
echo -e "${YELLOW}Complete the manual steps above to go live.${NC}\n"
