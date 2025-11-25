-- ========================================
-- E9TH TOKEN COLLECTION & TRANSFER SYSTEM
-- ========================================

-- Table to track collected e9th tokens from credit usage
CREATE TABLE IF NOT EXISTS e9th_collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    transaction_id INT NULL,  -- Reference to credit_transactions.id
    credits_used DECIMAL(10, 2) NOT NULL,  -- Credits that were used
    e9th_tokens_collected DECIMAL(18, 8) NOT NULL,  -- E9th tokens collected (1:1 ratio)
    job_id VARCHAR(100) NULL,  -- Download job ID
    songs_downloaded INT NULL,  -- Number of songs downloaded
    collection_status ENUM('pending', 'collected', 'transferred', 'failed') DEFAULT 'pending',
    transfer_tx_hash VARCHAR(255) NULL,  -- Blockchain transaction hash when transferred to receiving wallet
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transferred_at TIMESTAMP NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES credit_transactions(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_collection_status (collection_status),
    INDEX idx_transaction_id (transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table for receiving wallet configuration
CREATE TABLE IF NOT EXISTS e9th_receiving_wallets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wallet_address VARCHAR(100) NOT NULL UNIQUE,  -- Receiving wallet address
    wallet_name VARCHAR(100) NULL,  -- Human-readable name
    network VARCHAR(50) DEFAULT 'e9th',  -- Blockchain network
    is_active BOOLEAN DEFAULT TRUE,
    auto_transfer_enabled BOOLEAN DEFAULT FALSE,  -- Auto-transfer collected tokens
    min_collection_threshold DECIMAL(18, 8) DEFAULT 0.0,  -- Minimum tokens before auto-transfer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default receiving wallet (update with actual wallet address)
INSERT INTO e9th_receiving_wallets (wallet_address, wallet_name, is_active, auto_transfer_enabled, min_collection_threshold)
VALUES ('0x0000000000000000000000000000000000000000', 'Primary Receiving Wallet', TRUE, FALSE, 0.0)
ON DUPLICATE KEY UPDATE wallet_address = VALUES(wallet_address);

-- Table to track token transfers to receiving wallet
CREATE TABLE IF NOT EXISTS e9th_transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    receiving_wallet_id INT NOT NULL,
    total_tokens_transferred DECIMAL(18, 8) NOT NULL,
    collection_count INT NOT NULL,  -- Number of collections included in this transfer
    tx_hash VARCHAR(255) NULL,  -- Blockchain transaction hash
    transfer_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    gas_fee DECIMAL(18, 8) NULL,  -- Gas fee paid for transfer
    error_message TEXT NULL,
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    
    FOREIGN KEY (receiving_wallet_id) REFERENCES e9th_receiving_wallets(id) ON DELETE RESTRICT,
    INDEX idx_transfer_status (transfer_status),
    INDEX idx_receiving_wallet_id (receiving_wallet_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Link collections to transfers
ALTER TABLE e9th_collections
    ADD COLUMN transfer_id INT NULL AFTER transfer_tx_hash,
    ADD FOREIGN KEY (transfer_id) REFERENCES e9th_transfers(id) ON DELETE SET NULL,
    ADD INDEX idx_transfer_id (transfer_id);

-- View for pending collections (ready to transfer)
CREATE OR REPLACE VIEW pending_e9th_collections AS
SELECT 
    ec.id,
    ec.user_id,
    u.email,
    ec.credits_used,
    ec.e9th_tokens_collected,
    ec.collection_status,
    ec.collected_at,
    SUM(ec.e9th_tokens_collected) OVER () AS total_pending_tokens
FROM e9th_collections ec
JOIN users u ON ec.user_id = u.id
WHERE ec.collection_status = 'collected'
ORDER BY ec.collected_at ASC;

-- View for collection summary
CREATE OR REPLACE VIEW e9th_collection_summary AS
SELECT 
    DATE(ec.collected_at) AS collection_date,
    COUNT(*) AS total_collections,
    SUM(ec.e9th_tokens_collected) AS total_tokens_collected,
    SUM(ec.songs_downloaded) AS total_songs,
    COUNT(DISTINCT ec.user_id) AS unique_users
FROM e9th_collections ec
WHERE ec.collection_status IN ('collected', 'transferred')
GROUP BY DATE(ec.collected_at)
ORDER BY collection_date DESC;

