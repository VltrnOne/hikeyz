-- ========================================
-- E9TH DIRECT PAYMENT BONUS MIGRATION
-- Adds 25% bonus for E9th direct payments
-- ========================================

-- Add column to credit_transactions to track E9th direct payment bonus
ALTER TABLE credit_transactions
ADD COLUMN e9th_direct_bonus DECIMAL(10, 2) DEFAULT 0.00 AFTER bonus_credits,
ADD COLUMN is_e9th_direct_payment BOOLEAN DEFAULT FALSE AFTER payment_method;

-- Add configuration for E9th direct payment bonus percentage
INSERT INTO pricing_config (config_key, config_value, description) VALUES
('e9th_direct_bonus_percentage', 0.25, 'Bonus percentage for E9th direct payments (0.25 = 25%)')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);

-- Update the add_credits stored procedure to include E9th direct payment bonus
DROP PROCEDURE IF EXISTS add_credits;

DELIMITER //

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
    DECLARE v_e9th_direct_bonus DECIMAL(10, 2);
    DECLARE v_e9th_bonus_percentage DECIMAL(10, 4);
    DECLARE v_usd_amount DECIMAL(10, 2);
    DECLARE v_new_balance DECIMAL(10, 2);
    DECLARE v_is_e9th_direct BOOLEAN;

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
        -- Check if payment method is E9th direct
        SET v_is_e9th_direct = (p_payment_method = 'e9th_stablecoin' OR p_payment_method = 'e9th_direct');

        -- Calculate E9th direct payment bonus (25% of base credits)
        IF v_is_e9th_direct THEN
            -- Get E9th direct bonus percentage from config
            SELECT config_value INTO v_e9th_bonus_percentage
            FROM pricing_config
            WHERE config_key = 'e9th_direct_bonus_percentage';

            SET v_e9th_direct_bonus = v_base_credits * v_e9th_bonus_percentage;
        ELSE
            SET v_e9th_direct_bonus = 0.00;
        END IF;

        -- Add base credits
        UPDATE users
        SET credit_balance = credit_balance + v_base_credits,
            total_credits_purchased = total_credits_purchased + v_base_credits
        WHERE id = p_user_id;

        SELECT credit_balance INTO v_new_balance
        FROM users WHERE id = p_user_id;

        INSERT INTO credit_transactions (
            user_id, transaction_type, amount, balance_after,
            package_id, usd_amount, payment_method, e9th_tx_hash,
            is_e9th_direct_payment, e9th_direct_bonus
        ) VALUES (
            p_user_id, 'purchase', v_base_credits, v_new_balance,
            p_package_id, v_usd_amount, p_payment_method, p_tx_hash,
            v_is_e9th_direct, v_e9th_direct_bonus
        );

        -- Add package bonus credits if applicable
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
                p_package_id, CONCAT('Package bonus credits')
            );
        END IF;

        -- Add E9th direct payment bonus if applicable
        IF v_e9th_direct_bonus > 0 THEN
            UPDATE users
            SET credit_balance = credit_balance + v_e9th_direct_bonus,
                total_credits_purchased = total_credits_purchased + v_e9th_direct_bonus
            WHERE id = p_user_id;

            SELECT credit_balance INTO v_new_balance
            FROM users WHERE id = p_user_id;

            INSERT INTO credit_transactions (
                user_id, transaction_type, amount, balance_after,
                package_id, notes, e9th_direct_bonus
            ) VALUES (
                p_user_id, 'bonus', v_e9th_direct_bonus, v_new_balance,
                p_package_id, CONCAT('E9th direct payment bonus (25%)'), v_e9th_direct_bonus
            );
        END IF;

        COMMIT;
        SET p_success = TRUE;
        SET p_error_message = NULL;
    END IF;
END //

DELIMITER ;

-- Create view for E9th direct payment statistics
CREATE OR REPLACE VIEW e9th_direct_payment_stats AS
SELECT
    COUNT(*) as total_e9th_direct_payments,
    SUM(amount) as total_e9th_direct_amount,
    SUM(e9th_direct_bonus) as total_e9th_bonuses_issued,
    AVG(e9th_direct_bonus) as avg_e9th_bonus_per_payment
FROM credit_transactions
WHERE is_e9th_direct_payment = TRUE
AND transaction_type = 'purchase';

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Check new columns
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'credit_transactions'
AND COLUMN_NAME IN ('e9th_direct_bonus', 'is_e9th_direct_payment');

-- Check new config
SELECT * FROM pricing_config WHERE config_key = 'e9th_direct_bonus_percentage';

-- Verify stored procedure
SHOW PROCEDURE STATUS WHERE Name = 'add_credits';
