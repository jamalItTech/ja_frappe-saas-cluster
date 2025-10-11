#!/bin/bash

echo "🚀 بدء تشغيل نظام SaaS Trial..."

# التحقق من وجود Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker غير مثبت. يرجى تثبيت Docker أولاً."
    exit 1
fi

# بناء وتشغيل الحاويات
echo "📦 بناء وتشغيل الحاويات..."
docker-compose down
docker-compose up -d --build

# الانتظار للتأكد من تشغيل الخدمات
echo "⏳ انتظار تهيئة الخدمات..."
sleep 10

# التحقق من حالة الخدمات
echo "🔍 التحقق من حالة الخدمات..."
docker-compose ps

echo "✅ تم تشغيل النظام بنجاح!"
echo "🌐 الواجهة الأمامية: http://localhost:8081"
echo "⚡ الواجهة الخلفية: http://localhost:5000"
echo "🗄️ إدارة قاعدة البيانات: http://localhost:8081"
