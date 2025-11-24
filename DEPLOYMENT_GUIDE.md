# SiteGround Deployment Guide
## SUNO Downloader Pro - hikeyz.com

Complete step-by-step guide to deploy your SaaS to SiteGround.

---

## Pre-Deployment Checklist

- [ ] SiteGround hosting account active
- [ ] Domain hikeyz.com pointed to SiteGround
- [ ] Stripe account created with API keys
- [ ] Google AdSense account approved
- [ ] SSL certificate ready (Let's Encrypt via cPanel)

---

## Step 1: Prepare Stripe Products

1. Log into Stripe Dashboard (https://dashboard.stripe.com)
2. Navigate to **Products** → **Add Product**
3. Create two products:

   **Product 1: Quick Download**
   - Name: Quick Download
   - Description: 10 minutes access to download up to 500 SUNO songs
   - Pricing: $4.99 USD (one-time payment)
   - Copy the Price ID (starts with `price_...`)

   **Product 2: Pro Access**
   - Name: Pro Access
   - Description: 72 hours unlimited access to download SUNO songs
   - Pricing: $49.99 USD (one-time payment)
   - Copy the Price ID (starts with `price_...`)

4. Get your API keys:
   - Go to **Developers** → **API Keys**
   - Copy **Publishable key** (starts with `pk_live_...` or `pk_test_...`)
   - Copy **Secret key** (starts with `sk_live_...` or `sk_test_...`)

---

## Step 2: Upload Files to SiteGround

### Option A: Using cPanel File Manager

1. Log into SiteGround cPanel
2. Open **File Manager**
3. Navigate to `/home/username/public_html/`
4. Create folder: `hitbot-agency`
5. Upload all files maintaining structure:
   ```
   hitbot-agency/
   ├── public/
   ├── api/
   ├── database/
   ├── config/
   └── README.md
   ```

### Option B: Using FTP/SFTP

1. Get SFTP credentials from SiteGround
2. Use FileZilla or similar client
3. Upload entire `hitbot-agency` folder to `/home/username/`

---

## Step 3: Set Up Python Environment

### SSH into SiteGround

```bash
ssh username@hikeyz.com -p18765
```

### Create Virtual Environment

```bash
cd ~/hitbot-agency/api
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4: Create MySQL Database

1. In cPanel, go to **MySQL Databases**
2. Create database: `username_suno`
3. Create user: `username_suno_user`
4. Set strong password (save this!)
5. Grant **ALL PRIVILEGES** to user on database
6. Click **Add**

### Import Database Schema

1. Open **phpMyAdmin** from cPanel
2. Select `username_suno` database
3. Click **Import** tab
4. Choose file: `database/schema.sql`
5. Click **Go**

---

## Step 5: Configure Environment Variables

Create `.env` file in `config/` directory:

```bash
cd ~/hitbot-agency/config
cp .env.template .env
nano .env
```

Fill in the values:

```env
# Stripe Configuration (from Step 1)
STRIPE_SECRET_KEY=sk_live_your_actual_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_actual_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Stripe Price IDs
STRIPE_QUICK_PRICE_ID=price_quick_id_from_step_1
STRIPE_PRO_PRICE_ID=price_pro_id_from_step_1

# Application Settings
APP_ENV=production
APP_SECRET_KEY=generate_random_64_char_string
APP_BASE_URL=https://hikeyz.com

# Database (from Step 4)
DATABASE_URL=mysql://username_suno_user:your_password@localhost/username_suno

# Google AdSense (from your AdSense account)
ADSENSE_CLIENT_ID=ca-pub-your_adsense_id
ADSENSE_SLOT_ID=your_ad_slot_id

# Server
PORT=5000
WORKERS=4

# Storage
DOWNLOAD_DIR=/home/username/hitbot-agency/downloads
```

Save and exit (Ctrl+X, Y, Enter)

---

## Step 6: Set Up Python App in cPanel

1. Go to cPanel → **Setup Python App**
2. Click **Create Application**
3. Configure:
   - Python version: 3.9 or higher
   - Application root: `/home/username/hitbot-agency/api`
   - Application URL: Leave empty (we'll use domain)
   - Application startup file: `app.py`
   - Application Entry point: `app`
4. Click **Create**

### Update Passenger Configuration

Create `.htaccess` in `/public_html/`:

```apache
PassengerEnabled On
PassengerAppRoot /home/username/hitbot-agency/api
PassengerBaseURI /
PassengerPython /home/username/hitbot-agency/api/venv/bin/python3

RewriteEngine On

# API proxy
RewriteCond %{REQUEST_URI} ^/api/
RewriteRule ^(.*)$ - [L,E=PROXY_PASS:http://localhost:5000/$1]

# Static files
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_URI} !^/api/
RewriteRule ^(.*)$ /index.html [L]
```

---

## Step 7: Configure Domain DNS

1. In cPanel → **Zone Editor**
2. Add/Update records for hikeyz.com:
   ```
   Type: A
   Name: hikeyz.com
   Points to: [Your SiteGround server IP]

   Type: A
   Name: www
   Points to: [Your SiteGround server IP]
   ```

---

## Step 8: Enable SSL Certificate

1. In cPanel → **Let's Encrypt SSL**
2. Select domain: `hikeyz.com` and `www.hikeyz.com`
3. Click **Install**
4. Wait for installation (2-5 minutes)

### Force HTTPS Redirect

Add to `.htaccess` (top of file):

```apache
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

---

## Step 9: Set Up Stripe Webhook

1. Go to Stripe Dashboard → **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Endpoint URL: `https://hikeyz.com/api/webhook`
4. Events to send:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Click **Add endpoint**
6. Copy the **Signing secret** (starts with `whsec_...`)
7. Update `.env` with this secret:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_your_copied_secret
   ```

---

## Step 10: Test the Application

### Test Landing Page

Visit: https://hikeyz.com

Should see:
- Landing page loads correctly
- All images/fonts work
- Pricing cards display
- Navigation works

### Test Payment Flow

1. Click "Get Started" on Quick Download plan
2. Should redirect to Stripe Checkout
3. Use test card: `4242 4242 4242 4242`
4. Complete payment
5. Should redirect back with session ID

### Test API Endpoints

```bash
# Health check
curl https://hikeyz.com/api/

# Pricing
curl https://hikeyz.com/api/pricing
```

---

## Step 11: Set Up Cron Jobs

In cPanel → **Cron Jobs**, add:

### Cleanup expired sessions (daily at 2 AM)
```
0 2 * * * cd /home/username/hitbot-agency/api && /home/username/hitbot-agency/api/venv/bin/python3 -c "from app import cleanup_sessions; cleanup_sessions()"
```

### Delete old download files (daily at 3 AM)
```
0 3 * * * find /home/username/hitbot-agency/downloads -name "*.zip" -mtime +7 -delete
```

---

## Step 12: Monitoring and Logs

### View Application Logs

```bash
tail -f ~/logs/hitbot-agency_error.log
tail -f ~/logs/hitbot-agency_access.log
```

### Monitor Stripe Dashboard

Check regularly:
- Successful payments
- Failed payments
- Webhook delivery status

---

## Troubleshooting

### Payment not working
- Check Stripe webhook is receiving events
- Verify webhook secret in `.env`
- Check API logs for errors

### 500 Internal Server Error
- Check Python app is running: `ps aux | grep python`
- Verify database connection in `.env`
- Check file permissions: `chmod 755 ~/hitbot-agency/api/app.py`

### SSL not working
- Wait 5-10 minutes after installation
- Clear browser cache
- Check cPanel SSL/TLS Status

### Database connection failed
- Verify credentials in `.env`
- Check user has ALL PRIVILEGES
- Test connection: `mysql -u username_suno_user -p username_suno`

---

## Post-Launch Checklist

- [ ] Test complete payment flow with real card
- [ ] Verify emails are being sent (if configured)
- [ ] Monitor first few transactions closely
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom)
- [ ] Configure backup schedule in cPanel
- [ ] Document any custom configurations
- [ ] Set up Google Analytics
- [ ] Submit sitemap to Google Search Console

---

## Scaling Considerations

### When you hit 100 users/month:
- Monitor server resources in cPanel
- Consider upgrading to Cloud Hosting
- Implement Redis for session storage

### When you hit 500 users/month:
- Migrate to VPS or cloud (AWS/GCP)
- Set up separate database server
- Add Celery for background jobs
- Implement CDN for static assets

### When you hit 1000+ users/month:
- Kubernetes for auto-scaling
- Load balancer
- Object storage (S3/GCS)
- Dedicated support team

---

## Security Best Practices

1. Never commit `.env` to git
2. Use strong database passwords
3. Keep Python packages updated
4. Enable cPanel two-factor authentication
5. Regular backups (automated in cPanel)
6. Monitor Stripe for suspicious activity
7. Rate limit API endpoints (implement in app.py)
8. Regular security audits

---

## Support

If you encounter issues:
1. Check logs first (`~/logs/`)
2. Verify environment variables
3. Test API endpoints manually
4. Contact SiteGround support for server issues
5. Contact Stripe support for payment issues

---

## Success Metrics to Track

- Daily/monthly revenue
- Conversion rate (visitors → paying customers)
- Average order value
- Customer acquisition cost
- Churn rate (for Pro plan users)
- Server uptime
- Average download time
- Customer support tickets

---

## Maintenance Schedule

**Daily:**
- Check Stripe dashboard for new payments
- Monitor error logs

**Weekly:**
- Review analytics
- Check disk space usage
- Update dependencies if needed

**Monthly:**
- Review and optimize costs
- Analyze user feedback
- Plan new features
- Security audit

---

🎉 **Deployment Complete!**

Your SUNO Downloader Pro is now live at **https://hikeyz.com**

Remember to test thoroughly before promoting to customers.
