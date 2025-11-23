#!/bin/bash
echo "🚀 Initializing Frappe with host storage..."

# أوقف الخدمات إذا كانت شغالة
docker-compose down

# أنشئ المجلدات إذا لم تكن موجودة
if [ ! -d "./data" ]; then
    echo "📁 Creating folder structure..."
    chmod +x create-folders.sh
    ./create-folders.sh
fi

# ابدأ الخدمات
echo "🐳 Starting containers..."
docker-compose up -d

# انتظر حتى تكون قاعدة البيانات جاهزة
echo "⏳ Waiting for database..."
sleep 30

# تحقق من اتصال قاعدة البيانات
echo "🔍 Testing database connection..."
docker exec frappe-coder-app mysql -h db-primary -u root -p123456 -e "SHOW DATABASES;" || {
    echo "❌ Database connection failed"
    exit 1
}

# أنشئ الموقع إذا لم يكن موجود
echo "🌐 Setting up Frappe site..."
docker exec frappe-coder-app bash -c "
cd /home/frappe/frappe-bench

if [ ! -f 'sites/sites.json' ]; then
    echo '📦 Creating new site...'
    bench new-site erpnext.local --db-root-password 123456 --admin-password admin123
    bench --site erpnext.local install-app erpnext
else
    echo '✅ Site already exists'
fi

echo '🎉 Frappe setup completed!'
"

echo "✅ Initialization completed!"
echo "📁 All data stored in: /workspaces/.devcontainer/data/"
echo "🌐 Access at: http://localhost:8001"
echo "🔑 Admin: Administrator / admin123"
echo "💾 To backup: just copy the ./data folder"