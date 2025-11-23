#!/bin/bash
echo "📥 Pulling images from local registry: hub.ittech-ye.net"

# تسجيل الدخول للـ Registry المحلي
docker login hub.ittech-ye.net

# سحب الصور من الـ Registry المحلي
docker pull hub.ittech-ye.net/frappe/erpnext:version-15
docker pull hub.ittech-ye.net/mariadb:10.6
docker pull hub.ittech-ye.net/redis:alpine

# التحقق من الصور
echo "✅ Images pulled successfully:"
docker images | grep hub.ittech-ye.net