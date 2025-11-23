#!/bin/bash

echo "🚀 Setting up Frappe/ERPNext in Coder..."

# الانتقال إلى مجلد العمل
cd /home/frappe/frappe-bench

# إذا لم يكن هناك موقع، قم بإنشاء واحد
if [ ! -f "sites/sites.json" ]; then
    echo "📦 Creating new site..."
    bench new-site erpnext.local --db-root-password 123456 --admin-password admin123
fi

# بدء خدمات Frappe
echo "🔄 Starting Frappe services..."
bench start &

echo "✅ Setup completed! Frappe is ready at http://localhost:8000"
echo "🔑 Admin credentials: Administrator / admin123"