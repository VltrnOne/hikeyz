# GitHub Actions Auto-Deployment Setup

This guide will help you set up automatic deployment from GitHub to SiteGround.

## Quick Setup (5 minutes)

### Step 1: Get Your SSH Private Key

**Option A: Use existing key**
```bash
cat ~/sg_key_new
```
Copy the entire output (including BEGIN/END lines)

**Option B: Generate new key in SiteGround**
1. Log into SiteGround cPanel
2. Go to: **Site Tools → Dev → SSH Keys Manager**
3. Click "Generate a New Key"
4. Name it: `github-actions`
5. Download the private key
6. Copy its contents

### Step 2: Add GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these 4 secrets:

| Secret Name | Value | Example |
|------------|-------|---------|
| `SITEGROUND_SSH_HOST` | Your SiteGround host | `gcam1145.siteground.biz` |
| `SITEGROUND_SSH_USER` | Your SiteGround username | `u2296-bzl1wdrk3lgl` |
| `SITEGROUND_SSH_PORT` | SSH port | `18765` |
| `SITEGROUND_SSH_KEY` | Your SSH private key (full content) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

**Important**: For `SITEGROUND_SSH_KEY`, paste the ENTIRE key including:
- `-----BEGIN OPENSSH PRIVATE KEY-----`
- All the key content
- `-----END OPENSSH PRIVATE KEY-----`

### Step 3: Test Deployment

1. Make a small change (add a comment to any file)
2. Commit and push:
   ```bash
   git add .
   git commit -m "Test auto-deployment"
   git push origin main
   ```
3. Go to GitHub → **Actions** tab
4. You should see "Deploy to SiteGround" workflow running
5. Wait for it to complete (usually 1-2 minutes)
6. Check your SiteGround site - changes should be live!

## How It Works

- **Automatic**: Every push to `main` branch triggers deployment
- **Secure**: SSH keys stored in GitHub Secrets (encrypted)
- **Fast**: Only pulls changes and updates dependencies if needed
- **Safe**: Application auto-restarts on SiteGround

## Manual Deployment

You can also trigger deployment manually:

1. GitHub → **Actions** tab
2. Select **Deploy to SiteGround**
3. Click **Run workflow**
4. Select branch → **Run workflow**

## Troubleshooting

### ❌ "Permission denied (publickey)"

**Problem**: SSH key not authorized or incorrect

**Solution**:
1. Verify SSH key is authorized in SiteGround cPanel → SSH Keys Manager
2. Check that the key secret contains the full private key
3. Test SSH manually:
   ```bash
   ssh -i ~/sg_key_new -p 18765 u2296-bzl1wdrk3lgl@gcam1145.siteground.biz
   ```

### ❌ "Host key verification failed"

**Problem**: Host key not in known_hosts

**Solution**: The workflow handles this automatically, but if it persists:
```bash
ssh-keyscan -p 18765 gcam1145.siteground.biz >> ~/.ssh/known_hosts
```

### ❌ Deployment succeeds but site doesn't update

**Problem**: Application not restarting

**Solution**:
1. Check SiteGround cPanel → Python App → Logs
2. Manually restart: cPanel → Python App → Restart
3. Verify file changes were pulled: SSH in and check `~/hikeyz/api/app.py` timestamp

### ❌ Dependencies not updating

**Problem**: `requirements.txt` changes not reflected

**Solution**: 
- Check workflow logs - pip install should run automatically
- If it fails, check Python version compatibility
- Manually update: SSH in and run `pip install -r requirements.txt`

## What Gets Deployed

✅ All code files  
✅ Python dependencies (if requirements.txt changed)  
✅ Public files (HTML, CSS, JS)  
✅ Database schemas (not auto-applied)  

❌ Environment variables (set in cPanel)  
❌ Database data (manual migration required)  
❌ Local files (downloads/, logs/)  

## Security Best Practices

- ✅ SSH keys stored in GitHub Secrets (encrypted)
- ✅ Keys cleaned up after each deployment
- ✅ Only authorized repository collaborators can trigger
- ✅ Deployment logs are visible to repository members only

## Next Steps

Once auto-deployment is working:

1. ✅ Test with a small change
2. ✅ Verify site updates automatically
3. ✅ Set up branch protection (optional)
4. ✅ Configure deployment notifications (optional)

## Need Help?

- Check workflow logs in GitHub → Actions tab
- Review SiteGround Python App logs
- Test SSH connection manually
- Check `.github/workflows/deploy-siteground.yml` for workflow details

