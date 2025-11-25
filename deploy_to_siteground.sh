#!/bin/bash
# SiteGround Deployment Script for hikeyz.com

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================="
echo "hikeyz.com SiteGround Deployment"
echo -e "===================================${NC}\n"

# SiteGround SSH Details
SG_HOST="gcam1145.siteground.biz"
SG_USER="u2296-bzl1wdrk3lgl"
SG_PORT="18765"

# Remote directories
REMOTE_APP_DIR="~/hikeyz"
REMOTE_VENV_DIR="~/virtualenv/hikeyz"

echo -e "${YELLOW}Step 1: Testing SSH Connection...${NC}"
ssh -p $SG_PORT $SG_USER@$SG_HOST "echo 'SSH connection successful!'"

if [ $? -ne 0 ]; then
    echo -e "${RED}SSH connection failed. Please check your credentials.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 2: Creating directory structure...${NC}"
ssh -p $SG_PORT $SG_USER@$SG_HOST << 'ENDSSH'
    mkdir -p ~/hikeyz/downloads
    mkdir -p ~/hikeyz/logs
    mkdir -p ~/virtualenv
    echo "Directories created"
ENDSSH

echo -e "\n${YELLOW}Step 3: Cloning repository from GitHub...${NC}"
ssh -p $SG_PORT $SG_USER@$SG_HOST << 'ENDSSH'
    cd ~
    if [ -d "hikeyz/.git" ]; then
        echo "Repository exists, pulling latest changes..."
        cd hikeyz
        git pull origin main
    else
        echo "Cloning repository..."
        git clone https://github.com/VltrnOne/hikeyz.git
    fi
ENDSSH

echo -e "\n${YELLOW}Step 4: Setting up Python virtual environment...${NC}"
ssh -p $SG_PORT $SG_USER@$SG_HOST << 'ENDSSH'
    cd ~/hikeyz
    python3 -m venv ~/virtualenv/hikeyz
    source ~/virtualenv/hikeyz/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Python packages installed"
ENDSSH

echo -e "\n${YELLOW}Step 5: Configuration reminder...${NC}"
echo -e "${RED}IMPORTANT: You need to manually configure the following in SiteGround cPanel:${NC}"
echo ""
echo "1. Python App Setup:"
echo "   - Go to: cPanel > Setup Python App"
echo "   - Python version: 3.9+"
echo "   - Application root: /home/$SG_USER/hikeyz"
echo "   - Application URL: hikeyz.com"
echo "   - Application startup file: api/app.py"
echo "   - Application Entry point: app"
echo ""
echo "2. Environment Variables (Add in cPanel > Python App > Environment Variables):"
echo "   STRIPE_SECRET_KEY=your_stripe_secret_key"
echo "   STRIPE_WEBHOOK_SECRET=your_webhook_secret"
echo "   STRIPE_QUICK_PRICE_ID=your_quick_price_id"
echo "   STRIPE_PRO_PRICE_ID=your_pro_price_id"
echo "   DB_HOST=localhost"
echo "   DB_USER=your_db_user"
echo "   DB_PASSWORD=your_db_password"
echo "   DB_NAME=hikeyz_db"
echo "   APP_BASE_URL=https://hikeyz.com"
echo ""
echo "3. MySQL Database:"
echo "   - Go to: cPanel > MySQL Databases"
echo "   - Create database: hikeyz_db"
echo "   - Create user with strong password"
echo "   - Grant ALL privileges"
echo "   - Import schema from: database/schema.sql"
echo ""
echo "4. SSL Certificate:"
echo "   - Go to: cPanel > SSL/TLS Status"
echo "   - Enable AutoSSL for hikeyz.com"
echo ""

echo -e "\n${GREEN}Deployment script completed!${NC}"
echo -e "${YELLOW}Next: Complete manual configuration steps above in cPanel${NC}"
