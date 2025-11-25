-- ========================================
-- UPDATED STORED PROCEDURES FOR E9TH TOKEN COLLECTION
-- ========================================

DELIMITER //

-- Updated procedure to deduct credits AND collect e9th tokens
DROP PROCEDURE IF EXISTS deduct_credits //
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
    DECLARE v_e9th_tokens_collected DECIMAL(18, 8);
    DECLARE v_transaction_id INT;
    DECLARE v_user_paid_with_e9th BOOLEAN DEFAULT FALSE;

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

        -- Get the transaction ID
        SET v_transaction_id = LAST_INSERT_ID();

        -- Check if user originally paid with e9th tokens
        -- (Check if user has any e9th deposits that haven't been fully used)
        SELECT COUNT(*) > 0 INTO v_user_paid_with_e9th
        FROM e9th_deposits
        WHERE user_id = p_user_id 
        AND status = 'confirmed'
        AND utility_tokens_issued > 0;

        -- If user paid with e9th tokens, collect equivalent e9th tokens
        -- 1 credit = 1 e9th token (1:1 ratio)
        IF v_user_paid_with_e9th THEN
            SET v_e9th_tokens_collected = v_total_cost;  -- 1 credit = 1 e9th token
            
            -- Record e9th token collection
            INSERT INTO e9th_collections (
                user_id, transaction_id, credits_used, e9th_tokens_collected,
                job_id, songs_downloaded, collection_status
            ) VALUES (
                p_user_id, v_transaction_id, v_total_cost, v_e9th_tokens_collected,
                p_job_id, p_songs_count, 'collected'
            );
        END IF;

        COMMIT;
        SET p_success = TRUE;
        SET p_error_message = NULL;
    END IF;
END //

-- Procedure to process e9th token deposit and issue credits
DROP PROCEDURE IF EXISTS process_e9th_deposit //
CREATE PROCEDURE process_e9th_deposit(
    IN p_user_id INT,
    IN p_e9th_amount DECIMAL(18, 8),
    IN p_tx_hash VARCHAR(255),
    IN p_wallet_address VARCHAR(100),
    IN p_package_id INT,
    OUT p_success BOOLEAN,
    OUT p_error_message VARCHAR(255),
    OUT p_credits_issued DECIMAL(10, 2)
)
BEGIN
    DECLARE v_base_credits DECIMAL(10, 2);
    DECLARE v_bonus_credits DECIMAL(10, 2);
    DECLARE v_total_credits DECIMAL(10, 2);
    DECLARE v_usd_amount DECIMAL(10, 2);
    DECLARE v_new_balance DECIMAL(10, 2);
    DECLARE v_deposit_id INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Database error occurred';
        SET p_credits_issued = 0;
    END;

    START TRANSACTION;

    -- Get package details if provided
    IF p_package_id IS NOT NULL THEN
        SELECT base_credits, bonus_credits, total_credits, usd_amount
        INTO v_base_credits, v_bonus_credits, v_total_credits, v_usd_amount
        FROM credit_packages
        WHERE id = p_package_id AND is_active = TRUE;
    ELSE
        -- Direct deposit: 1 e9th = 1 credit (no bonus)
        SET v_base_credits = p_e9th_amount;
        SET v_bonus_credits = 0;
        SET v_total_credits = p_e9th_amount;
        SET v_usd_amount = p_e9th_amount;
    END IF;

    IF v_total_credits IS NULL THEN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Invalid package or amount';
        SET p_credits_issued = 0;
    ELSE
        -- Record e9th deposit
        INSERT INTO e9th_deposits (
            user_id, e9th_stablecoin_amount, utility_tokens_issued,
            tx_hash, wallet_address, status, confirmation_count
        ) VALUES (
            p_user_id, p_e9th_amount, v_total_credits,
            p_tx_hash, p_wallet_address, 'confirmed', 1
        );

        SET v_deposit_id = LAST_INSERT_ID();

        -- Add base credits
        UPDATE users
        SET credit_balance = credit_balance + v_base_credits,
            total_credits_purchased = total_credits_purchased + v_base_credits
        WHERE id = p_user_id;

        SELECT credit_balance INTO v_new_balance
        FROM users WHERE id = p_user_id;

        -- Record purchase transaction
        INSERT INTO credit_transactions (
            user_id, transaction_type, amount, balance_after,
            package_id, usd_amount, payment_method, e9th_tx_hash
        ) VALUES (
            p_user_id, 'purchase', v_base_credits, v_new_balance,
            p_package_id, v_usd_amount, 'e9th_stablecoin', p_tx_hash
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
                p_package_id, CONCAT('Bonus credits for e9th deposit')
            );
        END IF;

        -- Update user's e9th wallet address if not set
        UPDATE users
        SET e9th_wallet_address = p_wallet_address
        WHERE id = p_user_id AND (e9th_wallet_address IS NULL OR e9th_wallet_address = '');

        COMMIT;
        SET p_success = TRUE;
        SET p_error_message = NULL;
        SET p_credits_issued = v_total_credits;
    END IF;
END //

-- Procedure to transfer collected e9th tokens to receiving wallet
DROP PROCEDURE IF EXISTS transfer_collected_e9th //
CREATE PROCEDURE transfer_collected_e9th(
    IN p_receiving_wallet_id INT,
    OUT p_success BOOLEAN,
    OUT p_error_message VARCHAR(255),
    OUT p_transfer_id INT,
    OUT p_total_transferred DECIMAL(18, 8)
)
BEGIN
    DECLARE v_total_tokens DECIMAL(18, 8);
    DECLARE v_collection_count INT;
    DECLARE v_wallet_address VARCHAR(100);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Database error occurred';
        SET p_transfer_id = NULL;
        SET p_total_transferred = 0;
    END;

    START TRANSACTION;

    -- Get receiving wallet address
    SELECT wallet_address INTO v_wallet_address
    FROM e9th_receiving_wallets
    WHERE id = p_receiving_wallet_id AND is_active = TRUE;

    IF v_wallet_address IS NULL THEN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_error_message = 'Invalid or inactive receiving wallet';
        SET p_transfer_id = NULL;
        SET p_total_transferred = 0;
    ELSE
        -- Calculate total tokens to transfer (all collected tokens)
        SELECT 
            COALESCE(SUM(e9th_tokens_collected), 0),
            COUNT(*)
        INTO v_total_tokens, v_collection_count
        FROM e9th_collections
        WHERE collection_status = 'collected';

        IF v_total_tokens <= 0 THEN
            ROLLBACK;
            SET p_success = FALSE;
            SET p_error_message = 'No tokens available for transfer';
            SET p_transfer_id = NULL;
            SET p_total_transferred = 0;
        ELSE
            -- Create transfer record
            INSERT INTO e9th_transfers (
                receiving_wallet_id, total_tokens_transferred,
                collection_count, transfer_status
            ) VALUES (
                p_receiving_wallet_id, v_total_tokens,
                v_collection_count, 'pending'
            );

            SET p_transfer_id = LAST_INSERT_ID();

            -- Update collections to link to transfer
            UPDATE e9th_collections
            SET collection_status = 'transferred',
                transfer_id = p_transfer_id
            WHERE collection_status = 'collected';

            COMMIT;
            SET p_success = TRUE;
            SET p_error_message = NULL;
            SET p_total_transferred = v_total_tokens;
        END IF;
    END IF;
END //

DELIMITER ;

