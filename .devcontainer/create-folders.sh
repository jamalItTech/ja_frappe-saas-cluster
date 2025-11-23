#!/bin/bash
echo "📁 Creating folder structure in /workspaces/.devcontainer..."

# أنشئ الهيكل الكامل للمجلدات
mkdir -p ./data/{frappe,mariadb,redis}
mkdir -p ./data/frappe/{sites,apps,logs,config}
mkdir -p ./data/redis/{cache,queue,socketio}

# أنشئ الملفات الأساسية لـ Frappe
mkdir -p ./data/frappe/config/sites

# أنشئ common_site_config.json
cat > ./data/frappe/config/sites/common_site_config.json << 'EOF'
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

# أنشئ Procfile
cat > ./data/frappe/config/Procfile << 'EOF'
web: bench serve --port 8000
socketio: /home/frappe/frappe-bench/env/bin/node /home/frappe/frappe-bench/apps/frappe/socketio.js
watch: bench watch
worker: bench worker --queue default
worker_short: bench worker --queue short
worker_long: bench worker --queue long
EOF

# أنشئ apps.json
cat > ./data/frappe/config/sites/apps.json << 'EOF'
[
 {
  "name": "frappe",
  "app_name": "frappe",
  "app_version": "version-15"
 }
]
EOF

# اضبط الصلاحيات
chmod -R 755 ./data
echo "✅ Folder structure created successfully!"
echo "📁 Location: /workspaces/.devcontainer/data/"