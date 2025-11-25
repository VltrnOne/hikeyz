# SSH Key Authorization for SiteGround

Your SSH key is configured locally but needs to be authorized in SiteGround cPanel before deployment can proceed.

## Current Status

✓ SSH private key exists: `~/sg_key`
✓ Permissions set correctly: `600`
✗ Key needs authorization on SiteGround server

## How to Authorize Your SSH Key

### Step 1: Access SiteGround cPanel

1. Log into your SiteGround account
2. Navigate to: **Site Tools → Dev → SSH Keys Manager**

### Step 2: Check if Key Already Exists

Look for any existing SSH keys named "hikeyz" or similar.

**If the key already exists:**
- Look for the key in the list
- Click the "Manage" button next to it
- Click "Authorize" if it shows as "Not Authorized"
- **Done!** Skip to Step 4.

**If no key exists or you want to create a new one:**
- Continue to Step 3

### Step 3: Upload Your SSH Key

#### Option A: Generate a new key pair in cPanel (Recommended)

1. Click "Generate a New Key"
2. Enter a name: `hikeyz`
3. Optional: Add a passphrase for extra security
4. Click "Generate"
5. The key will be automatically authorized
6. Download the **Private Key** and save it as `~/sg_key` (replace the existing one)

#### Option B: Upload your existing public key

**First, generate the public key from your private key:**

```bash
# In Terminal, run:
ssh-keygen -y -f ~/sg_key

# When prompted for passphrase, enter it
# Copy the output (starts with "ssh-rsa" or "ssh-ed25519")
```

**Then upload in cPanel:**

1. Click "Import Key"
2. Paste the public key you just copied
3. Give it a name: `hikeyz`
4. Click "Import"
5. Click "Manage" next to the newly imported key
6. Click "Authorize"

### Step 4: Test SSH Connection

Once authorized, test the connection:

```bash
ssh -i ~/sg_key -p 18765 u2296-bzl1wdrk3lgl@gcam1145.siteground.biz
```

You should see a successful login prompt.

### Step 5: Run Deployment Script

Once SSH works, run the deployment:

```bash
cd /Users/Morpheous/vltrndataroom/hitbot-agency
./setup_ssh_and_deploy.sh
```

---

## Troubleshooting

### "Permission denied (publickey)"
- The key isn't authorized yet. Complete Steps 1-3 above.

### "Host key verification failed"
- Run: `ssh-keyscan -p 18765 gcam1145.siteground.biz >> ~/.ssh/known_hosts`

### "Bad permissions"
- Run: `chmod 600 ~/sg_key`

### Key has passphrase and you forgot it
- Generate a new key pair in cPanel (Option A above)
- Download the new private key
- Save as `~/sg_key`

---

## What Happens After Authorization

Once your SSH key is authorized, the deployment script will automatically:

1. ✓ Connect to SiteGround via SSH
2. ✓ Create directory structure
3. ✓ Clone GitHub repository
4. ✓ Set up Python virtual environment
5. ✓ Install dependencies
6. ✓ Prepare application for deployment

You'll then need to complete manual configuration in cPanel:
- Setup Python App
- Add environment variables
- Create MySQL database
- Enable SSL

Full instructions will appear after successful deployment.

---

**Need Help?**

If you're stuck, the deployment script will provide detailed error messages and guidance. Each step is validated before proceeding to the next.
