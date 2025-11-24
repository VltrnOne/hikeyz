#!/usr/bin/env python3
"""
SUNO Downloader Pro - Backend API with Stripe Integration
"""

from flask import Flask, request, jsonify, redirect, send_file
from flask_cors import CORS
import stripe
import os
import json
import time
import threading
from datetime import datetime, timedelta
import secrets
import sys

# Add workers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'workers'))
from suno_downloader import SUNODownloader

app = Flask(__name__)
CORS(app)

# Stripe Configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_YOUR_KEY_HERE')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_YOUR_WEBHOOK_SECRET')

# Pricing Configuration
PRICING_PLANS = {
    'quick': {
        'name': 'Quick Download',
        'price': 4.99,
        'duration_minutes': 10,
        'max_songs': 500,
        'stripe_price_id': os.getenv('STRIPE_QUICK_PRICE_ID', 'price_QUICK_ID')
    },
    'pro': {
        'name': 'Pro Access',
        'price': 49.99,
        'duration_hours': 72,
        'max_songs': None,  # Unlimited
        'stripe_price_id': os.getenv('STRIPE_PRO_PRICE_ID', 'price_PRO_ID')
    }
}

# In-memory session storage (replace with database in production)
active_sessions = {}
download_jobs = {}

@app.route('/')
def index():
    """Health check"""
    return jsonify({
        'status': 'online',
        'service': 'SUNO Downloader Pro API',
        'version': '1.0.0'
    })

@app.route('/api/pricing', methods=['GET'])
def get_pricing():
    """Get available pricing plans"""
    return jsonify({
        'plans': PRICING_PLANS
    })

@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """
    Create a Stripe Checkout session for payment

    Request body:
    {
        "plan": "quick" or "pro",
        "success_url": "https://yourdomain.com/success",
        "cancel_url": "https://yourdomain.com/cancel"
    }
    """
    try:
        data = request.get_json()
        plan_type = data.get('plan', 'quick')
        success_url = data.get('success_url', 'https://hitbot.agency/success')
        cancel_url = data.get('cancel_url', 'https://hitbot.agency/cancel')

        if plan_type not in PRICING_PLANS:
            return jsonify({'error': 'Invalid plan type'}), 400

        plan = PRICING_PLANS[plan_type]

        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': plan['stripe_price_id'],
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            client_reference_id=secrets.token_urlsafe(16),
            metadata={
                'plan_type': plan_type,
                'plan_name': plan['name'],
                'duration': str(plan.get('duration_minutes', plan.get('duration_hours', 0)))
            }
        )

        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session)

    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"Payment succeeded: {payment_intent['id']}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        print(f"Payment failed: {payment_intent['id']}")

    return jsonify({'status': 'success'})

def handle_successful_payment(session):
    """
    Process successful payment and create download session
    """
    client_reference_id = session.get('client_reference_id')
    plan_type = session['metadata'].get('plan_type', 'quick')

    # Calculate expiration time
    plan = PRICING_PLANS[plan_type]
    if 'duration_minutes' in plan:
        expires_at = datetime.now() + timedelta(minutes=plan['duration_minutes'])
    else:
        expires_at = datetime.now() + timedelta(hours=plan['duration_hours'])

    # Create session token
    session_token = secrets.token_urlsafe(32)

    # Store session
    active_sessions[session_token] = {
        'plan_type': plan_type,
        'plan_name': plan['name'],
        'created_at': datetime.now().isoformat(),
        'expires_at': expires_at.isoformat(),
        'max_songs': plan['max_songs'],
        'songs_downloaded': 0,
        'client_reference_id': client_reference_id,
        'stripe_session_id': session['id']
    }

    print(f"Created session: {session_token} for plan: {plan_type}")
    return session_token

@app.route('/api/validate-session', methods=['POST'])
def validate_session():
    """
    Validate if a session token is still active

    Request body:
    {
        "session_token": "token_here"
    }
    """
    data = request.get_json()
    session_token = data.get('session_token')

    if not session_token or session_token not in active_sessions:
        return jsonify({'valid': False, 'error': 'Invalid session'}), 401

    session = active_sessions[session_token]
    expires_at = datetime.fromisoformat(session['expires_at'])

    if datetime.now() > expires_at:
        # Session expired
        del active_sessions[session_token]
        return jsonify({'valid': False, 'error': 'Session expired'}), 401

    return jsonify({
        'valid': True,
        'session': {
            'plan_name': session['plan_name'],
            'expires_at': session['expires_at'],
            'max_songs': session['max_songs'],
            'songs_downloaded': session['songs_downloaded'],
            'time_remaining': (expires_at - datetime.now()).total_seconds()
        }
    })

def run_download_worker(job_id, session_token, credentials, max_songs):
    """
    Background function to run the download worker
    """
    try:
        print(f"Starting download worker for job {job_id}")

        # Create downloader instance
        downloader = SUNODownloader(job_id, session_token, credentials, max_songs)

        # Run the download process
        result = downloader.run()

        # Update job status in memory
        if job_id in download_jobs:
            if result.get('success'):
                download_jobs[job_id]['status'] = 'completed'
                download_jobs[job_id]['zip_path'] = result.get('zip_path')
            else:
                download_jobs[job_id]['status'] = 'failed'
                download_jobs[job_id]['error'] = result.get('error')

        print(f"Download worker completed for job {job_id}: {result}")

    except Exception as e:
        print(f"Download worker error for job {job_id}: {e}")
        if job_id in download_jobs:
            download_jobs[job_id]['status'] = 'failed'
            download_jobs[job_id]['error'] = str(e)

@app.route('/api/start-download', methods=['POST'])
def start_download():
    """
    Start a download job

    Request body:
    {
        "session_token": "token_here",
        "suno_credentials": {
            "method": "chrome_debug",  # Uses existing Chrome session
            "data": {}
        }
    }
    """
    data = request.get_json()
    session_token = data.get('session_token')
    credentials = data.get('suno_credentials', {'method': 'chrome_debug', 'data': {}})

    # Validate session
    if not session_token or session_token not in active_sessions:
        return jsonify({'error': 'Invalid session'}), 401

    session = active_sessions[session_token]
    expires_at = datetime.fromisoformat(session['expires_at'])

    if datetime.now() > expires_at:
        return jsonify({'error': 'Session expired'}), 401

    # Determine max songs based on plan
    max_songs = session.get('max_songs', 20)
    if max_songs is None:  # Pro plan (unlimited)
        max_songs = 500  # Practical limit per job

    # Create download job
    job_id = secrets.token_urlsafe(16)
    download_jobs[job_id] = {
        'status': 'queued',
        'session_token': session_token,
        'created_at': datetime.now().isoformat(),
        'progress': {
            'total_songs': 0,
            'downloaded': 0,
            'failed': 0,
            'current_song': None
        },
        'zip_path': None
    }

    # Start download worker in background thread
    worker_thread = threading.Thread(
        target=run_download_worker,
        args=(job_id, session_token, credentials, max_songs),
        daemon=True
    )
    worker_thread.start()

    return jsonify({
        'job_id': job_id,
        'status': 'queued',
        'message': 'Download job created and started',
        'max_songs': max_songs
    })

@app.route('/api/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Get the status of a download job
    Reads real-time progress from the progress JSON file
    """
    if job_id not in download_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = download_jobs[job_id]

    # Try to read progress from file for real-time updates
    progress_file = f"/Users/Morpheous/vltrndataroom/hitbot-agency/downloads/{job_id}_progress.json"
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                file_progress = json.load(f)

            # Update job with latest progress from file
            job['status'] = file_progress.get('status', job['status'])
            job['progress'] = {
                'total_songs': file_progress.get('total_songs', 0),
                'downloaded': file_progress.get('downloaded', 0),
                'failed': file_progress.get('failed', 0),
                'current_song': file_progress.get('current_song'),
                'error_message': file_progress.get('error_message')
            }

            # If completed, get zip path
            if file_progress.get('status') == 'completed':
                job['zip_path'] = file_progress.get('zip_file_path')

        except Exception as e:
            print(f"Error reading progress file: {e}")

    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'progress': job['progress'],
        'created_at': job['created_at'],
        'zip_path': job.get('zip_path')
    })

@app.route('/api/download-file/<job_id>', methods=['GET'])
def download_file(job_id):
    """
    Download the completed ZIP file
    """
    if job_id not in download_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = download_jobs[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400

    # Get ZIP file path
    zip_path = job.get('zip_path')

    if not zip_path or not os.path.exists(zip_path):
        return jsonify({'error': 'Download file not found'}), 404

    # Serve the ZIP file
    try:
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'suno_songs_{job_id}.zip'
        )
    except Exception as e:
        return jsonify({'error': f'Error serving file: {str(e)}'}), 500

@app.route('/api/cancel-job/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """
    Cancel a running download job
    """
    if job_id not in download_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = download_jobs[job_id]

    if job['status'] in ['completed', 'failed', 'cancelled']:
        return jsonify({'error': 'Cannot cancel job in current state'}), 400

    job['status'] = 'cancelled'

    return jsonify({
        'message': 'Job cancelled',
        'job_id': job_id
    })

if __name__ == '__main__':
    # Development server
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
