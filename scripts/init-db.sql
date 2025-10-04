-- scripts/init-db.sql
CREATE DATABASE IF NOT EXISTS frappe_production;
CREATE USER IF NOT EXISTS 'frappe_user'@'%' IDENTIFIED BY 'frappe123';
GRANT ALL PRIVILEGES ON frappe_production.* TO 'frappe_user'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'frappe_user'@'%';
FLUSH PRIVILEGES;
