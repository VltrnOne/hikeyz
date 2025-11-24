#!/usr/bin/env python3
"""
Test script to verify the complete API integration
"""

import requests
import time
import json
from datetime import datetime, timedelta

# Test configuration
API_BASE = "http://localhost:5000"

def test_api_integration():
    """Test the complete API flow"""

    print("="*60)
    print("TESTING API INTEGRATION")
    print("="*60)

    # Step 1: Manually create a test session (simulating successful payment)
    print("\n1. Creating test session...")

    from api.app import active_sessions, PRICING_PLANS
    import secrets

    session_token = secrets.token_urlsafe(32)
    plan = PRICING_PLANS['quick']
    expires_at = datetime.now() + timedelta(minutes=plan['duration_minutes'])

    active_sessions[session_token] = {
        'plan_type': 'quick',
        'plan_name': plan['name'],
        'created_at': datetime.now().isoformat(),
        'expires_at': expires_at.isoformat(),
        'max_songs': plan['max_songs'],
        'songs_downloaded': 0,
        'client_reference_id': 'test_client',
        'stripe_session_id': 'test_session_123'
    }

    print(f"✓ Session created: {session_token[:20]}...")

    # Step 2: Validate session
    print("\n2. Validating session...")

    response = requests.post(
        f"{API_BASE}/api/validate-session",
        json={'session_token': session_token}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('valid'):
            print(f"✓ Session valid: {data['session']['plan_name']}")
            print(f"  Max songs: {data['session']['max_songs']}")
        else:
            print(f"✗ Session invalid: {data.get('error')}")
            return
    else:
        print(f"✗ Validation failed: {response.status_code}")
        return

    # Step 3: Start download job
    print("\n3. Starting download job...")

    response = requests.post(
        f"{API_BASE}/api/start-download",
        json={
            'session_token': session_token,
            'suno_credentials': {
                'method': 'chrome_debug',
                'data': {}
            }
        }
    )

    if response.status_code == 200:
        data = response.json()
        job_id = data.get('job_id')
        print(f"✓ Job started: {job_id}")
        print(f"  Status: {data.get('status')}")
        print(f"  Max songs: {data.get('max_songs')}")
    else:
        print(f"✗ Failed to start job: {response.status_code}")
        print(f"  Error: {response.text}")
        return

    # Step 4: Poll job status
    print("\n4. Monitoring download progress...")
    print("-" * 60)

    last_downloaded = 0
    check_count = 0
    max_checks = 60  # 2 minutes at 2-second intervals

    while check_count < max_checks:
        check_count += 1

        response = requests.get(f"{API_BASE}/api/job-status/{job_id}")

        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            progress = data.get('progress', {})

            downloaded = progress.get('downloaded', 0)
            total = progress.get('total_songs', 0)
            failed = progress.get('failed', 0)
            current = progress.get('current_song', 'N/A')

            # Print update if progress changed
            if downloaded != last_downloaded or check_count == 1:
                print(f"\n[Check {check_count}] Status: {status}")
                print(f"  Progress: {downloaded}/{total} songs")
                print(f"  Failed: {failed}")
                print(f"  Current: {current}")
                last_downloaded = downloaded

            # Check if completed
            if status == 'completed':
                print("\n✓ Download completed!")
                print(f"  Total downloaded: {downloaded}")
                print(f"  Total failed: {failed}")

                zip_path = data.get('zip_path')
                if zip_path:
                    print(f"  ZIP file: {zip_path}")

                break

            # Check if failed
            if status == 'failed':
                error = progress.get('error_message')
                print(f"\n✗ Download failed: {error}")
                break

        else:
            print(f"✗ Failed to get status: {response.status_code}")
            break

        # Wait before next check
        time.sleep(2)

    if check_count >= max_checks:
        print("\n⚠ Timeout: Job still running after 2 minutes")
        print("  This is normal for large downloads")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    # Note: This test requires the Flask API to be running
    print("\nNOTE: Make sure the Flask API is running on port 5000")
    print("Run: python3 api/app.py\n")

    input("Press Enter when API is ready...")

    try:
        test_api_integration()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
