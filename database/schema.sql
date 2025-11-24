-- SUNO Downloader Pro Database Schema
-- Database: suno_downloader

-- Users table (optional - for future user accounts)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    total_downloads INT DEFAULT 0,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sessions table (paid access sessions)
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_token VARCHAR(64) UNIQUE NOT NULL,
    stripe_session_id VARCHAR(255) UNIQUE,
    client_reference_id VARCHAR(255),
    plan_type ENUM('quick', 'pro') NOT NULL,
    plan_name VARCHAR(100),
    user_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    max_songs INT NULL,
    songs_downloaded INT DEFAULT 0,
    status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
    INDEX idx_session_token (session_token),
    INDEX idx_stripe_session (stripe_session_id),
    INDEX idx_expires_at (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Download jobs table
CREATE TABLE IF NOT EXISTS download_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(64) UNIQUE NOT NULL,
    session_id INT NOT NULL,
    status ENUM('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    total_songs INT DEFAULT 0,
    songs_downloaded INT DEFAULT 0,
    songs_failed INT DEFAULT 0,
    current_song VARCHAR(255) NULL,
    error_message TEXT NULL,
    zip_file_path VARCHAR(500) NULL,
    zip_file_size BIGINT NULL,
    INDEX idx_job_id (job_id),
    INDEX idx_session_id (session_id),
    INDEX idx_status (status),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Song downloads table (detailed log of each song)
CREATE TABLE IF NOT EXISTS song_downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    song_index INT NOT NULL,
    song_title VARCHAR(255),
    song_url VARCHAR(500),
    song_id VARCHAR(100),
    status ENUM('pending', 'downloading', 'completed', 'failed') DEFAULT 'pending',
    file_path VARCHAR(500) NULL,
    file_size BIGINT NULL,
    downloaded_at TIMESTAMP NULL,
    error_message TEXT NULL,
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    FOREIGN KEY (job_id) REFERENCES download_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payments table (Stripe payment records)
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    stripe_session_id VARCHAR(255),
    session_id INT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status ENUM('pending', 'succeeded', 'failed', 'refunded') DEFAULT 'pending',
    customer_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stripe_payment (stripe_payment_intent_id),
    INDEX idx_stripe_session (stripe_session_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Analytics table (track usage metrics)
CREATE TABLE IF NOT EXISTS analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type ENUM('page_view', 'checkout_started', 'payment_completed', 'download_started', 'download_completed', 'ad_impression', 'ad_click') NOT NULL,
    session_token VARCHAR(64) NULL,
    job_id VARCHAR(64) NULL,
    metadata JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ad revenue tracking
CREATE TABLE IF NOT EXISTS ad_revenue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_token VARCHAR(64) NULL,
    job_id VARCHAR(64) NULL,
    ad_network ENUM('google_adsense', 'other') DEFAULT 'google_adsense',
    ad_unit_id VARCHAR(100),
    impression_count INT DEFAULT 0,
    click_count INT DEFAULT 0,
    estimated_revenue DECIMAL(10, 4) DEFAULT 0.00,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_date (date),
    INDEX idx_session (session_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Cleanup expired sessions (run as cron job)
DELIMITER //
CREATE PROCEDURE cleanup_expired_sessions()
BEGIN
    -- Mark sessions as expired
    UPDATE sessions
    SET status = 'expired'
    WHERE expires_at < NOW()
    AND status = 'active';

    -- Delete old expired sessions (older than 30 days)
    DELETE FROM sessions
    WHERE status = 'expired'
    AND expires_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

    -- Delete old download files (older than 7 days)
    UPDATE download_jobs
    SET zip_file_path = NULL
    WHERE completed_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
    AND status = 'completed';
END //
DELIMITER ;

-- Create views for common queries
CREATE OR REPLACE VIEW active_sessions_view AS
SELECT
    s.id,
    s.session_token,
    s.plan_type,
    s.created_at,
    s.expires_at,
    s.songs_downloaded,
    s.max_songs,
    TIMESTAMPDIFF(SECOND, NOW(), s.expires_at) AS seconds_remaining,
    dj.job_id,
    dj.status AS job_status,
    dj.total_songs,
    dj.songs_downloaded AS job_songs_downloaded
FROM sessions s
LEFT JOIN download_jobs dj ON s.id = dj.session_id AND dj.status IN ('processing', 'queued')
WHERE s.status = 'active'
AND s.expires_at > NOW();

-- Revenue analytics view
CREATE OR REPLACE VIEW revenue_analytics AS
SELECT
    DATE(p.created_at) AS date,
    COUNT(DISTINCT p.id) AS total_payments,
    SUM(p.amount) AS total_revenue,
    SUM(CASE WHEN s.plan_type = 'quick' THEN p.amount ELSE 0 END) AS quick_revenue,
    SUM(CASE WHEN s.plan_type = 'pro' THEN p.amount ELSE 0 END) AS pro_revenue,
    COUNT(DISTINCT s.session_token) AS active_sessions,
    SUM(s.songs_downloaded) AS total_songs_downloaded
FROM payments p
LEFT JOIN sessions s ON p.session_id = s.id
WHERE p.status = 'succeeded'
GROUP BY DATE(p.created_at);

-- Insert initial test data (for development)
-- INSERT INTO users (email) VALUES ('test@example.com');

-- Grant permissions (adjust username as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON suno_downloader.* TO 'suno_user'@'localhost';
-- FLUSH PRIVILEGES;
