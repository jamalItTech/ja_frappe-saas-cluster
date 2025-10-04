#!/bin/bash
# scripts/setup-sites.sh
echo "🚀 Setting up production sites..."

cd /home/frappe/production

# إنشاء المواقع الأساسية
sites=(
    "press-admin.com"
    "almansor-group.com" 
    "tadawul-finance.com"
    "saudi-tech.com"
    "client-company1.com"
    "client-company2.com"
)

for site in "${sites[@]}"; do
    echo "Creating site: $site"
    bench new-site $site --db-host=$DB_HOST --db-root-password=$DB_PASSWORD --install-app erpnext --install-app press --force
done

# بناء الأصول
echo "Building assets..."
bench build

echo "✅ All sites created successfully"
