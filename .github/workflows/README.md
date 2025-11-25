# GitHub Actions Deployment

This workflow automatically deploys your code to SiteGround whenever you push to the `main` branch.

## Setup Instructions

### 1. Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

- **SITEGROUND_SSH_HOST**: `gcam1145.siteground.biz`
- **SITEGROUND_SSH_USER**: `u2296-bzl1wdrk3lgl`
- **SITEGROUND_SSH_PORT**: `18765`
- **SITEGROUND_SSH_KEY**: Your SSH private key content (the entire key file)

### 2. Get Your SSH Private Key

If you already have the SSH key file (`~/sg_key_new` or similar), you can get its content:

```bash
cat ~/sg_key_new
```

Copy the entire output (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)

**OR** if you need to generate a new key:

1. Log into SiteGround cPanel
2. Go to: **Site Tools → Dev → SSH Keys Manager**
3. Generate a new key pair
4. Download the private key
5. Copy its contents to the GitHub secret

### 3. Test the Workflow

1. Make a small change to your code
2. Commit and push to `main`:
   ```bash
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```
3. Go to your GitHub repository → Actions tab
4. Watch the deployment workflow run
5. Check the logs for any errors

## How It Works

1. **Trigger**: Automatically runs on every push to `main` branch
2. **Checkout**: Downloads your code
3. **SSH Setup**: Configures SSH connection using secrets
4. **Deploy**: 
   - Connects to SiteGround
   - Pulls latest code from GitHub
   - Updates Python dependencies if needed
   - Creates necessary directories
   - Application auto-restarts (SiteGround Python apps restart on file changes)

## Manual Deployment

You can also trigger deployment manually:

1. Go to GitHub repository → Actions tab
2. Select "Deploy to SiteGround" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Troubleshooting

### Deployment Fails

1. **Check SSH Key**: Verify the SSH key secret is correct (full key including headers)
2. **Check SSH Access**: Test manually:
   ```bash
   ssh -i ~/sg_key_new -p 18765 u2296-bzl1wdrk3lgl@gcam1145.siteground.biz
   ```
3. **Check Logs**: View the Actions tab for detailed error messages

### Application Not Updating

- SiteGround Python apps should auto-restart on file changes
- If not, you may need to manually restart in cPanel → Python App → Restart

### Dependencies Not Updating

- The workflow checks `requirements.txt` and updates dependencies automatically
- Check the deployment logs to see if pip install ran successfully

## Security Notes

- SSH keys are stored securely in GitHub Secrets
- Keys are never exposed in logs
- Keys are cleaned up after deployment
- Only authorized users with repository access can trigger deployments

