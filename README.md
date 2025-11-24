# SUNO Downloader Pro

Automated bulk download service for SUNO AI songs with Stripe payment integration.

## Overview

SUNO Downloader Pro is a SaaS application that automates the bulk downloading of songs from SUNO AI accounts. Users can purchase access in two tiers:

- **Quick Download** ($4.99): 10 minutes access, up to 500 songs
- **Pro Access** ($49.99): 72 hours unlimited access

## Features

- Automated infinite scroll handling for large libraries (340+ songs)
- Real-time progress dashboard
- Stripe payment integration
- Google AdSense monetization during downloads
- Secure session management
- ZIP file delivery
- Rate limiting and download optimization

## Project Structure

```
hitbot-agency/
├── public/               # Frontend landing page
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── api/                  # Backend API
│   ├── app.py           # Flask API with Stripe integration
│   └── requirements.txt
├── workers/             # Background job processors
│   └── downloader.py    # SUNO download automation
├── database/            # Database schemas
│   └── schema.sql
└── config/              # Configuration
    └── .env.template
```

## Setup Instructions

### 1. Backend Setup

```bash
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the `.env.template` to `.env` and fill in your values:

```bash
cp config/.env.template config/.env
```

Required variables:
- `STRIPE_SECRET_KEY`: Your Stripe secret key
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key
- `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook secret
- `STRIPE_QUICK_PRICE_ID`: Price ID for Quick Download plan
- `STRIPE_PRO_PRICE_ID`: Price ID for Pro Access plan

### 3. Create Stripe Products

1. Go to Stripe Dashboard > Products
2. Create two products:
   - **Quick Download**: $4.99, one-time payment
   - **Pro Access**: $49.99, one-time payment
3. Copy the Price IDs to your `.env` file

### 4. Set Up Webhook

1. In Stripe Dashboard, go to Developers > Webhooks
2. Add endpoint: `https://hikeyz.com/api/webhook`
3. Select events: `checkout.session.completed`, `payment_intent.succeeded`, `payment_intent.payment_failed`
4. Copy webhook signing secret to `.env`

### 5. Run the Application

Development:
```bash
cd api
python3 app.py
```

Production (with Gunicorn):
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API Endpoints

### Public Endpoints

- `GET /` - Health check
- `GET /api/pricing` - Get pricing plans
- `POST /api/create-checkout-session` - Create Stripe checkout
- `POST /api/webhook` - Stripe webhook handler

### Authenticated Endpoints

- `POST /api/validate-session` - Validate session token
- `POST /api/start-download` - Start download job
- `GET /api/job-status/<job_id>` - Get job status
- `GET /api/download-file/<job_id>` - Download ZIP file
- `POST /api/cancel-job/<job_id>` - Cancel job

## SiteGround Deployment

### Prerequisites

- cPanel access to your SiteGround account
- Domain: hikeyz.com
- Python 3.9+ support
- MySQL database

### Deployment Steps

1. **Upload Files via cPanel**
   - Use File Manager or FTP to upload the entire project
   - Place in `/home/username/hitbot-agency/`

2. **Set up Python Environment**
   ```bash
   cd ~/hitbot-agency/api
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create Database**
   - Use cPanel > MySQL Databases
   - Create database: `username_suno`
   - Import `database/schema.sql`

4. **Configure .htaccess**
   Create `.htaccess` in public root:
   ```apache
   RewriteEngine On
   RewriteCond %{REQUEST_FILENAME} !-f
   RewriteCond %{REQUEST_FILENAME} !-d
   RewriteRule ^(.*)$ /index.html [L]

   # API proxy
   RewriteRule ^api/(.*)$ http://localhost:5000/api/$1 [P,L]
   ```

5. **Set up Passenger**
   - In cPanel > Setup Python App
   - Set application root: `/home/username/hitbot-agency/api`
   - Set application URL: `hikeyz.com`
   - Set entry point: `app:app`

6. **Configure Cron Jobs**
   Add to crontab:
   ```
   */5 * * * * /home/username/hitbot-agency/workers/cleanup.sh
   ```

7. **SSL Certificate**
   - Enable Let's Encrypt SSL in cPanel
   - Force HTTPS redirect

## Security Considerations

1. Never commit `.env` files to git
2. Use strong secret keys
3. Enable Stripe webhook signature verification
4. Implement rate limiting on API endpoints
5. Sanitize all user inputs
6. Set up CORS properly for production

## Monetization Strategy

### Stripe Payments
- Quick Download: $4.99 (estimated 10 minutes server cost: $0.05)
- Pro Access: $49.99 (estimated 72 hours server cost: $2.00)
- Profit margins: ~98% and ~96% respectively

### Google AdSense
- Display ads during download process
- Estimated CPM: $2-5
- Additional revenue: $0.10-$0.25 per session

## Scaling Considerations

### Initial Launch (0-100 users)
- Single server deployment on SiteGround
- In-memory session storage
- Direct download processing

### Growth Phase (100-1000 users)
- Migrate to VPS or cloud hosting (AWS/GCP)
- Implement Redis for session management
- Add Celery for background job queue
- Set up CDN for file delivery

### Scale Phase (1000+ users)
- Kubernetes cluster for auto-scaling
- Separate database server (RDS/Cloud SQL)
- Object storage for downloads (S3/GCS)
- Load balancer for API

## Development Roadmap

- [ ] Phase 1: MVP Launch
  - [x] Landing page
  - [x] Stripe payment integration
  - [ ] SUNO automation worker
  - [ ] Real-time progress dashboard
  - [ ] File delivery system

- [ ] Phase 2: Features
  - [ ] User accounts (optional login)
  - [ ] Download history
  - [ ] Email notifications
  - [ ] Batch processing queue

- [ ] Phase 3: Growth
  - [ ] Referral program
  - [ ] Subscription plans
  - [ ] Enterprise tier
  - [ ] API access

## Troubleshooting

### Payment not processing
- Check Stripe webhook is receiving events
- Verify webhook secret matches
- Check server logs for errors

### Download fails
- Verify Chrome debugging port is accessible
- Check SUNO session is still valid
- Ensure sufficient disk space

### Session expired
- Check system time is correct
- Verify Redis connection (if using)
- Check session expiration logic

## Support

For issues or questions:
- Email: support@hikeyz.com
- Discord: [Link to Discord]
- Documentation: https://hikeyz.com/docs

## License

Proprietary - All rights reserved

## Contributors

- Jay Fairchild (@morpheous)

---

Built with Flask, Stripe, Selenium, and deployed on SiteGround.
