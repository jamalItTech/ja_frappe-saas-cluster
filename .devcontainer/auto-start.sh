#!/bin/bash
# هذا الملف يشتغل تلقائياً عند فتح Coder

echo "🚀 Auto-starting Frappe ERPNext..."

# أنشئ المجلدات إذا لم تكن موجودة
mkdir -p /workspaces/frappe-data/{sites,apps,logs,config,mariadb,redis/{cache,queue,socketio}}

# أنشئ الملفات الأساسية إذا لم تكن موجودة
if [ ! -f "/workspaces/frappe-data/config/Procfile" ]; then
    echo "📁 Creating initial Frappe configuration..."
    
    # Procfile
    cat > /workspaces/frappe-data/config/Procfile << 'EOF'
web: bench serve --port 8000
socketio: /home/frappe/frappe-bench/env/bin/node /home/frappe/frappe-bench/apps/frappe/socketio.js
watch: bench watch
worker: bench worker --queue default
worker_short: bench worker --queue short
worker_long: bench worker --queue long
EOF

    # common_site_config.json
    mkdir -p /workspaces/frappe-data/config/sites
    cat > /workspaces/frappe-data/config/sites/common_site_config.json << 'EOF'
{
 "db_host": "db-primary",
 "db_port": 3306,
 "db_name": "frappe",
 "db_password": "123456",
 "db_type": "mariadb",
 "auto_cache_clear": 1,
 "redis_cache": "redis://redis-cache:6379",
 "redis_queue": "redis://redis-queue:6379",
 "redis_socketio": "redis://redis-socketio:6379"
}
EOF
fi

# ابدأ الحاويات
echo "🐳 Starting Docker containers..."
cd /workspaces/.devcontainer
docker-compose up -d

# انتظر تهيئة الخدمات
echo "⏳ Waiting for services to start..."
sleep 30

# تحقق من اتصال قاعدة البيانات
if docker exec frappe-coder-db mysql -u root -p123456 -e "USE frappe;" 2>/dev/null; then
    echo "✅ Database is ready"
else
    echo "🔧 Initializing database..."
    docker exec frappe-coder-db mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS frappe;"
fi

# ابدأ Frappe إذا كانت البيانات موجودة
if [ -f "/workspaces/frappe-data/sites/sites.json" ]; then
    echo "🎯 Starting Frappe services..."
    docker exec -d frappe-coder-app bash -c "cd /home/frappe/frappe-bench && bench start --daemon"
    echo "🌐 Frappe is starting at: http://localhost:8000"
else
    echo "💡 Run './setup-frappe.sh' to complete initial setup"
fi

echo "✅ Auto-start completed!"