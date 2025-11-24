# Security & Environment Setup

## 🔒 What's Safe vs. Unsafe for GitHub

### ✅ SAFE to Commit (Already in Repo)
- Application code (`.py`, `.html`, `.css`, `.js`)
- Database schema (`.sql`)
- Documentation (`.md`)
- `.gitignore`
- `.env.example` (template with fake values)
- `requirements.txt`
- Deployment guides

### ❌ NEVER Commit (Blocked by .gitignore)
- `.env` (real secrets)
- `downloads/` (user files)
- `*.mp3`, `*.zip` (song files)
- `logs/` (log files)
- Database dumps with data
- Any file containing real API keys

---

## 📝 Proper Workflow

### 1. First Time Setup (Local Development)

```bash
# Clone your repo
git clone https://github.com/yourusername/hitbot-agency.git
cd hitbot-agency

# Create your local .env from template
cp .env.example .env

# Edit .env with your real secrets
nano .env  # or use your favorite editor

# Install dependencies
pip3 install -r requirements.txt

# The .env file is in .gitignore, so it won't be committed!
```

### 2. Daily Development Workflow

```bash
# Make code changes
nano api/app.py

# Test locally (your .env is still there)
python3 api/app.py

# Commit ONLY code changes
git add api/app.py
git commit -m "Add new feature"
git push origin main

# ✅ Your .env stays LOCAL and never gets pushed!
```

### 3. Production Deployment (SiteGround)

**Option A: Manual Environment Variables (Recommended)**
1. Go to SiteGround cPanel → Python App
2. Click "Environment Variables"
3. Add each variable manually:
   - `STRIPE_SECRET_KEY` = `sk_live_...`
   - `DB_PASSWORD` = `your_password`
   - etc.

**Option B: Upload .env via SFTP**
1. Upload `.env` directly via SFTP (not Git!)
2. Place in `/home/your_user/hitbot-agency/.env`
3. Never commit this file to GitHub

---

## 🔐 Environment Variable Storage Options

### Local Development
```bash
# File: .env (ignored by git)
STRIPE_SECRET_KEY=sk_test_...
DB_PASSWORD=dev_password
```

### Production (SiteGround)
**Use cPanel Environment Variables:**
- More secure than file storage
- Can't accidentally commit
- Easy to update without redeployment

### Alternative: GitHub Secrets (For CI/CD)
If you set up GitHub Actions later:
1. Go to repo → Settings → Secrets
2. Add secrets there
3. Reference in workflows

---

## 🚨 What If You Accidentally Commit Secrets?

### If you haven't pushed yet:
```bash
# Undo the commit
git reset HEAD~1

# Remove from staging
git restore --staged .env

# Make sure .env is in .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

### If you already pushed:
1. **IMMEDIATELY rotate all secrets:**
   - Stripe: Dashboard → API Keys → "Roll key"
   - Database: Change password

2. **Remove from Git history:**
   ```bash
   # WARNING: This rewrites history!
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all

   git push origin --force --all
   ```

3. **Consider using BFG Repo-Cleaner for large cleanups**

---

## ✅ Verification Checklist

Before pushing to GitHub:

```bash
# Check what will be committed
git status

# Make sure .env is NOT listed
# If it is, STOP and add to .gitignore

# Check .gitignore exists and includes .env
cat .gitignore | grep "^\.env$"

# Double-check no secrets in staged files
git diff --cached | grep -i "sk_live\|sk_test\|password"

# If nothing found, you're safe to push
git push
```

---

## 📚 Best Practices Summary

1. **Always use .env.example as template**
   - Commit .env.example (fake values)
   - Never commit .env (real values)

2. **Separate configs per environment**
   - `.env.development` (local)
   - `.env.staging` (test server)
   - `.env.production` (live server)

3. **Use environment-specific logic**
   ```python
   import os

   if os.getenv('DEBUG') == 'True':
       # Development settings
       stripe.api_key = os.getenv('STRIPE_TEST_KEY')
   else:
       # Production settings
       stripe.api_key = os.getenv('STRIPE_LIVE_KEY')
   ```

4. **Regular security audits**
   ```bash
   # Scan for accidentally committed secrets
   git log -p | grep -i "sk_live\|password\|secret"
   ```

---

## 🆘 Need Help?

If you're unsure if something is safe to commit:
1. Check if it's in `.gitignore`
2. Ask: "Would this be dangerous if public?"
3. When in doubt, DON'T commit it!
