#!/bin/bash

echo "🚀 بدء حفظ التغييرات ورفع الصور المحدثة..."

# تعريف الريجستري
REGISTRY="hub.ittech-ye.net"

# 1. حفظ حاوية قاعدة البيانات المحدثة
echo "📦 حفظ حاوية db-primary المحدثة..."
docker commit db-primary hub.ittech-ye.net/frappe/db-primary:v1
docker push $REGISTRY/frappe/db-primary:v1

# 2. حفظ حاوية التطبيقات المحدثة
echo "📦 حفظ حاوية app-server-1 المحدثة..."
docker commit app-server-1 $REGISTRY/frappe/app-server-1:v1
docker push $REGISTRY/frappe/app-server-1:v1

echo "✅ تم حفظ ورفع الصور المحدثة بنجاح!"
echo "📝 الإصدارات الجديدة: v1"
