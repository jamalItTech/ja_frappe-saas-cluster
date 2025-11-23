#!/bin/bash
REGISTRY="hub.ittech-ye.net"

echo "🚀 بدء رفع الحاويات إلى Registry المحلي..."

# تسجيل الدخول
sudo docker login hub.ittech-ye.net

# رفع app-server-1
echo "📦 رفع app-server-1..."
docker commit db-primary hub.ittech-ye.net/frappe/db-primary:v1

sudo docker commit app-server-1 hub.ittech-ye.net/app-server-1:v1
docker tag  hub.ittech-ye.net/app-server-1:v1 hub.ittech-ye.net/frappe/app-server-1:v1
# sudo docker tag hub.ittech-ye.net/app-server-1:v1 hub.ittech-ye.net/app-server-1:$(date +%Y%m%d)
sudo docker push hub.ittech-ye.net/app-server-1:v1
# sudo docker push hub.ittech-ye.net/app-server-1:$(date +%Y%m%d)

# رفع app-server-2
# echo "📦 رفع app-server-2..."
# sudo docker commit app-server-2 hub.ittech-ye.net/app-server-2:v1
# sudo docker tag hub.ittech-ye.net/app-server-2:v1 hub.ittech-ye.net/app-server-2:$(date +%Y%m%d)
# sudo docker push hub.ittech-ye.net/app-server-2:v1
# sudo docker push hub.ittech-ye.net/app-server-2:$(date +%Y%m%d)

echo "✅ تم الرفع بنجاح!"
echo "📋 Images المتاحة:"
sudo docker images | grep hub.ittech-ye.net