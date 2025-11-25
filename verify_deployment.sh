#!/bin/bash
# Verification script for GitHub Actions deployment setup

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}==================================="
echo "GitHub Actions Deployment Verification"
echo -e "===================================${NC}\n"

# Check 1: Workflow file exists
echo -e "${YELLOW}✓ Checking workflow file...${NC}"
if [ -f ".github/workflows/deploy-siteground.yml" ]; then
    echo -e "${GREEN}  ✓ Workflow file exists${NC}"
else
    echo -e "${RED}  ✗ Workflow file not found${NC}"
    exit 1
fi

# Check 2: YAML syntax
echo -e "\n${YELLOW}✓ Checking YAML syntax...${NC}"
if python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-siteground.yml'))" 2>/dev/null; then
    echo -e "${GREEN}  ✓ YAML syntax is valid${NC}"
else
    echo -e "${RED}  ✗ YAML syntax error${NC}"
    exit 1
fi

# Check 3: Required secrets referenced
echo -e "\n${YELLOW}✓ Checking required secrets...${NC}"
REQUIRED_SECRETS=("SITEGROUND_SSH_HOST" "SITEGROUND_SSH_USER" "SITEGROUND_SSH_PORT" "SITEGROUND_SSH_KEY")
for secret in "${REQUIRED_SECRETS[@]}"; do
    if grep -q "secrets.$secret" .github/workflows/deploy-siteground.yml; then
        echo -e "${GREEN}  ✓ $secret referenced${NC}"
    else
        echo -e "${RED}  ✗ $secret not found${NC}"
    fi
done

# Check 4: Workflow triggers
echo -e "\n${YELLOW}✓ Checking workflow triggers...${NC}"
if grep -q "push:" .github/workflows/deploy-siteground.yml && grep -q "branches:" .github/workflows/deploy-siteground.yml; then
    echo -e "${GREEN}  ✓ Push trigger configured${NC}"
else
    echo -e "${RED}  ✗ Push trigger missing${NC}"
fi

if grep -q "workflow_dispatch" .github/workflows/deploy-siteground.yml; then
    echo -e "${GREEN}  ✓ Manual trigger enabled${NC}"
else
    echo -e "${YELLOW}  ⚠ Manual trigger not found (optional)${NC}"
fi

# Check 5: SSH setup steps
echo -e "\n${YELLOW}✓ Checking deployment steps...${NC}"
if grep -q "Setup SSH" .github/workflows/deploy-siteground.yml; then
    echo -e "${GREEN}  ✓ SSH setup step found${NC}"
else
    echo -e "${RED}  ✗ SSH setup step missing${NC}"
fi

if grep -q "Deploy to SiteGround" .github/workflows/deploy-siteground.yml; then
    echo -e "${GREEN}  ✓ Deployment step found${NC}"
else
    echo -e "${RED}  ✗ Deployment step missing${NC}"
fi

if grep -q "Cleanup SSH key" .github/workflows/deploy-siteground.yml; then
    echo -e "${GREEN}  ✓ Cleanup step found${NC}"
else
    echo -e "${YELLOW}  ⚠ Cleanup step not found${NC}"
fi

# Check 6: Git repository status
echo -e "\n${YELLOW}✓ Checking git status...${NC}"
if [ -d ".git" ]; then
    echo -e "${GREEN}  ✓ Git repository detected${NC}"
    
    # Check if workflow is tracked
    if git ls-files --error-unmatch .github/workflows/deploy-siteground.yml >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Workflow file is tracked by git${NC}"
    else
        echo -e "${YELLOW}  ⚠ Workflow file not yet committed${NC}"
        echo -e "${YELLOW}    Run: git add .github/workflows/deploy-siteground.yml${NC}"
    fi
    
    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo -e "${GREEN}  ✓ Current branch: $CURRENT_BRANCH${NC}"
else
    echo -e "${YELLOW}  ⚠ Not a git repository${NC}"
fi

# Summary
echo -e "\n${GREEN}==================================="
echo "Verification Complete"
echo -e "===================================${NC}\n"

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Add GitHub Secrets (if not done):"
echo "   - Go to: GitHub Repo → Settings → Secrets → Actions"
echo "   - Add: SITEGROUND_SSH_HOST, SITEGROUND_SSH_USER, SITEGROUND_SSH_PORT, SITEGROUND_SSH_KEY"
echo ""
echo "2. Commit and push the workflow:"
echo "   git add .github/workflows/deploy-siteground.yml"
echo "   git commit -m 'Add GitHub Actions auto-deployment'"
echo "   git push origin main"
echo ""
echo "3. Test the workflow:"
echo "   - Go to: GitHub Repo → Actions tab"
echo "   - You should see 'Deploy to SiteGround' workflow"
echo "   - Or trigger manually: Actions → Deploy to SiteGround → Run workflow"
echo ""
echo -e "${GREEN}Workflow is ready to use!${NC}\n"

