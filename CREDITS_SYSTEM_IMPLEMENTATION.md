# Credit-Based Account System Implementation

## Overview

Transition from time-based pricing to **credit-based prepaid accounts** with E9th token integration.

---

## Pricing Model

### Credit Economics
- **1 USD = 1 Credit**
- **1 Song Download = 0.35 Credits**
- **Example**: $100 purchase = 100 credits = ~285 songs

### Prepaid Packages with Bonuses

| Package | Pay | Base Credits | Bonus | Total Credits | Total Songs |
|---------|-----|--------------|-------|---------------|-------------|
| **Starter** | $25 | 25 | +15 | **40** | ~114 songs |
| **Popular** | $50 | 50 | +25 | **75** | ~214 songs |
| **Premium** | $100 | 100 | +100 | **200** | ~571 songs |

---

## E9th Token Integration

### Deposit Flow
1. User deposits **E9th Stablecoins** (pegged to USD)
2. System converts 1:1 to **E9th Utility Tokens**
3. Utility tokens stored as credit balance
4. Credits deducted per song download (0.35 per song)

### Blockchain Recording
- All deposits recorded with transaction hash
- Confirmation tracking (pending → confirmed)
- Transparent, auditable credit issuance
- Wallet address linked to user account

---

## User Authentication

### Email + PIN System
- **No passwords** - simplified authentication
- **Email**: Primary identifier
- **PIN**: 4-6 digit numeric code (hashed with bcrypt)
- **Security**: PIN rate limiting, account lockout after failed attempts

### Account Structure
```
User Account:
  - Email (unique)
  - PIN (hashed)
  - Credit Balance (E9th utility tokens)
  - E9th Wallet Address
  - Transaction History
  - Download History
```

---

## API Endpoints (New)

### 1. User Registration
**POST `/api/users/register`**

Request:
```json
{
  "email": "user@example.com",
  "pin": "1234"
}
```

Response:
```json
{
  "success": true,
  "user_id": 123,
  "email": "user@example.com",
  "credit_balance": 0.00,
  "message": "Account created successfully"
}
```

---

### 2. User Login
**POST `/api/users/login`**

Request:
```json
{
  "email": "user@example.com",
  "pin": "1234"
}
```

Response:
```json
{
  "success": true,
  "session_token": "usr_abc123...",
  "user": {
    "email": "user@example.com",
    "credit_balance": 45.50,
    "songs_available": 130,
    "total_songs_downloaded": 25
  }
}
```

---

### 3. Get Credit Balance
**POST `/api/users/balance`**

Request:
```json
{
  "session_token": "usr_abc123..."
}
```

Response:
```json
{
  "email": "user@example.com",
  "credit_balance": 45.50,
  "songs_available": 130,
  "total_credits_purchased": 75.00,
  "total_credits_spent": 29.50,
  "total_songs_downloaded": 84
}
```

---

### 4. Purchase Credits
**POST `/api/credits/purchase`**

Request:
```json
{
  "session_token": "usr_abc123...",
  "package_id": 2,
  "payment_method": "e9th_stablecoin",
  "tx_hash": "0xabc123...",
  "wallet_address": "0x742d35Cc..."
}
```

Response:
```json
{
  "success": true,
  "package_name": "Popular Pack",
  "usd_amount": 50.00,
  "base_credits": 50.00,
  "bonus_credits": 25.00,
  "total_credits_added": 75.00,
  "new_balance": 120.50,
  "transaction_id": 456
}
```

---

### 5. Get Available Packages
**GET `/api/credits/packages`**

Response:
```json
{
  "packages": [
    {
      "id": 1,
      "name": "Starter Pack",
      "usd_amount": 25.00,
      "base_credits": 25.00,
      "bonus_credits": 15.00,
      "total_credits": 40.00,
      "estimated_songs": 114
    },
    {
      "id": 2,
      "name": "Popular Pack",
      "usd_amount": 50.00,
      "base_credits": 50.00,
      "bonus_credits": 25.00,
      "total_credits": 75.00,
      "estimated_songs": 214
    },
    {
      "id": 3,
      "name": "Premium Pack",
      "usd_amount": 100.00,
      "base_credits": 100.00,
      "bonus_credits": 100.00,
      "total_credits": 200.00,
      "estimated_songs": 571
    }
  ]
}
```

---

### 6. Transaction History
**POST `/api/users/transactions`**

Request:
```json
{
  "session_token": "usr_abc123...",
  "limit": 20,
  "offset": 0
}
```

Response:
```json
{
  "transactions": [
    {
      "id": 789,
      "type": "purchase",
      "amount": 50.00,
      "balance_after": 120.50,
      "package_name": "Popular Pack",
      "created_at": "2025-11-25T14:30:00Z"
    },
    {
      "id": 788,
      "type": "bonus",
      "amount": 25.00,
      "balance_after": 70.50,
      "notes": "Bonus credits for package purchase",
      "created_at": "2025-11-25T14:30:05Z"
    },
    {
      "id": 787,
      "type": "deduction",
      "amount": -10.50,
      "balance_after": 45.50,
      "songs_downloaded": 30,
      "created_at": "2025-11-25T10:15:00Z"
    }
  ],
  "total_count": 45
}
```

---

### 7. Start Download (Updated for Credits)
**POST `/api/start-download`**

Request:
```json
{
  "session_token": "usr_abc123...",
  "requested_songs": 50
}
```

Response (Success):
```json
{
  "job_id": "job_xyz789",
  "max_songs": 50,
  "credits_required": 17.50,
  "credits_available": 45.50,
  "credits_after": 28.00,
  "message": "Download started. Credits will be deducted upon completion."
}
```

Response (Insufficient Credits):
```json
{
  "error": "Insufficient credits",
  "credits_required": 17.50,
  "credits_available": 10.00,
  "credits_needed": 7.50,
  "message": "You need 7.50 more credits to download 50 songs. Please purchase more credits."
}
```

---

## Frontend Changes Needed

### 1. Updated Pricing Cards (index.html)

Replace existing pricing section with:

```html
<!-- Free Tier - Keep for ad-supported users -->
<div class="pricing-card free-tier">
    <h3>Free Tier</h3>
    <div class="price">$0</div>
    <p>3 free downloads + watch ads for more</p>
</div>

<!-- Starter Pack -->
<div class="pricing-card">
    <h3>Starter Pack</h3>
    <div class="price">$25</div>
    <div class="bonus-badge">+$15 Bonus</div>
    <p>40 Credits Total</p>
    <ul>
        <li>~114 song downloads</li>
        <li>E9th utility tokens</li>
        <li>60% bonus credits</li>
        <li>Never expires</li>
    </ul>
</div>

<!-- Popular Pack -->
<div class="pricing-card featured">
    <div class="badge-featured">MOST POPULAR</div>
    <h3>Popular Pack</h3>
    <div class="price">$50</div>
    <div class="bonus-badge">+$25 Bonus</div>
    <p>75 Credits Total</p>
    <ul>
        <li>~214 song downloads</li>
        <li>E9th utility tokens</li>
        <li>50% bonus credits</li>
        <li>Never expires</li>
    </ul>
</div>

<!-- Premium Pack -->
<div class="pricing-card premium">
    <div class="badge-premium">BEST VALUE</div>
    <h3>Premium Pack</h3>
    <div class="price">$100</div>
    <div class="bonus-badge">+$100 Bonus</div>
    <p>200 Credits Total</p>
    <ul>
        <li>~571 song downloads</li>
        <li>E9th utility tokens</li>
        <li>100% bonus credits</li>
        <li>Never expires</li>
    </ul>
</div>
```

### 2. Account Dashboard Page (NEW)

Create `dashboard.html`:
- Credit balance display
- Purchase credits button
- Transaction history table
- Download history
- E9th wallet connection

### 3. Login/Register Modal

Add modal for:
- Email + PIN login
- New account registration
- Forgot PIN recovery

---

## Database Migration Steps

1. **Backup existing database**
```bash
mysqldump -u root -p hikeyz_db > backup_$(date +%Y%m%d).sql
```

2. **Run new schema**
```bash
mysql -u root -p hikeyz_db < database/schema_credits.sql
```

3. **Verify tables created**
```sql
SHOW TABLES;
SELECT * FROM credit_packages;
SELECT * FROM pricing_config;
```

---

## E9th Token Smart Contract Integration

### Required Smart Contract Functions

```solidity
// E9th Stablecoin → Utility Token Conversion
function depositStablecoin(uint256 amount) external returns (uint256 utilityTokens);

// Check user balance
function balanceOf(address user) external view returns (uint256);

// Deduct tokens on download
function deductTokens(address user, uint256 amount) external returns (bool);

// Admin: Issue bonus tokens
function issueBonusTokens(address user, uint256 amount) external onlyAdmin;
```

### Integration Flow

1. User deposits E9th stablecoins to contract
2. Contract emits event with transaction hash
3. Backend listens for event
4. Backend calls `/api/credits/purchase` with tx_hash
5. System confirms transaction on blockchain
6. Credits added to user account

---

## Security Considerations

### PIN Security
- Hash PINs with bcrypt (cost factor 12)
- Rate limit login attempts (5 per 15 minutes)
- Lock account after 10 failed attempts
- Email notification on suspicious activity

### Credit Protection
- Database transactions for atomicity
- Stored procedures prevent race conditions
- Audit trail for all credit changes
- Admin approval for refunds/adjustments

### E9th Integration
- Verify transaction confirmations (minimum 3 blocks)
- Check transaction belongs to user's wallet
- Prevent double-spending with tx_hash uniqueness
- Monitor for fraudulent deposits

---

## Migration from Old System

### Option 1: Hard Cutover
- Deploy new system with credit-based pricing
- Keep free tier for ad-supported users
- Deprecate $4.99 and $49.99 time-based plans

### Option 2: Gradual Migration
- Run both systems in parallel
- Convert existing paid users to equivalent credits
- Phase out time-based plans over 30 days

### Conversion Table (if migrating existing users)
| Old Plan | Price | Convert To |
|----------|-------|------------|
| Quick Download (10 min) | $4.99 | 5 credits |
| Pro Access (3 days) | $49.99 | 50 credits |

---

## Testing Checklist

- [ ] User registration with email + PIN
- [ ] User login authentication
- [ ] Credit balance checking
- [ ] Package purchase with E9th deposit
- [ ] Bonus credits automatically added
- [ ] Download deducts correct credits (0.35 per song)
- [ ] Insufficient credits error handling
- [ ] Transaction history accuracy
- [ ] E9th wallet integration
- [ ] Free tier still works for ad users
- [ ] PIN rate limiting works
- [ ] Account lockout after failed attempts

---

## Next Steps

1. **Backend API** - Implement new endpoints in `api/app.py`
2. **Frontend** - Update pricing cards and add dashboard
3. **E9th Contract** - Deploy or connect to existing E9th token contract
4. **Testing** - End-to-end testing of credit flow
5. **Deploy** - Push to production (Render + SiteGround)
6. **Monitor** - Track credit transactions and user adoption

---

**Status**: Database schema complete. API implementation next.
