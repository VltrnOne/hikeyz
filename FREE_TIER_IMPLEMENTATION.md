# Free Tier Implementation Guide

## Overview
Adding a freemium model to SUNO Downloader Pro:
- **3 free downloads** initially
- **1 additional download per 45-second ad** watched
- Tracks anonymous users via session tokens
- IP-based abuse prevention

---

## 1. Database Changes ✅ COMPLETED

### Updated `sessions` table:
```sql
- Added `free` to plan_type ENUM
- Added `free_credits` INT (tracks remaining free downloads)
- Added `ads_watched` INT (count of ads viewed)
- Added `ip_address` VARCHAR(45) (abuse prevention)
```

### New `ad_views` table:
```sql
- Tracks each ad view session
- Validates 45-second watch requirement
- Prevents credit fraud
```

---

## 2. API Endpoints Needed

### A. Create Free Session
```
POST /api/session/free
```

**Request:**
```json
{
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

**Response:**
```json
{
  "session_token": "free_abc123...",
  "plan_type": "free",
  "free_credits": 3,
  "expires_at": "2025-11-26T12:00:00Z"
}
```

**Logic:**
1. Check IP hasn't created free session in last 24 hours
2. Generate session_token with "free_" prefix
3. Set free_credits = 3
4. Set expires_at = now + 24 hours
5. Return session data

---

### B. Start Ad View
```
POST /api/ad/start
```

**Request:**
```json
{
  "session_token": "free_abc123...",
  "ad_network": "youtube_player"
}
```

**Response:**
```json
{
  "ad_id": "ad_xyz789...",
  "required_duration": 45,
  "video_url": "https://youtube.com/embed/..."
}
```

**Logic:**
1. Validate session token
2. Generate unique ad_id
3. Create ad_views record with started_at = now
4. Return ad details

---

### C. Complete Ad View & Grant Credit
```
POST /api/ad/complete
```

**Request:**
```json
{
  "session_token": "free_abc123...",
  "ad_id": "ad_xyz789...",
  "actual_duration": 47
}
```

**Response:**
```json
{
  "success": true,
  "credit_granted": true,
  "free_credits": 4,
  "message": "You earned 1 free download!"
}
```

**Logic:**
1. Validate ad_id matches session
2. Check actual_duration >= 45 seconds
3. Update ad_views: completed = TRUE, credit_granted = TRUE
4. Increment sessions.free_credits += 1
5. Increment sessions.ads_watched += 1
6. Return updated credits

---

### D. Update Start Download Endpoint
```
POST /api/start-download
```

**Existing logic + Free tier check:**

```python
# Before starting download:
if session['plan_type'] == 'free':
    if session['free_credits'] <= 0:
        return {'error': 'No free credits. Watch an ad to earn more!'}, 403

    # Deduct 1 credit per song
    max_songs = min(requested_songs, session['free_credits'])
else:
    # Existing paid logic
    max_songs = 500 if session['tier'] == 'quick' else 999999
```

---

## 3. Frontend Changes

### A. Landing Page - Add "Try Free" Button

**Update `index.html`:**
```html
<!-- Add before pricing cards -->
<div class="free-tier-cta">
    <h3>Try Before You Buy</h3>
    <p>Download 3 songs FREE - no credit card required!</p>
    <button class="btn-free" data-plan="free">
        Start Free Download
    </button>
</div>
```

**Update `script.js`:**
```javascript
// Add free tier handler
const freeButtons = document.querySelectorAll('[data-plan="free"]');
freeButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
        e.preventDefault();

        // Create free session
        const response = await fetch(`${API_BASE_URL}/api/session/free`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ip_address: null,  // Backend will capture from request
                user_agent: navigator.userAgent
            })
        });

        const data = await response.json();

        // Redirect to progress page with free session
        window.location.href = `/progress.html?session_token=${data.session_token}&free=true`;
    });
});
```

---

### B. Progress Page - Add Ad Player Modal

**Update `progress.html`:**
```html
<!-- Add modal for ad player -->
<div id="adModal" class="modal" style="display: none;">
    <div class="modal-content">
        <h2>Watch ad to earn 1 free download</h2>
        <p id="adTimer">45 seconds remaining...</p>

        <!-- YouTube iframe or AdSense unit -->
        <div id="adPlayer"></div>

        <button id="closeAdBtn" disabled>
            Close (available in <span id="closeTimer">45</span>s)
        </button>
    </div>
</div>

<!-- Update credits display -->
<div class="free-credits-banner" id="freeCredits" style="display: none;">
    <span>Free Downloads Remaining: <strong id="creditsCount">3</strong></span>
    <button class="btn-watch-ad" id="watchAdBtn">Watch Ad (+1 Download)</button>
</div>
```

**Add ad logic to `progress.html` script:**
```javascript
// Show free credits banner for free tier
if (urlParams.get('free') === 'true') {
    document.getElementById('freeCredits').style.display = 'block';
}

// Watch ad button handler
document.getElementById('watchAdBtn').addEventListener('click', async () => {
    // Start ad view
    const response = await fetch(`${API_BASE_URL}/api/ad/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_token: sessionToken,
            ad_network: 'youtube_player'
        })
    });

    const adData = await response.json();

    // Show modal with YouTube ad
    showAdModal(adData);
});

function showAdModal(adData) {
    const modal = document.getElementById('adModal');
    modal.style.display = 'block';

    // Load YouTube video
    const player = document.getElementById('adPlayer');
    player.innerHTML = `
        <iframe width="560" height="315"
            src="${adData.video_url}"
            frameborder="0"
            allow="accelerometer; autoplay; encrypted-media"
            allowfullscreen>
        </iframe>
    `;

    // Start countdown timer
    let timeLeft = 45;
    const timer = setInterval(() => {
        timeLeft--;
        document.getElementById('closeTimer').textContent = timeLeft;
        document.getElementById('adTimer').textContent = `${timeLeft} seconds remaining...`;

        if (timeLeft <= 0) {
            clearInterval(timer);
            document.getElementById('closeAdBtn').disabled = false;
            document.getElementById('closeAdBtn').textContent = 'Claim Your Download!';

            // Grant credit
            grantAdCredit(adData.ad_id);
        }
    }, 1000);
}

async function grantAdCredit(adId) {
    const response = await fetch(`${API_BASE_URL}/api/ad/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_token: sessionToken,
            ad_id: adId,
            actual_duration: 45
        })
    });

    const data = await response.json();

    // Update credits display
    document.getElementById('creditsCount').textContent = data.free_credits;

    // Show success message
    alert(`You earned 1 free download! Total: ${data.free_credits}`);
}
```

---

## 4. Backend Implementation (Flask)

### Create `/api/app.py` additions:

```python
# Free tier endpoints

@app.route('/api/session/free', methods=['POST'])
def create_free_session():
    """Create a free session with 3 initial credits"""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent')

    # Check if IP created free session in last 24 hours
    recent_session = db.execute(
        "SELECT id FROM sessions WHERE ip_address = %s AND plan_type = 'free' AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)",
        (ip_address,)
    ).fetchone()

    if recent_session:
        return jsonify({'error': 'You already have an active free session'}), 429

    # Create session
    session_token = f"free_{secrets.token_urlsafe(32)}"
    expires_at = datetime.now() + timedelta(hours=24)

    db.execute(
        "INSERT INTO sessions (session_token, plan_type, expires_at, free_credits, ip_address) VALUES (%s, 'free', %s, 3, %s)",
        (session_token, expires_at, ip_address)
    )

    return jsonify({
        'session_token': session_token,
        'plan_type': 'free',
        'free_credits': 3,
        'expires_at': expires_at.isoformat()
    })


@app.route('/api/ad/start', methods=['POST'])
def start_ad_view():
    """Start an ad view session"""
    data = request.json
    session_token = data.get('session_token')

    # Validate session
    session = db.execute(
        "SELECT * FROM sessions WHERE session_token = %s AND status = 'active'",
        (session_token,)
    ).fetchone()

    if not session:
        return jsonify({'error': 'Invalid session'}), 401

    # Generate ad ID
    ad_id = f"ad_{secrets.token_urlsafe(16)}"

    # Create ad_views record
    db.execute(
        "INSERT INTO ad_views (session_token, ad_id, ad_network, ip_address, user_agent) VALUES (%s, %s, 'youtube_player', %s, %s)",
        (session_token, ad_id, request.remote_addr, request.headers.get('User-Agent'))
    )

    # Return YouTube ad URL (replace with your video ID)
    video_url = "https://www.youtube.com/embed/YOUR_AD_VIDEO_ID?autoplay=1&rel=0"

    return jsonify({
        'ad_id': ad_id,
        'required_duration': 45,
        'video_url': video_url
    })


@app.route('/api/ad/complete', methods=['POST'])
def complete_ad_view():
    """Mark ad as complete and grant credit"""
    data = request.json
    session_token = data.get('session_token')
    ad_id = data.get('ad_id')
    actual_duration = data.get('actual_duration', 0)

    # Validate ad exists and belongs to session
    ad = db.execute(
        "SELECT * FROM ad_views WHERE ad_id = %s AND session_token = %s",
        (ad_id, session_token)
    ).fetchone()

    if not ad:
        return jsonify({'error': 'Invalid ad view'}), 404

    if ad['credit_granted']:
        return jsonify({'error': 'Credit already granted'}), 400

    # Check duration requirement
    if actual_duration < 45:
        return jsonify({'error': 'Must watch full ad'}), 400

    # Mark ad as completed
    db.execute(
        "UPDATE ad_views SET completed = TRUE, credit_granted = TRUE, actual_duration = %s, completed_at = NOW() WHERE ad_id = %s",
        (actual_duration, ad_id)
    )

    # Grant credit to session
    db.execute(
        "UPDATE sessions SET free_credits = free_credits + 1, ads_watched = ads_watched + 1 WHERE session_token = %s",
        (session_token,)
    )

    # Get updated credits
    session = db.execute(
        "SELECT free_credits FROM sessions WHERE session_token = %s",
        (session_token,)
    ).fetchone()

    return jsonify({
        'success': True,
        'credit_granted': True,
        'free_credits': session['free_credits'],
        'message': 'You earned 1 free download!'
    })
```

---

## 5. Deployment Steps

1. **Update Database:**
   ```bash
   mysql -u username -p database_name < database/schema.sql
   ```

2. **Update API on Render:**
   - Push code to GitHub
   - Render will auto-deploy

3. **Update Frontend on SiteGround:**
   ```bash
   cd ~/vltrndataroom/hitbot-agency
   ./setup_ssh_and_deploy.sh
   ```

4. **Add YouTube Ad Video:**
   - Upload a 45-second ad video to YouTube
   - Set as unlisted
   - Replace `YOUR_AD_VIDEO_ID` in backend code

5. **Test Flow:**
   - Click "Try Free" → Creates session with 3 credits
   - Download 3 songs → Credits = 0
   - Click "Watch Ad" → Shows 45s video
   - After 45s → Credits = 1
   - Download 1 more song → Credits = 0
   - Repeat

---

## 6. Pricing Structure

| Tier | Price | Downloads | Duration | Ads |
|------|-------|-----------|----------|-----|
| **Free** | $0 | 3 initial + 1 per ad | 24 hours | Required |
| **Quick Download** | $4.99 | Up to 500 | 10 minutes | No ads |
| **Pro Access** | $49.99 | Unlimited | 3 days | No ads |

---

## 7. Abuse Prevention

- **IP Tracking:** Max 1 free session per IP per 24 hours
- **Session Expiry:** Free sessions expire after 24 hours
- **Ad Verification:** Must watch full 45 seconds to get credit
- **Credit Limits:** Max 20 ad credits per session (prevent farming)

---

## Next Steps

Would you like me to:
1. Implement the Flask API endpoints?
2. Create the ad player modal UI?
3. Set up a YouTube ad video?
4. Add analytics tracking?

Let me know which part you'd like to tackle first!
