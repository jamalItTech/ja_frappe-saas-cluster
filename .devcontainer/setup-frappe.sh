#!/bin/bash
echo "🎯 Complete Frappe Setup..."

# تأكد أن الحاويات شغالة
cd /workspaces/.devcontainer
docker-compose up -d
sleep 20

# أنشئ الموقع
echo "📦 Creating Frappe site..."
docker exec frappe-coder-app bash -c "
cd /home/frappe/frappe-bench

# أنشئ الموقع
bench new-site erpnext.local --db-root-password 123456 --admin-password admin123

# ثبت ERPNext
bench get-app erpnext 
bench --site erpnext.local install-app erpnext

# ابدأ الخدمات
bench start --daemon
"

echo "✅ Setup completed!"
echo "🌐 Access: http://localhost:8000"
echo "🔑 Admin: Administrator / admin123"
echo "💾 Data stored in: /workspaces/frappe-data/"