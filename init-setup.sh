#!/bin/bash
# init-setup.sh - إعداد Frappe Press تلقائياً

echo "🚀 Starting Frappe Press Setup..."

# انتظر حتى تبدأ الخدمات
sleep 30

# إعداد app-server-1
docker exec app-server-1 bash -c "
cd /home/frappe/production

# تثبيت تطبيق Press
echo '📦 Installing Frappe Press...'
bench get-app press https://github.com/frappe/press

# إنشاء موقع Press
echo '🌐 Creating Press site...'
bench new-site press.localdev.me --db-root-password 123456 --admin-password admin123 --force

# تثبيت التطبيق على الموقع
echo '⚙️ Installing Press on site...'
bench --site press.localdev.me install-app press

# إعداد common_site_config.json
echo '📄 Configuring site settings...'
cat > sites/common_site_config.json << 'EOF'
{
 \"db_host\": \"db-primary\",
 \"db_port\": 3306,
 \"db_password\": \"123456\",
 \"redis_cache\": \"redis://redis-server:6379/1\",
 \"redis_queue\": \"redis://redis-server:6379/2\", 
 \"redis_socketio\": \"redis://redis-server:6379/3\",
 \"use_redis_auth\": false
}
EOF

echo '✅ Frappe Press setup completed!'
"

echo "🎉 Setup finished! Access your sites:"
echo "   - Press: https://press.localdev.me"
echo "   - Site 1: https://site1.localdev.me" 
echo "   - Site 2: https://site2.localdev.me"