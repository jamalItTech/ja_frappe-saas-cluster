#!/bin/bash
echo "🚀 Pushing images to local registry: hub.ittech-ye.net"

# تسجيل الدخول للـ Registry المحلي (إذا يحتاج مصادقة)
docker login hub.ittech-ye.net

# سحب الصور الأصلية من Docker Hub
echo "📥 Pulling original images..."
docker pull frappe/erpnext:version-15
docker pull mariadb:10.6
docker pull redis:alpine

# إعادة تسمية الصور للـ Registry المحلي
echo "🏷️ Tagging images for local registry..."
docker tag frappe/erpnext:version-15 hub.ittech-ye.net/frappe/erpnext:version-15
docker tag mariadb:10.6 hub.ittech-ye.net/mariadb:10.6
docker tag redis:alpine hub.ittech-ye.net/redis:alpine

# رفع الصور للـ Registry المحلي
echo "📤 Pushing images to local registry..."
docker push hub.ittech-ye.net/frappe/erpnext:version-15
docker push hub.ittech-ye.net/mariadb:10.6
docker push hub.ittech-ye.net/redis:alpine

# تنظيف الصور المحلية القديمة (اختياري)
echo "🧹 Cleaning up local images..."
docker rmi frappe/erpnext:version-15
docker rmi mariadb:10.6
docker rmi redis:alpine

echo "✅ All images pushed to hub.ittech-ye.net successfully!"
echo "📦 Images available:"
echo "   - hub.ittech-ye.net/frappe/erpnext:version-15"
echo "   - hub.ittech-ye.net/mariadb:10.6"
echo "   - hub.ittech-ye.net/redis:alpine"