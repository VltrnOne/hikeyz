# E9th Token Integration Setup Guide

## Quick Start

### Step 1: Run Database Migrations

Execute these SQL files in order:

```bash
# 1. Base credit system (if not already done)
mysql -u root -p hikeyz_db < database/schema_credits.sql

# 2. E9th collection tables
mysql -u root -p hikeyz_db < database/schema_e9th_collection.sql

# 3. Updated stored procedures (includes e9th collection logic)
mysql -u root -p hikeyz_db < database/stored_procedures_e9th.sql
```

**OR** update the existing `deduct_credits` procedure manually:

```sql
-- Drop and recreate with e9th collection support
DROP PROCEDURE IF EXISTS deduct_credits;

-- Then run the updated procedure from stored_procedures_e9th.sql
```

### Step 2: Configure Receiving Wallet

Set your receiving wallet address:

```sql
UPDATE e9th_receiving_wallets 
SET wallet_address = 'YOUR_E9TH_WALLET_ADDRESS_HERE',
    wallet_name = 'Primary Receiving Wallet'
WHERE id = 1;
```

**Important**: Replace `YOUR_E9TH_WALLET_ADDRESS_HERE` with your actual E9th wallet address.

### Step 3: Verify Setup

Check that tables exist:

```sql
SHOW TABLES LIKE 'e9th%';
-- Should show:
-- e9th_collections
-- e9th_deposits
-- e9th_receiving_wallets
-- e9th_transfers
```

Check receiving wallet:

```sql
SELECT * FROM e9th_receiving_wallets WHERE is_active = TRUE;
```

## How It Works

### Token Collection Flow

1. **User deposits E9th tokens** → Credits issued (1:1 ratio)
2. **User downloads songs** → Credits deducted
3. **System automatically collects E9th tokens** → Equivalent to credits used
4. **Admin transfers collected tokens** → To receiving wallet

### Example

- User deposits 100 E9th tokens → Gets 100 credits
- User downloads 10 songs (3.5 credits) → 3.5 E9th tokens collected
- Admin transfers all collected tokens → To receiving wallet

## API Usage Examples

### Process E9th Deposit

```javascript
const response = await fetch('https://your-api.com/api/e9th/deposit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_token: 'user_session_token',
    e9th_amount: 25.0,
    tx_hash: '0xabc123...',
    wallet_address: '0x742d35Cc...',
    package_id: 1  // Optional
  })
});
```

### Transfer Collected Tokens

```javascript
const response = await fetch('https://your-api.com/api/e9th/transfer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_token: 'admin_session_token',
    receiving_wallet_id: 1
  })
});
```

### Complete Transfer (after blockchain tx)

```javascript
const response = await fetch('https://your-api.com/api/e9th/transfer/complete', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_token: 'admin_session_token',
    transfer_id: 1,
    tx_hash: '0xdef456...',
    gas_fee: 0.001
  })
});
```

## Monitoring

### Check Collected Tokens

```sql
-- Total pending tokens
SELECT SUM(e9th_tokens_collected) as total_pending
FROM e9th_collections
WHERE collection_status = 'collected';
```

### View Recent Collections

```sql
SELECT 
    u.email,
    ec.credits_used,
    ec.e9th_tokens_collected,
    ec.collected_at
FROM e9th_collections ec
JOIN users u ON ec.user_id = u.id
WHERE ec.collection_status = 'collected'
ORDER BY ec.collected_at DESC
LIMIT 20;
```

### View Transfer History

```sql
SELECT 
    et.id,
    et.total_tokens_transferred,
    et.collection_count,
    et.transfer_status,
    et.tx_hash,
    et.initiated_at,
    erw.wallet_address
FROM e9th_transfers et
JOIN e9th_receiving_wallets erw ON et.receiving_wallet_id = erw.id
ORDER BY et.initiated_at DESC
LIMIT 10;
```

## Troubleshooting

### Tokens Not Being Collected

1. Verify user has E9th deposits:
   ```sql
   SELECT * FROM e9th_deposits 
   WHERE user_id = X AND status = 'confirmed';
   ```

2. Check if `e9th_collections` table exists:
   ```sql
   SHOW TABLES LIKE 'e9th_collections';
   ```

3. Verify `deduct_credits` procedure includes collection logic

### Transfer Issues

1. Check receiving wallet is configured:
   ```sql
   SELECT * FROM e9th_receiving_wallets WHERE is_active = TRUE;
   ```

2. Verify there are tokens to transfer:
   ```sql
   SELECT COUNT(*), SUM(e9th_tokens_collected) 
   FROM e9th_collections 
   WHERE collection_status = 'collected';
   ```

## Next Steps

1. ✅ Database setup complete
2. ✅ API endpoints ready
3. ✅ Frontend integration complete
4. ⏳ Configure receiving wallet address
5. ⏳ Test deposit flow
6. ⏳ Test collection flow
7. ⏳ Test transfer flow

For detailed documentation, see `E9TH_TOKEN_INTEGRATION.md`.

