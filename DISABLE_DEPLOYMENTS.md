# How to Disable/Enable GitHub Actions Deployments

## Quick Guide

### To DISABLE Deployments (Stop Auto-Deploy)

1. Go to your GitHub repository
2. Navigate to: **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"**
4. Name: `DEPLOYMENT_ENABLED`
5. Value: `false`
6. Click **"Add secret"**

**Result:** All deployments will be skipped. The workflow will still run but exit immediately with a message.

### To ENABLE Deployments Again

**Option 1:** Delete the secret
1. Go to: **Settings → Secrets and variables → Actions**
2. Find `DEPLOYMENT_ENABLED`
3. Click **"Delete"**

**Option 2:** Change the value
1. Go to: **Settings → Secrets and variables → Actions**
2. Find `DEPLOYMENT_ENABLED`
3. Click **"Update"**
4. Change value to: `true`
5. Click **"Update secret"**

## Alternative: Disable via GitHub UI

You can also disable the workflow entirely:

1. Go to: **Actions** tab
2. Click on **"Deploy to SiteGround"** workflow
3. Click **"..."** (three dots) in the top right
4. Click **"Disable workflow"**

To re-enable:
1. Go to: **Actions** tab
2. Click on **"Deploy to SiteGround"** workflow
3. Click **"..."** (three dots)
4. Click **"Enable workflow"**

## Why Use the Secret Method?

- ✅ More granular control
- ✅ Can leave workflow enabled but paused
- ✅ Easy to toggle on/off
- ✅ Workflow still runs (shows as skipped) so you can see activity
- ✅ No need to remember to re-enable later

## During Account Upgrades

When upgrading your SiteGround account:

1. **Before upgrade:** Set `DEPLOYMENT_ENABLED` secret to `false`
2. **Perform upgrade:** Complete your SiteGround account upgrade
3. **After upgrade:** Set `DEPLOYMENT_ENABLED` secret to `true` or delete it

This prevents deployments from interfering with your upgrade process.

