# Delete Render Service & Recreate After Upgrade

## Step 1: Delete the Current Service

1. **Go to Render Dashboard**: https://dashboard.render.com/web/hikeyz-api
2. **Click "Settings"** (left sidebar)
3. **Scroll to the very bottom** of the Settings page
4. **Look for "Danger Zone"** section
5. **Click "Delete Service"** or **"Suspend Service"**
6. **Type the service name** to confirm: `hikeyz-api`
7. **Click "Delete"** or **"Confirm"**

**This will:**
- ✅ Stop ALL deployments immediately
- ✅ Delete the service (but you can recreate it)
- ✅ Free up resources for upgrade

## Step 2: Upgrade Your Account

1. Go to: https://dashboard.render.com/account
2. Click **"Upgrade"** or **"Billing"**
3. Choose your plan
4. Complete the upgrade

## Step 3: Recreate the Service After Upgrade

### Option A: Quick Manual Creation

1. Go to: https://dashboard.render.com
2. Click **"+ New"** → **"Web Service"**
3. Connect GitHub repository: `VltrnOne/hikeyz`
4. Configure:
   - **Name**: `hikeyz-api`
   - **Region**: `Oregon`
   - **Branch**: `main`
   - **Root Directory**: (leave empty or `api`)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn api.app:app`
5. **Important**: Set **"Auto-Deploy"** to **"No"** (manual only)
6. Click **"Create Web Service"**

### Option B: Use Blueprint (render.yaml)

After upgrade, uncomment the render.yaml:

1. Edit `render.yaml` in your repo
2. Uncomment the service definition
3. Push to GitHub
4. Go to: https://dashboard.render.com/new/blueprint
5. Connect GitHub repo
6. Render will detect `render.yaml` and create the service

## Step 4: Set Environment Variables

After recreating, add your environment variables:

1. Go to service → **Settings** → **Environment**
2. Add all your variables:
   - `DB_HOST`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - etc.

## Quick Commands to Help

### Delete Service via Render Dashboard
Just follow Step 1 above - it's the fastest way.

### After Upgrade - Recreate
Use Option A (manual) for fastest setup, or Option B (Blueprint) for automated.

## Why This Works

- ✅ Clean slate - no conflicts
- ✅ Fresh start with upgraded account
- ✅ No deployment issues during upgrade
- ✅ Easy to recreate (5 minutes)

## Time Estimate

- **Delete service**: 1 minute
- **Upgrade account**: 5-10 minutes
- **Recreate service**: 5 minutes
- **Total**: ~15 minutes

This is faster than trying to disable everything!

