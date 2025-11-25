-- ========================================
-- CREDIT-BASED ACCOUNT SYSTEM SCHEMA
-- E9th Token Integration
-- ========================================

-- Users table with email + PIN authentication
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,  -- Hashed 4-6 digit PIN
    e9th_wallet_address VARCHAR(100) NULL,  -- E9th token wallet address
    credit_balance DECIMAL(10, 2) DEFAULT 0.00,  -- Current E9th utility token balance
    total_credits_purchased DECIMAL(10, 2) DEFAULT 0.00,  -- Lifetime purchases
    total_credits_spent DECIMAL(10, 2) DEFAULT 0.00,  -- Lifetime spending
    total_songs_downloaded INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    status ENUM('active', 'suspended', 'deleted') DEFAULT 'active',
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Credit purchase packages (with bonus structure)
CREATE TABLE IF NOT EXISTS credit_packages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    package_name VARCHAR(50) NOT NULL,
    usd_amount DECIMAL(10, 2) NOT NULL,  -- Amount paid in USD
    base_credits DECIMAL(10, 2) NOT NULL,  -- 1 USD = 1 credit
    bonus_credits DECIMAL(10, 2) NOT NULL,  -- Bonus credits
    total_credits DECIMAL(10, 2) NOT NULL,  -- base + bonus
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default credit packages
INSERT INTO credit_packages (package_name, usd_amount, base_credits, bonus_credits, total_credits, display_order) VALUES
('Starter Pack', 25.00, 25.00, 15.00, 40.00, 1),
('Popular Pack', 50.00, 50.00, 25.00, 75.00, 2),
('Premium Pack', 100.00, 100.00, 100.00, 200.00, 3)
ON DUPLICATE KEY UPDATE package_name = VALUES(package_name);

-- Credit transactions (all purchases and usage)
CREATE TABLE IF NOT EXISTS credit_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    transaction_type ENUM('purchase', 'bonus', 'deduction', 'refund', 'admin_adjustment') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,  -- Positive for additions, negative for deductions
    balance_after DECIMAL(10, 2) NOT NULL,  -- Balance after transaction

    -- Purchase details (if transaction_type = 'purchase')
    package_id INT NULL,
    usd_amount DECIMAL(10, 2) NULL,
    payment_method ENUM('e9th_stablecoin', 'crypto', 'card', 'other') NULL,
    e9th_tx_hash VARCHAR(255) NULL,  -- E9th blockchain transaction hash

    -- Usage details (if transaction_type = 'deduction')
    job_id VARCHAR(100) NULL,
    songs_downloaded INT NULL,

    -- Admin notes
    notes TEXT NULL,
    admin_user_id INT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (package_id) REFERENCES credit_packages(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_transaction_type (transaction_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Update sessions table for credit-based system
ALTER TABLE sessions
    ADD COLUMN user_id INT NULL AFTER session_token,
    ADD COLUMN credits_used DECIMAL(10, 2) DEFAULT 0.00 AFTER songs_downloaded,
    ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- E9th token deposits/conversions
CREATE TABLE IF NOT EXISTS e9th_deposits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    e9th_stablecoin_amount DECIMAL(18, 8) NOT NULL,  -- E9th stablecoins deposited
    utility_tokens_issued DECIMAL(10, 2) NOT NULL,  -- E9th utility tokens issued (1:1 ratio)
    tx_hash VARCHAR(255) NOT NULL,  -- Blockchain transaction hash
    blockchain_network VARCHAR(50) DEFAULT 'e9th',  -- Network identifier
    wallet_address VARCHAR(100) NOT NULL,  -- User's wallet address
    confirmation_count INT DEFAULT 0,
    status ENUM('pending', 'confirmed', 'failed', 'refunded') DEFAULT 'pending',
    confirmed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_tx_hash (tx_hash),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pricing configuration (per-song cost)
CREATE TABLE IF NOT EXISTS pricing_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_value DECIMAL(10, 4) NOT NULL,
    description TEXT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default pricing (0.35 credits per song)
INSERT INTO pricing_config (config_key, config_value, description) VALUES
('credits_per_song', 0.35, 'Credits deducted per song download'),
('usd_to_credit_ratio', 1.00, 'USD to credit conversion ratio'),
('min_credit_balance', 0.35, 'Minimum credits required to start download')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);

-- Free tier tracking (keep existing for ad-supported users)
CREATE TABLE IF NOT EXISTS free_tier_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NULL,
    ip_address VARCHAR(45) NOT NULL,
    session_token VARCHAR(64) NOT NULL,
    free_credits_used INT DEFAULT 0,
    ads_watched INT DEFAULT 0,
    last_ad_watched_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,

    INDEX idx_email (email),
    INDEX idx_ip_address (ip_address),
    INDEX idx_session_token (session_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Views for quick balance queries
CREATE OR REPLACE VIEW user_balances AS
SELECT
    u.id,
    u.email,
    u.credit_balance,
    u.total_credits_purchased,
    u.total_credits_spent,
    u.total_songs_downloaded,
    ROUND(u.credit_balance / 0.35, 0) AS songs_available,
    u.last_login_at,
    u.created_at
FROM users u
WHERE u.status = 'active';

-- View for transaction history
CREATE OR REPLACE VIEW user_transaction_history AS
SELECT
    ct.id,
    u.email,
    ct.transaction_type,
    ct.amount,
    ct.balance_after,
    cp.package_name,
    ct.usd_amount,
    ct.songs_downloaded,
    ct.created_at
FROM credit_transactions ct
JOIN users u ON ct.user_id = u.id
LEFT JOIN credit_packages cp ON ct.package_id = cp.id
ORDER BY ct.created_at DESC;

-- ========================================
-- PERFORMANCE INDEXES
-- ========================================

ALTER TABLE users ADD INDEX idx_credit_balance (credit_balance);
ALTER TABLE credit_transactions ADD INDEX idx_user_created (user_id, created_at);
ALTER TABLE e9th_deposits ADD INDEX idx_user_status (user_id, status);

-- ========================================
-- STORED PROCEDURES
-- ========================================

DELIMITER //

-- Procedure to deduct credits for downloads
CREATE PROCEDURE deduct_credits(
    IN p_user_id INT,
    IN p_job_id VARCHAR(100),
    IN p_songs_count INT,
    OUT p_success BOOLEAN,
    OUT p_error_message VARCHAR(255)
)
BEGIN
    DECLARE v_credits_per_song DECIMAL(10, 4);
    DECLARE v_total_cost DECIMAL(10, 2);
    DECLARE v_current_balance DECIMAL(10, 2);
    DECLARE v_new_balance DECIMAL(10, 2);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Database error occurred';
    END;

    START TRANSACTION;

    -- Get pricing
    SELECT config_value INTO v_credits_per_song
    FROM pricing_config
    WHERE config_key = 'credits_per_song';

    -- Calculate total cost
    SET v_total_cost = v_credits_per_song * p_songs_count;

    -- Get current balance with lock
    SELECT credit_balance INTO v_current_balance
    FROM users
    WHERE id = p_user_id
    FOR UPDATE;

    -- Check sufficient balance
    IF v_current_balance < v_total_cost THEN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = CONCAT('Insufficient credits. Required: ', v_total_cost, ', Available: ', v_current_balance);
    ELSE
        -- Deduct credits
        SET v_new_balance = v_current_balance - v_total_cost;

        UPDATE users
        SET credit_balance = v_new_balance,
            total_credits_spent = total_credits_spent + v_total_cost,
            total_songs_downloaded = total_songs_downloaded + p_songs_count
        WHERE id = p_user_id;

        -- Record transaction
        INSERT INTO credit_transactions (
            user_id, transaction_type, amount, balance_after,
            job_id, songs_downloaded
        ) VALUES (
            p_user_id, 'deduction', -v_total_cost, v_new_balance,
            p_job_id, p_songs_count
        );

        COMMIT;
        SET p_success = TRUE;
        SET p_error_message = NULL;
    END IF;
END //

-- Procedure to add credits (purchase or bonus)
CREATE PROCEDURE add_credits(
    IN p_user_id INT,
    IN p_package_id INT,
    IN p_payment_method VARCHAR(50),
    IN p_tx_hash VARCHAR(255),
    OUT p_success BOOLEAN,
    OUT p_error_message VARCHAR(255)
)
BEGIN
    DECLARE v_base_credits DECIMAL(10, 2);
    DECLARE v_bonus_credits DECIMAL(10, 2);
    DECLARE v_total_credits DECIMAL(10, 2);
    DECLARE v_usd_amount DECIMAL(10, 2);
    DECLARE v_new_balance DECIMAL(10, 2);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Database error occurred';
    END;

    START TRANSACTION;

    -- Get package details
    SELECT base_credits, bonus_credits, total_credits, usd_amount
    INTO v_base_credits, v_bonus_credits, v_total_credits, v_usd_amount
    FROM credit_packages
    WHERE id = p_package_id AND is_active = TRUE;

    IF v_total_credits IS NULL THEN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Invalid package';
    ELSE
        -- Add base credits
        UPDATE users
        SET credit_balance = credit_balance + v_base_credits,
            total_credits_purchased = total_credits_purchased + v_base_credits
        WHERE id = p_user_id;

        SELECT credit_balance INTO v_new_balance
        FROM users WHERE id = p_user_id;

        INSERT INTO credit_transactions (
            user_id, transaction_type, amount, balance_after,
            package_id, usd_amount, payment_method, e9th_tx_hash
        ) VALUES (
            p_user_id, 'purchase', v_base_credits, v_new_balance,
            p_package_id, v_usd_amount, p_payment_method, p_tx_hash
        );

        -- Add bonus credits if applicable
        IF v_bonus_credits > 0 THEN
            UPDATE users
            SET credit_balance = credit_balance + v_bonus_credits
            WHERE id = p_user_id;

            SELECT credit_balance INTO v_new_balance
            FROM users WHERE id = p_user_id;

            INSERT INTO credit_transactions (
                user_id, transaction_type, amount, balance_after,
                package_id, notes
            ) VALUES (
                p_user_id, 'bonus', v_bonus_credits, v_new_balance,
                p_package_id, CONCAT('Bonus credits for package purchase')
            );
        END IF;

        COMMIT;
        SET p_success = TRUE;
        SET p_error_message = NULL;
    END IF;
END //

DELIMITER ;

-- ========================================
-- MIGRATION NOTES
-- ========================================
--
-- To migrate from time-based to credit-based:
-- 1. Existing free tier remains for ad-supported users
-- 2. Create user accounts for anyone wanting to purchase credits
-- 3. Email + PIN replaces traditional password authentication
-- 4. E9th stablecoin deposits convert 1:1 to utility tokens
-- 5. Each song download costs 0.35 credits
--
-- ========================================
