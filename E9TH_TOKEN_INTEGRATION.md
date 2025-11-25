# E9th Token Integration Guide

## Overview

This system integrates E9th tokens for credit purchases and automatically collects E9th tokens when users spend credits. Collected tokens are transferred to a receiving wallet.

## Architecture

### Flow Diagram

```
User Deposits E9th Tokens
    ↓
E9th Stablecoins → Utility Tokens (1:1 ratio)
    ↓
Credits Added to User Account
    ↓
User Downloads Songs (Credits Deducted)
    ↓
E9th Tokens Collected (if user paid with E9th)
    ↓
Tokens Transferred to Receiving Wallet
```

## Database Schema

### New Tables

1. **e9th_collections** - Tracks tokens collected when credits are used
   - Links to user, transaction, and download job
   - Records collection status (pending, collected, transferred, failed)
   - Stores transfer transaction hash

2. **e9th_receiving_wallets** - Configuration for receiving wallets
   - Stores wallet address, network, auto-transfer settings
   - Supports multiple wallets with active/inactive status

3. **e9th_transfers** - Records of token transfers to receiving wallet
   - Links multiple collections into a single transfer
   - Tracks transfer status and blockchain transaction hash

### Updated Stored Procedures

1. **deduct_credits** - Updated to automatically collect E9th tokens
   - Checks if user originally paid with E9th tokens
   - Collects equivalent tokens (1 credit = 1 e9th token)
   - Records collection in `e9th_collections` table

2. **process_e9th_deposit** - New procedure for E9th deposits
   - Processes E9th stablecoin deposits
   - Issues utility tokens (credits) at 1:1 ratio
   - Records deposit in `e9th_deposits` table
   - Updates user's wallet address

3. **transfer_collected_e9th** - New procedure for token transfers
   - Aggregates all collected tokens
   - Creates transfer record
   - Updates collection statuses

## API Endpoints

### 1. Process E9th Deposit
**POST `/api/e9th/deposit`**

Processes an E9th token deposit and issues credits.

**Request:**
```json
{
  "session_token": "usr_abc123...",
  "e9th_amount": 25.0,
  "tx_hash": "0xabc123...",
  "wallet_address": "0x742d35Cc...",
  "package_id": 1  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "e9th_amount": 25.0,
  "credits_issued": 40.0,
  "new_balance": 40.0,
  "tx_hash": "0xabc123...",
  "message": "Successfully deposited 25.0 e9th tokens. 40.0 credits added to your account!"
}
```

### 2. Get E9th Collections
**GET `/api/e9th/collections`**

Retrieves collection history (admin or user-specific).

**Query Parameters:**
- `session_token` - Required for user-specific collections
- `status` - Filter by status (pending, collected, transferred, failed)
- `limit` - Number of records (default: 100)

**Response:**
```json
{
  "success": true,
  "collections": [
    {
      "id": 1,
      "user_id": 123,
      "email": "user@example.com",
      "credits_used": 3.5,
      "e9th_tokens_collected": 3.5,
      "collection_status": "collected",
      "collected_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1
}
```

### 3. Transfer Collected Tokens
**POST `/api/e9th/transfer`**

Transfers collected tokens to receiving wallet.

**Request:**
```json
{
  "session_token": "usr_abc123...",
  "receiving_wallet_id": 1  // Optional, defaults to active wallet
}
```

**Response:**
```json
{
  "success": true,
  "transfer_id": 1,
  "total_tokens_transferred": 150.5,
  "receiving_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
  "wallet_name": "Primary Receiving Wallet",
  "status": "processing",
  "message": "Transfer initiated. 150.5 e9th tokens will be transferred..."
}
```

### 4. Complete Transfer
**POST `/api/e9th/transfer/complete`**

Marks transfer as completed after blockchain transaction.

**Request:**
```json
{
  "session_token": "usr_abc123...",
  "transfer_id": 1,
  "tx_hash": "0xdef456...",
  "gas_fee": 0.001  // Optional
}
```

### 5. Manage Receiving Wallet
**GET/POST `/api/e9th/receiving-wallet`**

Get or update receiving wallet configuration.

## Frontend Integration

### Wallet Connection

The dashboard includes E9th wallet connection functionality:

```javascript
// Connect wallet
connectWallet() - Connects to E9th wallet provider or manual entry

// Purchase with E9th
purchasePackageWithE9th(packageId, packageName, e9thAmount) - Initiates E9th payment
```

### Payment Flow

1. User clicks "Purchase" on a package
2. Selects payment method (E9th or Stripe)
3. If E9th:
   - Wallet connection checked
   - Transaction initiated via wallet provider
   - Transaction hash sent to API
   - Credits issued upon confirmation
4. If Stripe:
   - Standard Stripe checkout flow

## Setup Instructions

### 1. Database Setup

Run the schema files in order:

```bash
# 1. Base credit system (if not already done)
mysql -u root -p hikeyz_db < database/schema_credits.sql

# 2. E9th collection tables
mysql -u root -p hikeyz_db < database/schema_e9th_collection.sql

# 3. Updated stored procedures
mysql -u root -p hikeyz_db < database/stored_procedures_e9th.sql
```

### 2. Configure Receiving Wallet

Update the receiving wallet address:

```sql
UPDATE e9th_receiving_wallets 
SET wallet_address = 'YOUR_RECEIVING_WALLET_ADDRESS',
    wallet_name = 'Your Wallet Name'
WHERE id = 1;
```

Or via API:

```bash
curl -X POST https://your-api.com/api/e9th/receiving-wallet \
  -H "Content-Type: application/json" \
  -d '{
    "session_token": "admin_token",
    "wallet_id": 1,
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
    "wallet_name": "Primary Wallet"
  }'
```

### 3. Environment Variables

No additional environment variables required. The system uses existing database configuration.

## Token Collection Logic

### When Tokens Are Collected

E9th tokens are automatically collected when:
1. User downloads songs (credits are deducted)
2. User originally paid with E9th tokens (has confirmed e9th_deposits)
3. Collection ratio: 1 credit used = 1 e9th token collected

### Collection Process

1. User downloads songs → `deduct_credits` procedure called
2. Procedure checks if user has E9th deposits
3. If yes, creates record in `e9th_collections` table
4. Status set to 'collected'
5. Tokens ready for transfer

## Transfer Process

### Manual Transfer

1. Admin calls `/api/e9th/transfer`
2. System aggregates all 'collected' tokens
3. Creates transfer record in `e9th_transfers`
4. Updates collections to 'transferred' status
5. Admin completes blockchain transaction
6. Admin calls `/api/e9th/transfer/complete` with tx_hash

### Automated Transfer (Future)

Can be implemented with:
- Scheduled job (cron)
- Minimum threshold check
- Automatic blockchain transaction

## Testing

### Test E9th Deposit

```bash
curl -X POST https://your-api.com/api/e9th/deposit \
  -H "Content-Type: application/json" \
  -d '{
    "session_token": "test_token",
    "e9th_amount": 25.0,
    "tx_hash": "0xtest123...",
    "wallet_address": "0xtest456...",
    "package_id": 1
  }'
```

### Test Token Collection

1. User with E9th deposits downloads songs
2. Check `e9th_collections` table for new records
3. Verify tokens collected = credits used

### Test Transfer

```bash
curl -X POST https://your-api.com/api/e9th/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "session_token": "admin_token",
    "receiving_wallet_id": 1
  }'
```

## Monitoring

### View Collections

```sql
-- All collected tokens
SELECT * FROM e9th_collections WHERE collection_status = 'collected';

-- Total pending transfer
SELECT SUM(e9th_tokens_collected) as total_pending
FROM e9th_collections
WHERE collection_status = 'collected';
```

### View Transfers

```sql
-- Recent transfers
SELECT * FROM e9th_transfers 
ORDER BY initiated_at DESC 
LIMIT 10;
```

## Security Considerations

1. **Admin Access**: Transfer endpoints should require admin authentication
2. **Transaction Verification**: Verify blockchain transactions before marking as complete
3. **Wallet Validation**: Validate wallet addresses before processing
4. **Rate Limiting**: Implement rate limiting on deposit endpoints
5. **Audit Trail**: All collections and transfers are logged in database

## Troubleshooting

### Tokens Not Being Collected

1. Check if user has confirmed E9th deposits:
   ```sql
   SELECT * FROM e9th_deposits 
   WHERE user_id = X AND status = 'confirmed';
   ```

2. Verify `deduct_credits` procedure is being called
3. Check `e9th_collections` table for errors

### Transfer Fails

1. Verify receiving wallet is active:
   ```sql
   SELECT * FROM e9th_receiving_wallets WHERE is_active = TRUE;
   ```

2. Check for sufficient tokens to transfer
3. Verify blockchain transaction completed successfully

## Future Enhancements

1. **Auto-Transfer**: Automatic transfers when threshold reached
2. **Multi-Wallet Support**: Distribute transfers across multiple wallets
3. **Gas Fee Tracking**: Track and deduct gas fees from collections
4. **Smart Contract Integration**: Direct smart contract interaction
5. **Real-time Notifications**: Notify admins when transfers are ready

