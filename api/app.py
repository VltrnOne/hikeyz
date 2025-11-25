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
import bcrypt
import mysql.connector
from mysql.connector import Error

# Add workers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'workers'))
from suno_downloader import SUNODownloader

app = Flask(__name__)
CORS(app)

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'hikeyz_db'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def hash_pin(pin):
    """Hash a PIN using bcrypt"""
    return bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_pin(pin, pin_hash):
    """Verify a PIN against its hash"""
    return bcrypt.checkpw(pin.encode('utf-8'), pin_hash.encode('utf-8'))

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
    Create a Stripe Checkout session for credit package purchase

    Request body:
    {
        "session_token": "usr_abc123...",  # User must be logged in
        "package_id": 2,  # Credit package ID (1=Starter, 2=Popular, 3=Premium)
        "success_url": "https://yourdomain.com/success",
        "cancel_url": "https://yourdomain.com/cancel"
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        package_id = data.get('package_id')
        success_url = data.get('success_url', 'https://hikeyz.com/success')
        cancel_url = data.get('cancel_url', 'https://hikeyz.com/cancel')

        # Validate user session
        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token. Please log in first.'}), 401

        session = active_sessions[session_token]
        
        # Check session expiration
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            del active_sessions[session_token]
            return jsonify({'error': 'Session expired'}), 401

        # Only credit-based users can purchase packages
        if session.get('plan_type') != 'credit':
            return jsonify({'error': 'Only registered users can purchase credit packages'}), 403

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID not found in session'}), 400

        if not package_id:
            return jsonify({'error': 'Package ID is required'}), 400

        # Get package details from database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id, package_name, usd_amount, base_credits, bonus_credits, total_credits
                FROM credit_packages
                WHERE id = %s AND is_active = TRUE
            """, (package_id,))

            package = cursor.fetchone()

            if not package:
                return jsonify({'error': 'Invalid or inactive package'}), 400

            # Create Stripe Price dynamically (or use existing price_id if stored in DB)
            # For now, create a one-time payment price
            try:
                # Try to create or retrieve price
                price = stripe.Price.create(
                    unit_amount=int(float(package['usd_amount']) * 100),  # Convert to cents
                    currency='usd',
                    product_data={
                        'name': package['package_name'],
                        'description': f"{package['total_credits']} credits ({package['base_credits']} base + {package['bonus_credits']} bonus)"
                    },
                    metadata={
                        'package_id': str(package_id),
                        'total_credits': str(package['total_credits'])
                    }
                )
                price_id = price.id
            except Exception as e:
                print(f"Error creating Stripe price: {e}")
                return jsonify({'error': 'Failed to create payment session'}), 500

            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                client_reference_id=str(user_id),  # Store user_id for webhook
                customer_email=session.get('email'),  # Pre-fill email if available
                metadata={
                    'user_id': str(user_id),
                    'package_id': str(package_id),
                    'package_name': package['package_name'],
                    'total_credits': str(package['total_credits']),
                    'base_credits': str(package['base_credits']),
                    'bonus_credits': str(package['bonus_credits']),
                    'usd_amount': str(package['usd_amount']),
                    'payment_type': 'fiat_stripe'
                }
            )

            print(f"Created Stripe checkout session for user {user_id}, package {package_id}")

            return jsonify({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'package_name': package['package_name'],
                'total_credits': float(package['total_credits']),
                'usd_amount': float(package['usd_amount'])
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
    Processes payment completion and adds credits to user accounts
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"Invalid payload in webhook: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature in webhook: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    try:
        if event['type'] == 'checkout.session.completed':
            stripe_session = event['data']['object']
            print(f"Processing checkout.session.completed for session: {stripe_session.get('id')}")
            
            result = handle_successful_payment(stripe_session)
            
            if result and result.get('success'):
                print(f"Successfully processed payment: {result}")
            else:
                print(f"Failed to process payment: {result}")

        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            print(f"Payment intent succeeded: {payment_intent['id']}")
            # Credits are added via checkout.session.completed, so we just log this

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            print(f"Payment intent failed: {payment_intent['id']}")

        else:
            print(f"Unhandled webhook event type: {event['type']}")

    except Exception as e:
        print(f"Error processing webhook event: {e}")
        # Still return 200 to prevent Stripe from retrying
        return jsonify({'status': 'error', 'message': str(e)}), 200

    return jsonify({'status': 'success'})

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """
    Verify Stripe payment status and return updated credit balance
    
    Request body:
    {
        "session_token": "usr_abc123...",
        "stripe_session_id": "cs_test_abc123..."  # From Stripe checkout success URL
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        stripe_session_id = data.get('stripe_session_id')

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        session = active_sessions[session_token]
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User ID not found in session'}), 400

        if not stripe_session_id:
            return jsonify({'error': 'Stripe session ID is required'}), 400

        # Retrieve Stripe checkout session
        try:
            stripe_session = stripe.checkout.Session.retrieve(stripe_session_id)
        except stripe.error.StripeError as e:
            return jsonify({'error': f'Failed to retrieve Stripe session: {str(e)}'}), 400

        # Check payment status
        payment_status = stripe_session.get('payment_status', 'unpaid')
        
        if payment_status != 'paid':
            return jsonify({
                'paid': False,
                'payment_status': payment_status,
                'message': 'Payment not completed yet'
            }), 200

        # Get updated user balance
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT credit_balance, total_credits_purchased
                FROM users
                WHERE id = %s
            """, (user_id,))

            user = cursor.fetchone()

            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Get package info from metadata
            metadata = stripe_session.get('metadata', {})
            package_name = metadata.get('package_name', 'Unknown')
            total_credits = float(metadata.get('total_credits', 0))

            credits_per_song = 0.35
            songs_available = int(float(user['credit_balance']) / credits_per_song)

            return jsonify({
                'paid': True,
                'payment_status': payment_status,
                'package_name': package_name,
                'credits_added': total_credits,
                'credit_balance': float(user['credit_balance']),
                'songs_available': songs_available,
                'total_credits_purchased': float(user['total_credits_purchased']),
                'message': f'Payment successful! {total_credits} credits added to your account.'
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Error verifying payment: {e}")
        return jsonify({'error': str(e)}), 500

def handle_successful_payment(stripe_session):
    """
    Process successful Stripe payment and add credits to user account
    
    Args:
        stripe_session: Stripe checkout session object from webhook
    """
    try:
        # Extract metadata from Stripe session
        metadata = stripe_session.get('metadata', {})
        payment_type = metadata.get('payment_type', '')
        
        # Handle credit package purchases (fiat via Stripe)
        if payment_type == 'fiat_stripe':
            user_id = int(metadata.get('user_id', 0))
            package_id = int(metadata.get('package_id', 0))
            stripe_session_id = stripe_session.get('id')
            payment_intent_id = stripe_session.get('payment_intent')
            
            if not user_id or not package_id:
                print(f"ERROR: Missing user_id or package_id in Stripe session metadata")
                return None
            
            # Connect to database
            conn = get_db_connection()
            if not conn:
                print(f"ERROR: Database connection failed for payment processing")
                return None
            
            cursor = conn.cursor(dictionary=True)
            
            try:
                # Call stored procedure to add credits
                # Parameters: user_id (IN), package_id (IN), payment_method (IN), tx_hash (IN), success (OUT), error_message (OUT)
                payment_method = 'stripe_card'
                tx_hash = payment_intent_id or stripe_session_id  # Use payment_intent_id as transaction hash
                
                cursor.callproc('add_credits', [user_id, package_id, payment_method, tx_hash, None, None])
                
                # Get OUT parameters (indices 4 and 5 for the OUT parameters)
                cursor.execute("SELECT @_add_credits_4 AS success, @_add_credits_5 AS error_message")
                result = cursor.fetchone()
                
                if result and result.get('success'):
                    # Get updated balance
                    cursor.execute("""
                        SELECT credit_balance FROM users WHERE id = %s
                    """, (user_id,))
                    user = cursor.fetchone()
                    new_balance = float(user['credit_balance']) if user else 0.0
                    
                    # Get package details for logging
                    cursor.execute("""
                        SELECT package_name, total_credits FROM credit_packages WHERE id = %s
                    """, (package_id,))
                    package = cursor.fetchone()
                    
                    conn.commit()
                    
                    print(f"SUCCESS: Added {package['total_credits'] if package else 'unknown'} credits to user {user_id} "
                          f"(new balance: {new_balance}) via Stripe payment {stripe_session_id}")
                    
                    return {
                        'success': True,
                        'user_id': user_id,
                        'package_id': package_id,
                        'credits_added': float(package['total_credits']) if package else 0,
                        'new_balance': new_balance
                    }
                else:
                    error_msg = result.get('error_message', 'Unknown error') if result else 'Unknown error'
                    print(f"ERROR: Failed to add credits for user {user_id}, package {package_id}: {error_msg}")
                    conn.rollback()
                    return None
                    
            except Exception as e:
                print(f"ERROR: Exception while processing payment: {e}")
                conn.rollback()
                return None
            finally:
                cursor.close()
                conn.close()
        
        # Legacy time-based plan handling (for backward compatibility)
        else:
            client_reference_id = stripe_session.get('client_reference_id')
            plan_type = metadata.get('plan_type', 'quick')
            
            if plan_type in PRICING_PLANS:
                plan = PRICING_PLANS[plan_type]
                
                # Calculate expiration time
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
                    'stripe_session_id': stripe_session['id']
                }
                
                print(f"Created legacy session: {session_token} for plan: {plan_type}")
                return {'session_token': session_token}
        
        return None
        
    except Exception as e:
        print(f"ERROR: handle_successful_payment exception: {e}")
        return None

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
            'plan_type': session.get('plan_type'),
            'plan_name': session.get('plan_name'),  # May not exist for credit-based sessions
            'expires_at': session['expires_at'],
            'max_songs': session.get('max_songs'),  # May not exist for credit-based sessions
            'songs_downloaded': session.get('songs_downloaded', 0),  # May not exist for credit-based sessions
            'free_credits': session.get('free_credits', 0),
            'ads_watched': session.get('ads_watched', 0),
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

                songs_downloaded = result.get('songs_downloaded', 0)

                # DEDUCT CREDITS based on plan type
                if session_token in active_sessions:
                    session = active_sessions[session_token]
                    plan_type = session.get('plan_type', 'free')

                    # CREDIT-BASED users: Deduct from database
                    if plan_type == 'credit':
                        user_id = session.get('user_id')

                        # Connect to database
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            try:
                                # Call stored procedure to deduct credits
                                # Parameters: user_id (IN), job_id (IN), songs_count (IN), success (OUT), error_message (OUT)
                                cursor.callproc('deduct_credits', [user_id, job_id, songs_downloaded, None, None])

                                # Get OUT parameters (indices 3 and 4 for the OUT parameters)
                                cursor.execute("SELECT @_deduct_credits_3 AS success, @_deduct_credits_4 AS error_message")
                                deduct_result = cursor.fetchone()

                                if deduct_result and deduct_result[0]:  # success = TRUE
                                    print(f"Credit-based: Deducted {songs_downloaded * 0.35} credits from user {user_id}")
                                else:
                                    error_msg = deduct_result[1] if deduct_result else 'Unknown error'
                                    print(f"Credit deduction failed: {error_msg}")

                                conn.commit()

                            except Exception as e:
                                print(f"Error deducting credits: {e}")
                                conn.rollback()
                            finally:
                                cursor.close()
                                conn.close()

                    # FREE TIER users: Deduct from session memory
                    elif plan_type == 'free':
                        current_credits = session.get('free_credits', 0)

                        # Deduct credits (1 credit per song)
                        new_credits = max(0, current_credits - songs_downloaded)
                        session['free_credits'] = new_credits
                        session['songs_downloaded'] = session.get('songs_downloaded', 0) + songs_downloaded

                        print(f"Free tier: Deducted {songs_downloaded} credits. " +
                              f"Remaining: {new_credits} (was {current_credits})")

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
        },
        "requested_songs": 10  # Optional: number of songs to download
    }
    """
    data = request.get_json()
    session_token = data.get('session_token')
    credentials = data.get('suno_credentials', {'method': 'chrome_debug', 'data': {}})
    requested_songs = data.get('requested_songs', None)

    # Validate session
    if not session_token or session_token not in active_sessions:
        return jsonify({'error': 'Invalid session'}), 401

    session = active_sessions[session_token]
    expires_at = datetime.fromisoformat(session['expires_at'])

    if datetime.now() > expires_at:
        return jsonify({'error': 'Session expired'}), 401

    plan_type = session.get('plan_type', 'free')

    # Handle CREDIT-BASED users
    if plan_type == 'credit':
        user_id = session.get('user_id')

        # Connect to database to check credits
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Get user's credit balance
            cursor.execute("""
                SELECT credit_balance FROM users WHERE id = %s
            """, (user_id,))

            user = cursor.fetchone()

            if not user:
                return jsonify({'error': 'User not found'}), 404

            credit_balance = float(user['credit_balance'])
            credits_per_song = 0.35

            # Check if user has sufficient credits
            if credit_balance < credits_per_song:
                return jsonify({
                    'error': 'Insufficient credits',
                    'credits_available': credit_balance,
                    'credits_required': credits_per_song,
                    'message': 'You need to purchase more credits to download songs.'
                }), 403

            # Calculate how many songs user can download
            max_downloadable = int(credit_balance / credits_per_song)

            # Set requested songs (default to max available)
            if requested_songs is None:
                max_songs = min(max_downloadable, 500)  # Practical limit
            else:
                max_songs = min(requested_songs, max_downloadable)

            # Calculate credits required
            credits_required = max_songs * credits_per_song

            # Check final validation
            if credits_required > credit_balance:
                return jsonify({
                    'error': 'Insufficient credits',
                    'credits_required': credits_required,
                    'credits_available': credit_balance,
                    'credits_needed': credits_required - credit_balance,
                    'message': f'You need {credits_required - credit_balance:.2f} more credits to download {max_songs} songs.'
                }), 403

            print(f"Credit-based download: User {user_id} requesting {max_songs} songs " +
                  f"(requires {credits_required} credits, has {credit_balance})")

        finally:
            cursor.close()
            conn.close()

    # Handle FREE TIER logic
    elif plan_type == 'free':
        free_credits = session.get('free_credits', 0)

        # Check if user has any credits
        if free_credits <= 0:
            return jsonify({
                'error': 'No free credits remaining',
                'message': 'Watch an ad to earn more free downloads!',
                'free_credits': 0
            }), 403

        # Limit downloads to available credits
        max_songs = free_credits
        print(f"Free tier session: {session_token} has {free_credits} credits available")

    else:
        # Legacy PAID TIER logic (for old time-based plans)
        # Determine max songs based on plan
        max_songs = session.get('max_songs', 20)
        if max_songs is None:  # Pro plan (unlimited)
            max_songs = 500  # Practical limit per job

    # Apply user's requested song limit if provided
    if requested_songs is not None and plan_type != 'credit':
        max_songs = min(max_songs, requested_songs)

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

    # Build response based on plan type
    response_data = {
        'job_id': job_id,
        'status': 'queued',
        'message': 'Download job created and started',
        'max_songs': max_songs
    }

    # Add credit info for credit-based users
    if plan_type == 'credit':
        response_data['credits_required'] = max_songs * 0.35
        response_data['credits_available'] = credit_balance
        response_data['credits_after'] = credit_balance - (max_songs * 0.35)
        response_data['message'] = 'Download started. Credits will be deducted upon completion.'

    return jsonify(response_data)

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

# ==================== CREDIT-BASED USER ACCOUNT ENDPOINTS ====================

@app.route('/api/users/register', methods=['POST'])
def register_user():
    """
    Register a new user with email + PIN

    Request body:
    {
        "email": "user@example.com",
        "pin": "1234"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        pin = data.get('pin', '').strip()

        # Validate input
        if not email or '@' not in email:
            return jsonify({'error': 'Valid email is required'}), 400

        if not pin or len(pin) < 4 or len(pin) > 6 or not pin.isdigit():
            return jsonify({'error': 'PIN must be 4-6 digits'}), 400

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                return jsonify({'error': 'Email already registered'}), 409

            # Hash PIN
            pin_hashed = hash_pin(pin)

            # Insert new user
            cursor.execute("""
                INSERT INTO users (email, pin_hash, credit_balance, status)
                VALUES (%s, %s, 0.00, 'active')
            """, (email, pin_hashed))

            conn.commit()
            user_id = cursor.lastrowid

            print(f"New user registered: {email} (ID: {user_id})")

            return jsonify({
                'success': True,
                'user_id': user_id,
                'email': email,
                'credit_balance': 0.00,
                'message': 'Account created successfully'
            }), 201

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/login', methods=['POST'])
def login_user():
    """
    Login user with email + PIN

    Request body:
    {
        "email": "user@example.com",
        "pin": "1234"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        pin = data.get('pin', '').strip()

        if not email or not pin:
            return jsonify({'error': 'Email and PIN are required'}), 400

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Get user from database
            cursor.execute("""
                SELECT id, email, pin_hash, credit_balance,
                       total_credits_purchased, total_credits_spent,
                       total_songs_downloaded, status
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()

            if not user:
                return jsonify({'error': 'Invalid email or PIN'}), 401

            if user['status'] != 'active':
                return jsonify({'error': 'Account is suspended or deleted'}), 403

            # Verify PIN
            if not verify_pin(pin, user['pin_hash']):
                return jsonify({'error': 'Invalid email or PIN'}), 401

            # Update last login
            cursor.execute("""
                UPDATE users SET last_login_at = NOW()
                WHERE id = %s
            """, (user['id'],))
            conn.commit()

            # Create session token
            session_token = f"usr_{secrets.token_urlsafe(32)}"
            expires_at = datetime.now() + timedelta(days=7)

            # Store session in memory (should be moved to database/Redis in production)
            active_sessions[session_token] = {
                'user_id': user['id'],
                'email': user['email'],
                'plan_type': 'credit',
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }

            # Calculate songs available
            credits_per_song = 0.35
            songs_available = int(user['credit_balance'] / credits_per_song)

            print(f"User logged in: {email} (ID: {user['id']})")

            return jsonify({
                'success': True,
                'session_token': session_token,
                'user': {
                    'email': user['email'],
                    'credit_balance': float(user['credit_balance']),
                    'songs_available': songs_available,
                    'total_songs_downloaded': user['total_songs_downloaded']
                }
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/balance', methods=['POST'])
def get_user_balance():
    """
    Get user's credit balance and stats

    Request body:
    {
        "session_token": "usr_abc123..."
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        session = active_sessions[session_token]

        # Check session expiration
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            del active_sessions[session_token]
            return jsonify({'error': 'Session expired'}), 401

        user_id = session['user_id']

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Get user balance
            cursor.execute("""
                SELECT email, credit_balance, total_credits_purchased,
                       total_credits_spent, total_songs_downloaded
                FROM users
                WHERE id = %s AND status = 'active'
            """, (user_id,))

            user = cursor.fetchone()

            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Calculate songs available
            credits_per_song = 0.35
            songs_available = int(user['credit_balance'] / credits_per_song)

            return jsonify({
                'email': user['email'],
                'credit_balance': float(user['credit_balance']),
                'songs_available': songs_available,
                'total_credits_purchased': float(user['total_credits_purchased']),
                'total_credits_spent': float(user['total_credits_spent']),
                'total_songs_downloaded': user['total_songs_downloaded']
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Balance check error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/credits/packages', methods=['GET'])
def get_credit_packages():
    """
    Get available credit packages
    """
    try:
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Get active packages
            cursor.execute("""
                SELECT id, package_name, usd_amount, base_credits,
                       bonus_credits, total_credits
                FROM credit_packages
                WHERE is_active = TRUE
                ORDER BY display_order
            """)

            packages = cursor.fetchall()

            # Calculate estimated songs for each package
            credits_per_song = 0.35
            for package in packages:
                package['usd_amount'] = float(package['usd_amount'])
                package['base_credits'] = float(package['base_credits'])
                package['bonus_credits'] = float(package['bonus_credits'])
                package['total_credits'] = float(package['total_credits'])
                package['estimated_songs'] = int(package['total_credits'] / credits_per_song)

            return jsonify({
                'packages': packages
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Get packages error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/credits/purchase', methods=['POST'])
def purchase_credits():
    """
    Purchase credits with E9th token or other payment method

    Request body:
    {
        "session_token": "usr_abc123...",
        "package_id": 2,
        "payment_method": "e9th_stablecoin",
        "tx_hash": "0xabc123...",
        "wallet_address": "0x742d35Cc..."
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        package_id = data.get('package_id')
        payment_method = data.get('payment_method', 'e9th_stablecoin')
        tx_hash = data.get('tx_hash')
        wallet_address = data.get('wallet_address')

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        session = active_sessions[session_token]
        user_id = session['user_id']

        if not package_id:
            return jsonify({'error': 'Package ID is required'}), 400

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # If payment method is e9th_stablecoin, use the e9th deposit procedure
            if payment_method == 'e9th_stablecoin' and tx_hash and wallet_address:
                # Get package details first to get e9th amount
                cursor.execute("""
                    SELECT package_name, usd_amount, base_credits, bonus_credits, total_credits
                    FROM credit_packages
                    WHERE id = %s
                """, (package_id,))
                package = cursor.fetchone()
                
                if not package:
                    return jsonify({'error': 'Invalid package'}), 400
                
                # Use e9th amount = total_credits (1:1 ratio)
                e9th_amount = float(package['total_credits'])
                
                # Call process_e9th_deposit procedure
                cursor.callproc('process_e9th_deposit', [
                    user_id,
                    e9th_amount,
                    tx_hash,
                    wallet_address,
                    package_id,
                    None,  # OUT: success
                    None,  # OUT: error_message
                    None   # OUT: credits_issued
                ])
                
                # Get OUT parameters
                cursor.execute("SELECT @_process_e9th_deposit_5 AS success, @_process_e9th_deposit_6 AS error_message, @_process_e9th_deposit_7 AS credits_issued")
                result = cursor.fetchone()
                
                if not result or not result.get('success'):
                    error_msg = result.get('error_message', 'Purchase failed') if result else 'Purchase failed'
                    conn.rollback()
                    return jsonify({'error': error_msg}), 400
                
                credits_issued = float(result.get('credits_issued', 0))
                
                # Get new balance
                cursor.execute("SELECT credit_balance FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                new_balance = float(user['credit_balance'])
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'package_name': package['package_name'],
                    'usd_amount': float(package['usd_amount']),
                    'base_credits': float(package['base_credits']),
                    'bonus_credits': float(package['bonus_credits']),
                    'total_credits_added': credits_issued,
                    'e9th_amount': e9th_amount,
                    'new_balance': new_balance,
                    'tx_hash': tx_hash,
                    'message': f"Successfully deposited {e9th_amount} e9th tokens. {credits_issued} credits added to your account!"
                })
            else:
                # Use standard add_credits procedure for other payment methods
                cursor.callproc('add_credits', [user_id, package_id, payment_method, tx_hash, None, None])

                # Get OUT parameters (indices 4 and 5 for the OUT parameters)
                cursor.execute("SELECT @_add_credits_4 AS success, @_add_credits_5 AS error_message")
                result = cursor.fetchone()

                if not result or not result.get('success'):
                    error_msg = result.get('error_message', 'Purchase failed') if result else 'Purchase failed'
                    conn.rollback()
                    return jsonify({'error': error_msg}), 400

                # Get package details
                cursor.execute("""
                    SELECT package_name, usd_amount, base_credits, bonus_credits, total_credits
                    FROM credit_packages
                    WHERE id = %s
                """, (package_id,))

                package = cursor.fetchone()

                # Get new balance
                cursor.execute("""
                    SELECT credit_balance FROM users WHERE id = %s
                """, (user_id,))

                user = cursor.fetchone()
                new_balance = float(user['credit_balance'])

                conn.commit()

            print(f"Credits purchased: User {user_id}, Package {package_id}, Amount {package['total_credits']}")

            return jsonify({
                'success': True,
                'package_name': package['package_name'],
                'usd_amount': float(package['usd_amount']),
                'base_credits': float(package['base_credits']),
                'bonus_credits': float(package['bonus_credits']),
                'total_credits_added': float(package['total_credits']),
                'new_balance': new_balance,
                'message': f"Successfully added {package['total_credits']} credits to your account!"
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Purchase credits error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/e9th/deposit', methods=['POST'])
def process_e9th_deposit():
    """
    Process e9th token deposit and issue credits
    
    Request body:
    {
        "session_token": "usr_abc123...",
        "e9th_amount": 25.0,
        "tx_hash": "0xabc123...",
        "wallet_address": "0x742d35Cc...",
        "package_id": 1  // Optional: if depositing for a specific package
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        e9th_amount = data.get('e9th_amount')
        tx_hash = data.get('tx_hash')
        wallet_address = data.get('wallet_address')
        package_id = data.get('package_id')  # Optional

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        session = active_sessions[session_token]
        user_id = session['user_id']

        if not e9th_amount or not tx_hash or not wallet_address:
            return jsonify({'error': 'Missing required fields: e9th_amount, tx_hash, wallet_address'}), 400

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Call stored procedure to process e9th deposit
            cursor.callproc('process_e9th_deposit', [
                user_id, 
                float(e9th_amount), 
                tx_hash, 
                wallet_address, 
                package_id,
                None,  # OUT: success
                None,  # OUT: error_message
                None   # OUT: credits_issued
            ])

            # Get OUT parameters
            cursor.execute("SELECT @_process_e9th_deposit_5 AS success, @_process_e9th_deposit_6 AS error_message, @_process_e9th_deposit_7 AS credits_issued")
            result = cursor.fetchone()

            if not result or not result.get('success'):
                error_msg = result.get('error_message', 'Deposit failed') if result else 'Deposit failed'
                conn.rollback()
                return jsonify({'error': error_msg}), 400

            credits_issued = float(result.get('credits_issued', 0))

            # Get new balance
            cursor.execute("SELECT credit_balance FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            new_balance = float(user['credit_balance'])

            conn.commit()

            print(f"E9th deposit processed: User {user_id}, Amount {e9th_amount} e9th, Credits issued: {credits_issued}")

            return jsonify({
                'success': True,
                'e9th_amount': float(e9th_amount),
                'credits_issued': credits_issued,
                'new_balance': new_balance,
                'tx_hash': tx_hash,
                'message': f'Successfully deposited {e9th_amount} e9th tokens. {credits_issued} credits added to your account!'
            })

        except Exception as e:
            conn.rollback()
            print(f"E9th deposit error: {e}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Process e9th deposit error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/e9th/collections', methods=['GET'])
def get_e9th_collections():
    """
    Get e9th token collections (admin or user-specific)
    
    Query params:
    - session_token: Required for user-specific collections
    - status: Filter by status (pending, collected, transferred, failed)
    - limit: Number of records to return (default: 100)
    """
    try:
        session_token = request.args.get('session_token')
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 100))

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            query = """
                SELECT 
                    ec.id,
                    ec.user_id,
                    u.email,
                    ec.credits_used,
                    ec.e9th_tokens_collected,
                    ec.job_id,
                    ec.songs_downloaded,
                    ec.collection_status,
                    ec.transfer_tx_hash,
                    ec.collected_at,
                    ec.transferred_at
                FROM e9th_collections ec
                JOIN users u ON ec.user_id = u.id
                WHERE 1=1
            """
            params = []

            # Filter by user if session token provided
            if session_token and session_token in active_sessions:
                session = active_sessions[session_token]
                user_id = session.get('user_id')
                if user_id:
                    query += " AND ec.user_id = %s"
                    params.append(user_id)

            # Filter by status
            if status_filter:
                query += " AND ec.collection_status = %s"
                params.append(status_filter)

            query += " ORDER BY ec.collected_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            collections = cursor.fetchall()

            # Convert Decimal to float for JSON serialization
            for collection in collections:
                collection['credits_used'] = float(collection['credits_used'])
                collection['e9th_tokens_collected'] = float(collection['e9th_tokens_collected'])

            return jsonify({
                'success': True,
                'collections': collections,
                'count': len(collections)
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Get e9th collections error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/e9th/transfer', methods=['POST'])
def transfer_collected_e9th():
    """
    Transfer collected e9th tokens to receiving wallet
    
    Request body:
    {
        "session_token": "usr_abc123...",  // Admin session required
        "receiving_wallet_id": 1  // Optional: defaults to active wallet
    }
    
    Note: This endpoint should be called by an admin or automated system
    to transfer collected tokens to the receiving wallet.
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        receiving_wallet_id = data.get('receiving_wallet_id', 1)  # Default to wallet ID 1

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        # TODO: Add admin check here
        # For now, allow any authenticated user (should be restricted to admin)

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Call stored procedure to transfer collected tokens
            cursor.callproc('transfer_collected_e9th', [
                receiving_wallet_id,
                None,  # OUT: success
                None,  # OUT: error_message
                None,  # OUT: transfer_id
                None   # OUT: total_transferred
            ])

            # Get OUT parameters
            cursor.execute("SELECT @_transfer_collected_e9th_2 AS success, @_transfer_collected_e9th_3 AS error_message, @_transfer_collected_e9th_4 AS transfer_id, @_transfer_collected_e9th_5 AS total_transferred")
            result = cursor.fetchone()

            if not result or not result.get('success'):
                error_msg = result.get('error_message', 'Transfer failed') if result else 'Transfer failed'
                conn.rollback()
                return jsonify({'error': error_msg}), 400

            transfer_id = result.get('transfer_id')
            total_transferred = float(result.get('total_transferred', 0))

            # Get receiving wallet address
            cursor.execute("SELECT wallet_address, wallet_name FROM e9th_receiving_wallets WHERE id = %s", (receiving_wallet_id,))
            wallet = cursor.fetchone()

            # Update transfer status to 'processing' (actual blockchain transfer happens externally)
            cursor.execute("UPDATE e9th_transfers SET transfer_status = 'processing' WHERE id = %s", (transfer_id,))

            conn.commit()

            print(f"E9th transfer initiated: Transfer ID {transfer_id}, Amount {total_transferred} e9th tokens")

            return jsonify({
                'success': True,
                'transfer_id': transfer_id,
                'total_tokens_transferred': total_transferred,
                'receiving_wallet': wallet['wallet_address'],
                'wallet_name': wallet['wallet_name'],
                'status': 'processing',
                'message': f'Transfer initiated. {total_transferred} e9th tokens will be transferred to {wallet["wallet_address"]}. Please complete the blockchain transaction.'
            })

        except Exception as e:
            conn.rollback()
            print(f"E9th transfer error: {e}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Transfer collected e9th error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/e9th/transfer/complete', methods=['POST'])
def complete_e9th_transfer():
    """
    Mark e9th token transfer as completed (after blockchain transaction)
    
    Request body:
    {
        "session_token": "usr_abc123...",  // Admin session required
        "transfer_id": 1,
        "tx_hash": "0xabc123...",
        "gas_fee": 0.001  // Optional
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        transfer_id = data.get('transfer_id')
        tx_hash = data.get('tx_hash')
        gas_fee = data.get('gas_fee')

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        if not transfer_id or not tx_hash:
            return jsonify({'error': 'Missing required fields: transfer_id, tx_hash'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Update transfer record
            update_query = """
                UPDATE e9th_transfers 
                SET transfer_status = 'completed',
                    tx_hash = %s,
                    completed_at = NOW()
            """
            params = [tx_hash]

            if gas_fee:
                update_query += ", gas_fee = %s"
                params.append(float(gas_fee))

            update_query += " WHERE id = %s"
            params.append(transfer_id)

            cursor.execute(update_query, params)

            # Update collections with transfer tx hash
            cursor.execute("""
                UPDATE e9th_collections
                SET transfer_tx_hash = %s
                WHERE transfer_id = %s
            """, (tx_hash, transfer_id))

            conn.commit()

            print(f"E9th transfer completed: Transfer ID {transfer_id}, TX Hash {tx_hash}")

            return jsonify({
                'success': True,
                'transfer_id': transfer_id,
                'tx_hash': tx_hash,
                'message': 'Transfer marked as completed'
            })

        except Exception as e:
            conn.rollback()
            print(f"Complete e9th transfer error: {e}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Complete e9th transfer error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/e9th/receiving-wallet', methods=['GET', 'POST'])
def manage_receiving_wallet():
    """
    Get or update receiving wallet configuration
    
    GET: Returns active receiving wallet
    POST: Updates receiving wallet (admin only)
    """
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            if request.method == 'GET':
                # Get active receiving wallet
                cursor.execute("""
                    SELECT id, wallet_address, wallet_name, network, 
                           auto_transfer_enabled, min_collection_threshold
                    FROM e9th_receiving_wallets
                    WHERE is_active = TRUE
                    LIMIT 1
                """)
                wallet = cursor.fetchone()

                if wallet:
                    wallet['min_collection_threshold'] = float(wallet['min_collection_threshold'])
                    return jsonify({
                        'success': True,
                        'wallet': wallet
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'No active receiving wallet configured'
                    }), 404

            elif request.method == 'POST':
                # Update receiving wallet (admin only)
                data = request.get_json()
                session_token = data.get('session_token')

                if not session_token or session_token not in active_sessions:
                    return jsonify({'error': 'Invalid session token'}), 401

                # TODO: Add admin check

                wallet_id = data.get('wallet_id', 1)
                wallet_address = data.get('wallet_address')
                wallet_name = data.get('wallet_name')
                auto_transfer_enabled = data.get('auto_transfer_enabled')
                min_collection_threshold = data.get('min_collection_threshold')

                update_fields = []
                params = []

                if wallet_address:
                    update_fields.append("wallet_address = %s")
                    params.append(wallet_address)

                if wallet_name:
                    update_fields.append("wallet_name = %s")
                    params.append(wallet_name)

                if auto_transfer_enabled is not None:
                    update_fields.append("auto_transfer_enabled = %s")
                    params.append(bool(auto_transfer_enabled))

                if min_collection_threshold is not None:
                    update_fields.append("min_collection_threshold = %s")
                    params.append(float(min_collection_threshold))

                if not update_fields:
                    return jsonify({'error': 'No fields to update'}), 400

                params.append(wallet_id)

                cursor.execute(f"""
                    UPDATE e9th_receiving_wallets
                    SET {', '.join(update_fields)}, updated_at = NOW()
                    WHERE id = %s
                """, params)

                conn.commit()

                return jsonify({
                    'success': True,
                    'message': 'Receiving wallet updated successfully'
                })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Manage receiving wallet error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/transactions', methods=['POST'])
def get_user_transactions():
    """
    Get user's transaction history

    Request body:
    {
        "session_token": "usr_abc123...",
        "limit": 20,
        "offset": 0
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        limit = data.get('limit', 20)
        offset = data.get('offset', 0)

        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        session = active_sessions[session_token]
        user_id = session['user_id']

        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Get transactions
            cursor.execute("""
                SELECT
                    ct.id,
                    ct.transaction_type AS type,
                    ct.amount,
                    ct.balance_after,
                    cp.package_name,
                    ct.songs_downloaded,
                    ct.notes,
                    ct.created_at
                FROM credit_transactions ct
                LEFT JOIN credit_packages cp ON ct.package_id = cp.id
                WHERE ct.user_id = %s
                ORDER BY ct.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))

            transactions = cursor.fetchall()

            # Get total count
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM credit_transactions
                WHERE user_id = %s
            """, (user_id,))

            total_count = cursor.fetchone()['total']

            # Format transactions
            for txn in transactions:
                txn['amount'] = float(txn['amount'])
                txn['balance_after'] = float(txn['balance_after'])
                txn['created_at'] = txn['created_at'].isoformat() if txn['created_at'] else None

            return jsonify({
                'transactions': transactions,
                'total_count': total_count
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Get transactions error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== FREE TIER ENDPOINTS ====================

# In-memory storage for ad views (should be moved to database in production)
ad_views = {}

@app.route('/api/session/free', methods=['POST'])
def create_free_session():
    """
    Create a free session with 3 initial credits

    Request body:
    {
        "ip_address": "192.168.1.1",  # Optional, will use request IP if not provided
        "user_agent": "Mozilla/5.0..."  # Optional
    }

    Response:
    {
        "session_token": "free_abc123...",
        "plan_type": "free",
        "free_credits": 3,
        "expires_at": "2025-11-26T12:00:00Z"
    }
    """
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address') or request.remote_addr
        user_agent = data.get('user_agent') or request.headers.get('User-Agent', '')

        # Check if IP created free session in last 24 hours (abuse prevention)
        cutoff_time = datetime.now() - timedelta(hours=24)
        for token, session in active_sessions.items():
            if (session.get('plan_type') == 'free' and
                session.get('ip_address') == ip_address and
                datetime.fromisoformat(session.get('created_at', '2020-01-01')) > cutoff_time):
                return jsonify({
                    'error': 'You already have an active free session. Please wait 24 hours or upgrade to a paid plan.'
                }), 429

        # Create free session token
        session_token = f"free_{secrets.token_urlsafe(32)}"
        expires_at = datetime.now() + timedelta(hours=24)

        # Store session
        active_sessions[session_token] = {
            'plan_type': 'free',
            'plan_name': 'Free Tier',
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'free_credits': 3,  # 3 initial free downloads
            'ads_watched': 0,
            'songs_downloaded': 0,
            'max_songs': None,  # Will be limited by credits
            'ip_address': ip_address,
            'user_agent': user_agent
        }

        print(f"Created free session: {session_token} for IP: {ip_address}")

        return jsonify({
            'session_token': session_token,
            'plan_type': 'free',
            'free_credits': 3,
            'expires_at': expires_at.isoformat(),
            'message': 'Free session created! You have 3 free downloads.'
        })

    except Exception as e:
        print(f"Error creating free session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ad/start', methods=['POST'])
def start_ad_view():
    """
    Start an ad view session for Google AdSense

    Request body:
    {
        "session_token": "free_abc123...",
        "ad_network": "google_adsense"  # Optional, defaults to google_adsense
    }

    Response:
    {
        "ad_id": "ad_xyz789...",
        "required_duration": 45,
        "ad_network": "google_adsense",
        "message": "Watch the full ad to earn 1 free download!"
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        ad_network = data.get('ad_network', 'google_adsense')

        # Validate session exists and is free tier
        if not session_token or session_token not in active_sessions:
            return jsonify({'error': 'Invalid session token'}), 401

        session = active_sessions[session_token]

        if session.get('plan_type') != 'free':
            return jsonify({'error': 'Ad viewing is only for free tier users'}), 400

        # Check if session is expired
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({'error': 'Session expired'}), 401

        # Check if user has credits remaining (optional - allow watching ads even with credits)
        # This allows users to build up credits

        # Generate unique ad ID
        ad_id = f"ad_{secrets.token_urlsafe(16)}"

        # Store ad view record
        ad_views[ad_id] = {
            'session_token': session_token,
            'ad_network': ad_network,
            'required_duration': 45,  # 45 seconds minimum watch time
            'actual_duration': 0,
            'completed': False,
            'credit_granted': False,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }

        print(f"Started ad view: {ad_id} for session: {session_token}")

        return jsonify({
            'ad_id': ad_id,
            'required_duration': 45,
            'ad_network': ad_network,
            'message': 'Watch the full Google AdSense ad (45 seconds) to earn 1 free download!'
        })

    except Exception as e:
        print(f"Error starting ad view: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ad/complete', methods=['POST'])
def complete_ad_view():
    """
    Mark ad as complete and grant credit

    Request body:
    {
        "session_token": "free_abc123...",
        "ad_id": "ad_xyz789...",
        "actual_duration": 47  # Seconds watched
    }

    Response:
    {
        "success": true,
        "credit_granted": true,
        "free_credits": 4,
        "message": "You earned 1 free download!"
    }
    """
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        ad_id = data.get('ad_id')
        actual_duration = data.get('actual_duration', 0)

        # Validate ad exists
        if not ad_id or ad_id not in ad_views:
            return jsonify({'error': 'Invalid ad ID'}), 404

        ad = ad_views[ad_id]

        # Validate ad belongs to this session
        if ad['session_token'] != session_token:
            return jsonify({'error': 'Ad does not belong to this session'}), 403

        # Check if credit already granted
        if ad['credit_granted']:
            return jsonify({'error': 'Credit already granted for this ad'}), 400

        # Validate session exists
        if session_token not in active_sessions:
            return jsonify({'error': 'Invalid session'}), 401

        session = active_sessions[session_token]

        # Check if session is expired
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({'error': 'Session expired'}), 401

        # Validate duration requirement (must watch at least 45 seconds)
        if actual_duration < 45:
            return jsonify({
                'error': f'Must watch full ad. You watched {actual_duration} seconds, need 45 seconds.',
                'watched': actual_duration,
                'required': 45
            }), 400

        # Mark ad as completed
        ad['completed'] = True
        ad['credit_granted'] = True
        ad['actual_duration'] = actual_duration
        ad['completed_at'] = datetime.now().isoformat()

        # Grant credit to session
        current_credits = session.get('free_credits', 0)
        session['free_credits'] = current_credits + 1
        session['ads_watched'] = session.get('ads_watched', 0) + 1

        # Limit max credits to prevent farming (max 20 ad credits per session)
        if session['free_credits'] > 23:  # 3 initial + 20 from ads
            session['free_credits'] = 23

        new_credits = session['free_credits']

        print(f"Granted credit: {ad_id} -> session: {session_token} (now has {new_credits} credits)")

        return jsonify({
            'success': True,
            'credit_granted': True,
            'free_credits': new_credits,
            'ads_watched': session['ads_watched'],
            'message': f'You earned 1 free download! Total credits: {new_credits}'
        })

    except Exception as e:
        print(f"Error completing ad view: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Development server
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
