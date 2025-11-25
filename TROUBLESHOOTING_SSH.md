# Troubleshooting GitHub Actions SSH Authentication

## Error: "Permission denied (publickey)"

This error means GitHub Actions cannot authenticate with SiteGround using the SSH key.

## Common Causes & Solutions

### 1. SSH Key Format Issue

**Problem**: The SSH key secret might be missing newlines or have incorrect formatting.

**Solution**: 
- The SSH key MUST include the full key with proper line breaks
- It should look like this:
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
  ... (many lines of encoded key data) ...
  -----END OPENSSH PRIVATE KEY-----
  ```

**How to fix**:
1. Get your SSH key:
   ```bash
   cat ~/sg_key_new
   ```
2. Copy the ENTIRE output (including BEGIN and END lines)
3. In GitHub: Settings → Secrets → Actions → Edit `SITEGROUND_SSH_KEY`
4. Paste the complete key (make sure all lines are included)
5. Save

### 2. SSH Key Not Authorized on SiteGround

**Problem**: The key exists but isn't authorized in SiteGround cPanel.

**Solution**:
1. Log into SiteGround cPanel
2. Go to: **Site Tools → Dev → SSH Keys Manager**
3. Find your SSH key (or generate a new one)
4. Click **"Manage"** next to the key
5. Click **"Authorize"** if it shows as "Not Authorized"
6. Wait 1-2 minutes for changes to propagate

### 3. Wrong SSH Key Type

**Problem**: Using the wrong key (public instead of private, or wrong format).

**Solution**:
- You need the **PRIVATE KEY** (not the .pub file)
- It should start with `-----BEGIN OPENSSH PRIVATE KEY-----` or `-----BEGIN RSA PRIVATE KEY-----`
- If you only have the public key, generate a new key pair in SiteGround cPanel

### 4. Key Has Passphrase

**Problem**: SSH key is encrypted with a passphrase.

**Solution**:
- GitHub Actions cannot handle passphrase-protected keys
- Generate a new key WITHOUT a passphrase in SiteGround cPanel
- Or remove passphrase from existing key:
  ```bash
  ssh-keygen -p -f ~/sg_key_new
  # Enter old passphrase, then press Enter twice for no new passphrase
  ```

## Step-by-Step Fix

### Option A: Use Existing Key (Recommended)

1. **Get your SSH key**:
   ```bash
   cat ~/sg_key_new
   ```

2. **Copy the entire output** (all lines including BEGIN/END)

3. **Update GitHub Secret**:
   - Go to: GitHub Repo → Settings → Secrets → Actions
   - Click on `SITEGROUND_SSH_KEY`
   - Click "Update"
   - Paste the COMPLETE key (make sure no lines are missing)
   - Click "Update secret"

4. **Verify key is authorized**:
   - SiteGround cPanel → SSH Keys Manager
   - Ensure key shows as "Authorized"

5. **Test manually** (optional):
   ```bash
   ssh -i ~/sg_key_new -p 18765 u2296-bzl1wdrk3lgl@gcam1145.siteground.biz
   ```
   If this works, the GitHub secret should work too.

### Option B: Generate New Key in SiteGround

1. **Generate in cPanel**:
   - SiteGround cPanel → SSH Keys Manager
   - Click "Generate a New Key"
   - Name: `github-actions`
   - Leave passphrase EMPTY
   - Click "Generate"
   - Click "Authorize" (should auto-authorize)

2. **Download private key**:
   - Click "Manage" next to the key
   - Click "Download" (downloads private key)
   - Save it locally

3. **Add to GitHub Secret**:
   - Open the downloaded key file
   - Copy ALL contents
   - GitHub → Settings → Secrets → Actions → Update `SITEGROUND_SSH_KEY`
   - Paste complete key
   - Save

## Verification Steps

After updating the secret:

1. **Trigger workflow manually**:
   - GitHub → Actions → Deploy to SiteGround
   - Click "Run workflow" → "Run workflow"

2. **Check logs**:
   - Watch the "Setup SSH" step
   - Should see "SSH connection successful"
   - If still failing, check the error message

3. **Common error messages**:
   - `Permission denied (publickey)` → Key not authorized or wrong format
   - `Host key verification failed` → Already handled by workflow
   - `Connection timeout` → Network/firewall issue
   - `No such file or directory` → Key file not created properly

## Testing SSH Key Format

You can test if your key is valid:

```bash
# Check key format
head -1 ~/sg_key_new
# Should show: -----BEGIN OPENSSH PRIVATE KEY----- or -----BEGIN RSA PRIVATE KEY-----

tail -1 ~/sg_key_new
# Should show: -----END OPENSSH PRIVATE KEY----- or -----END RSA PRIVATE KEY-----

# Test key
ssh-keygen -l -f ~/sg_key_new
# Should show key fingerprint (not an error)
```

## Still Not Working?

1. **Double-check secret values**:
   - `SITEGROUND_SSH_HOST`: `gcam1145.siteground.biz`
   - `SITEGROUND_SSH_USER`: `u2296-bzl1wdrk3lgl`
   - `SITEGROUND_SSH_PORT`: `18765`
   - `SITEGROUND_SSH_KEY`: Full private key content

2. **Check SiteGround SSH access**:
   - Ensure SSH is enabled in SiteGround cPanel
   - Some accounts need SSH enabled manually

3. **Contact SiteGround support**:
   - They can verify SSH is enabled for your account
   - They can check if your key is properly authorized

## Quick Checklist

- [ ] SSH key includes BEGIN and END lines
- [ ] SSH key has no passphrase
- [ ] SSH key is authorized in SiteGround cPanel
- [ ] GitHub secret contains the complete private key
- [ ] Manual SSH connection works: `ssh -i ~/sg_key_new -p 18765 u2296-bzl1wdrk3lgl@gcam1145.siteground.biz`
- [ ] All 4 GitHub secrets are set correctly

