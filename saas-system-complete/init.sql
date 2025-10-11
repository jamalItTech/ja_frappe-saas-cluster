-- SaaS Trial System - Initial Database Setup
-- This file is executed when the database container starts for the first time

USE saas_trials;

-- Create trial_customers table if it doesn't exist
CREATE TABLE IF NOT EXISTS trial_customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    subdomain VARCHAR(100) NOT NULL UNIQUE,
    site_url VARCHAR(255) NOT NULL,
    site_name VARCHAR(255),
    admin_password VARCHAR(100),
    selected_apps TEXT,
    trial_days INT NOT NULL DEFAULT 14,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    status ENUM('active', 'expired', 'converted') DEFAULT 'active',
    frappe_site_created BOOLEAN DEFAULT FALSE,
    notes TEXT,
    INDEX idx_status (status),
    INDEX idx_expires_at (expires_at),
    INDEX idx_created_at (created_at),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create cluster_servers table for advanced cluster management
CREATE TABLE IF NOT EXISTS cluster_servers (
    server_id VARCHAR(50) PRIMARY KEY,
    ip_address VARCHAR(15) NOT NULL,
    port INT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    role ENUM('active', 'standby', 'maintenance') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_health_check TIMESTAMP NULL,
    cpu_percent FLOAT DEFAULT 0.0,
    memory_percent FLOAT DEFAULT 0.0,
    sites_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'unknown',
    INDEX idx_active (active),
    INDEX idx_role (role),
    INDEX idx_last_health_check (last_health_check)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default cluster servers (mock data for development)
INSERT IGNORE INTO cluster_servers (server_id, ip_address, port, active, role) VALUES
('frappe-app-01', '172.22.0.20', 8000, FALSE, 'standby'),
('frappe-app-02', '172.22.0.21', 8000, FALSE, 'standby'),
('frappe-app-03', '172.22.0.22', 8000, FALSE, 'standby');

-- Insert sample trial customers for testing
INSERT IGNORE INTO trial_customers
(company_name, contact_name, email, phone, subdomain, site_url, site_name, admin_password, selected_apps, trial_days, expires_at, status, frappe_site_created, notes)
VALUES
('شركة الأمل للتجارة', 'أحمد محمد علي', 'ahmed@amal-trading.com', '+967-1-234567', 'amal-trading-0101-abc123', 'http://amal-trading-0101-abc123.trial.local', 'amal-trading-0101-abc123.trial.local', 'admin123', '["erpnext", "hrms"]', 14, DATE_ADD(NOW(), INTERVAL 14 DAY), 'active', TRUE, 'عميل تجريبي للاختبار'),

('مؤسسة النور للتقنية', 'فاطمة سالم عبدالله', 'fatima@nour-tech.org', '+967-2-345678', 'nour-tech-0102-def456', 'http://nour-tech-0102-def456.trial.local', 'nour-tech-0102-def456.trial.local', 'admin123', '["erpnext"]', 30, DATE_ADD(NOW(), INTERVAL 30 DAY), 'active', TRUE, 'عميل تجريبي طويل الأمد'),

('مكتب المستقبل القانوني', 'محمد حسن غالب', 'mohamed@future-law.com', '+967-3-456789', 'future-law-0103-ghi789', 'http://future-law-0103-ghi789.trial.local', 'future-law-0103-ghi789.trial.local', 'admin123', '["crm"]', 7, DATE_ADD(NOW(), INTERVAL 7 DAY), 'active', TRUE, 'اختبار تطبيق CRM'),

('شركة الرياض للعقارات', 'ليلى أحمد المطري', 'layla@riyadh-realestate.net', '+967-4-567890', 'riyadh-realestate-0104-jkl012', 'http://riyadh-realestate-0104-jkl012.trial.local', 'riyadh-realestate-0104-jkl012.trial.local', 'admin123', '["erpnext", "crm", "website"]', 21, DATE_ADD(NOW(), INTERVAL 21 DAY), 'active', TRUE, 'عميل شامل بتطبيقات متعددة'),

('أكاديمية النجاح التعليمية', 'سعد محمد السعدي', 'saad@success-academy.edu', '+967-5-678901', 'success-academy-0105-mno345', 'http://success-academy-0105-mno345.trial.local', 'success-academy-0105-mno345.trial.local', 'admin123', '["lms"]', 14, DATE_ADD(NOW(), INTERVAL 14 DAY), 'active', TRUE, 'منصة تعليمية');

-- Sample expired trials
INSERT IGNORE INTO trial_customers
(company_name, contact_name, email, phone, subdomain, site_url, site_name, admin_password, selected_apps, trial_days, created_at, expires_at, status, frappe_site_created, notes)
VALUES
('شركة التقدم للصناعة', 'علي سالم محمد', 'ali@taqaddum-ind.com', '+967-6-789012', 'taqaddum-ind-123-expired', 'http://taqaddum-ind-123-expired.trial.local', 'taqaddum-ind-123-expired.trial.local', 'admin123', '["erpnext"]', 14, DATE_SUB(NOW(), INTERVAL 20 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY), 'expired', TRUE, 'فترة تجريبية انتهت'),

('مؤسسة الإبداع للتدريب', 'نورة حسن علي', 'noura@ibdaa-training.com', '+967-7-890123', 'ibdaa-training-456-expired', 'http://ibdaa-training-456-expired.trial.local', 'ibdaa-training-456-expired.trial.local', 'admin123', '["hrms", "lms"]', 7, DATE_SUB(NOW(), INTERVAL 15 DAY), DATE_SUB(NOW(), INTERVAL 8 DAY), 'expired', TRUE, 'فترة قصيرة انتهت');

-- Sample converted customers (became paid customers)
INSERT IGNORE INTO trial_customers
(company_name, contact_name, email, phone, subdomain, site_url, site_name, admin_password, selected_apps, trial_days, created_at, expires_at, status, frappe_site_created, notes)
VALUES
('بنك الأمان', 'خالد أحمد الربيعي', 'khaled@aman-bank.com', '+967-771-123456', 'aman-bank-789-converted', 'http://aman-bank-789-converted.trial.local', 'aman-bank-789-converted.trial.local', 'admin123', '["erpnext", "crm", "hrms"]', 14, DATE_SUB(NOW(), INTERVAL 45 DAY), DATE_SUB(NOW(), INTERVAL 31 DAY), 'converted', TRUE, 'تحول لعميل مدفوع - بنك كبير'),

('جامعة الحكمة', 'د. سامي محمد العلوي', 'sami@hikma-university.edu', '+967-772-234567', 'hikma-university-012-converted', 'http://hikma-university-012-converted.trial.local', 'hikma-university-012-converted.trial.local', 'admin123', '["lms", "erpnext"]', 30, DATE_SUB(NOW(), INTERVAL 60 DAY), DATE_SUB(NOW(), INTERVAL 30 DAY), 'converted', TRUE, 'تحول لعميل مدفوع - جامعة');

-- Show completion message
SELECT 'SaaS Trial System Database initialized successfully!' as status;
