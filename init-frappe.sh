#!/bin/bash
set -e

cd /home/frappe/frappe-bench

# تحقق إذا كان Bench موجوداً
if [ ! -f apps.txt ]; then
    echo "Initializing new bench..."
    bench init --skip-redis-config-generation --frappe-branch version-15 frappe-bench
    cd frappe-bench
fi

cd frappe-bench

# تحقق إذا كان الموقع موجوداً
if ! bench list-sites | grep -q "site1.local"; then
    echo "Creating new site..."
    bench new-site --force \
        --db-host $DB_HOST \
        --db-port $DB_PORT \
        --db-root-password $MYSQL_ROOT_PASSWORD \
        --admin-password $ADMIN_PASSWORD \
        site1.local
fi

echo "Setting site..."
bench use site1.local

echo "Starting bench server..."
bench start