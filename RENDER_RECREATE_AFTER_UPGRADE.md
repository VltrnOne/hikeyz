# Quick Guide: Recreate Render Service After Upgrade

## After You Delete & Upgrade

### Fastest Method: Manual Creation

1. **Go to**: https://dashboard.render.com/new/web-service
2. **Connect GitHub**: Select `VltrnOne/hikeyz` repository
3. **Configure**:
   ```
   Name: hikeyz-api
   Region: Oregon
   Branch: main
   Root Directory: api (or leave empty)
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn api.app:app
   ```
4. **Set Auto-Deploy**: **"No"** (manual deployments only)
5. **Click "Create Web Service"**

### Add Environment Variables

Go to Settings → Environment and add:
- `DB_HOST`
- `DB_USER` 
- `DB_PASSWORD`
- `DB_NAME`
- `DB_PORT`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- Any other vars you had before

### Test It Works

1. Go to service → **"Manual Deploy"**
2. Select **"Deploy latest commit"**
3. Wait for deployment to complete
4. Check your API URL: https://hikeyz-api.onrender.com

Done! 🎉

