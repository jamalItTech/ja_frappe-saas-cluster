#!/bin/bash
# scripts/health-check.sh
echo "🏥 Cluster Health Check"

# فحص الخوادم
echo "🔍 Checking servers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# فحص الشبكة
echo "🌐 Checking network..."
ping -c 2 db-primary > /dev/null && echo "✅ Database network: OK" || echo "❌ Database network: Failed"
ping -c 2 redis-server > /dev/null && echo "✅ Redis network: OK" || echo "❌ Redis network: Failed"

# فحص التطبيقات
echo "📱 Checking applications..."
curl -f http://app-server-1:8000 > /dev/null 2>&1 && echo "✅ App Server 1: OK" || echo "❌ App Server 1: Failed"
curl -f http://app-server-2:8000 > /dev/null 2>&1 && echo "✅ App Server 2: OK" || echo "❌ App Server 2: Failed"
curl -f http://app-server-3:8000 > /dev/null 2>&1 && echo "✅ App Server 3: OK" || echo "❌ App Server 3: Failed"

echo "📊 Health check completed"
