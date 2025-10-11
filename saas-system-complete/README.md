# 🌟 SaaS Trial System - نظام التجارب المجانية

<div dir="rtl">

## 📋 نظرة عامة

نظام SaaS متكامل لإنشاء وإدارة حسابات تجريبية (Trial Accounts) لـ Frappe/ERPNext بشكل آلي وسريع. يوفر واجهة مستخدم سهلة لإنشاء مواقع تجريبية في ثوانٍ معدودة.

## ✨ المميزات الرئيسية

### 🚀 الأتمتة الكاملة
- ✅ إنشاء مواقع Frappe تلقائياً
- ✅ تكوين Nginx ديناميكياً
- ✅ إدارة قواعد البيانات تلقائياً
- ✅ توليد نطاقات فرعية (subdomains) فريدة

### 🎨 واجهة مستخدم احترافية
- ✅ تصميم Bootstrap 5 متجاوب
- ✅ دعم كامل للغة العربية (RTL)
- ✅ تجربة مستخدم سلسة
- ✅ معالجة الأخطاء بشكل واضح

### 📦 التطبيقات المدعومة
- **ERPNext** 📊: نظام تخطيط الموارد الشامل
- **HRMS** 👥: إدارة الموارد البشرية
- **CRM** 🤝: إدارة علاقات العملاء
- **LMS** 🎓: نظام إدارة التعلم
- **Website** 🌐: منشئ مواقع الويب

### 🔧 مرونة في الإعدادات
- ⏰ مدة تجربة قابلة للتخصيص (7، 14، 30 يوم)
- 🎯 اختيار متعدد للتطبيقات
- 📊 تتبع حالة الحسابات

## 🏗️ المعمارية التقنية

### المكونات الرئيسية

```
┌─────────────────────────────────────────────────┐
│          Frontend (Nginx + HTML/JS)             │
│         172.22.0.100:8082                       │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│        Backend API (Flask Python)               │
│         172.22.0.101:5000                       │
├─────────────────────────────────────────────────┤
│  • TrialManager                                 │
│  • FrappeDirectManager                          │
│  • NginxManager                                 │
│  • DatabaseManager                              │
└─────────────────┬───────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐
│ MySQL   │  │ Frappe  │  │  Nginx   │
│ Database│  │ Servers │  │  Proxy   │
│ :3306   │  │ :8000/1 │  │  :80     │
└─────────┘  └─────────┘  └──────────┘
```

## 🚀 التشغيل السريع

### المتطلبات الأساسية

```bash
# البرامج المطلوبة
- Docker >= 20.10
- Docker Compose >= 2.0
- 4GB RAM (8GB مستحسن)
- 20GB مساحة تخزين

# الشبكة المطلوبة
frappe-cluster-net (يجب أن تكون موجودة مسبقاً)
```

### 1. إنشاء الشبكة (إذا لم تكن موجودة)

```bash
docker network create \
  --driver=bridge \
  --subnet=172.22.0.0/16 \
  --gateway=172.22.0.1 \
  frappe-cluster-net
```

### 2. تشغيل النظام

```bash
# الطريقة الأولى: استخدام النص البرمجي
cd saas-system-complete
chmod +x scripts/start.sh
./scripts/start.sh

# الطريقة الثانية: مباشرة
docker-compose up -d --build
```

### 3. التحقق من التشغيل

```bash
# التحقق من حالة الحاويات
docker-compose ps

# التحقق من صحة النظام
curl http://localhost:5000/api/health

# عرض السجلات
docker-compose logs -f backend
```

### 4. الوصول للنظام

| الخدمة | المنفذ | الرابط |
|--------|--------|---------|
| الواجهة الأمامية | 8082 | http://localhost:8082 |
| Backend API | 5000 | http://localhost:5000 |
| قاعدة البيانات | 3306 | mysql://172.22.0.102:3306 |

## 📁 هيكل المشروع

```
saas-system-complete/
├── backend/                        # Flask Backend
│   ├── app.py                     # التطبيق الرئيسي
│   ├── frappe_direct_manager.py   # إدارة Frappe
│   ├── nginx_manager.py           # إدارة Nginx
│   ├── requirements.txt           # المكتبات المطلوبة
│   ├── Dockerfile                 # بناء صورة Backend
│   ├── config/                    # ملفات التكوين
│   ├── models/                    # نماذج البيانات
│   ├── routes/                    # نقاط النهاية
│   └── utils/                     # أدوات مساعدة
│
├── frontend/                      # واجهة المستخدم
│   ├── index.html                # الصفحة الرئيسية
│   ├── select-apps.html          # اختيار التطبيقات
│   ├── signup.html               # التسجيل
│   ├── success.html              # النجاح
│   ├── demo.html                 # العرض التجريبي
│   ├── book-demo.html            # حجز موعد
│   ├── css/                      # ملفات CSS
│   │   └── style.css
│   └── js/                       # ملفات JavaScript
│       └── main.js
│
├── nginx/                         # إعدادات Nginx
│   ├── nginx.conf                # التكوين الرئيسي
│   ├── frontend.conf             # تكوين الواجهة
│   └── trial-sites.conf          # تكوين المواقع التجريبية
│
├── scripts/                       # نصوص التشغيل
│   ├── start.sh                  # تشغيل النظام
│   └── stop.sh                   # إيقاف النظام
│
├── docker-compose.yml             # تعريف الخدمات
└── README.md                      # هذا الملف
```

## 🔌 API Documentation

### 1. فحص صحة النظام
```bash
GET /api/health

Response:
{
  "success": true,
  "message": "✅ النظام يعمل بشكل صحيح",
  "database": "✅ متصل",
  "frappe_press": "✅ متصل (3 مواقع)",
  "timestamp": "2025-01-08T14:30:00"
}
```

### 2. إنشاء حساب تجريبي
```bash
POST /api/create-trial
Content-Type: application/json

Request Body:
{
  "company_name": "شركة المثال",
  "full_name": "أحمد محمد",
  "email": "ahmad@example.com",
  "phone": "0512345678",
  "password": "SecurePass123",
  "selected_apps": ["erpnext", "hrms"],
  "trial_days": 14
}

Response:
{
  "success": true,
  "site_url": "http://example-0108-abc123.trial.local",
  "message": "🎉 تم إنشاء موقعك التجريبي بنجاح!",
  "execution_time": "5.23 ثانية"
}
```

### 3. قائمة المواقع
```bash
GET /api/frappe-sites

Response:
{
  "success": true,
  "sites": [
    "example1.trial.local",
    "example2.trial.local"
  ],
  "count": 2
}
```

### 4. حالة موقع معين
```bash
GET /api/site-status/example.trial.local

Response:
{
  "success": true,
  "site_name": "example.trial.local",
  "nginx_config": true,
  "frappe_status": "connected"
}
```

### 5. أحدث العملاء
```bash
GET /api/recent-customers?limit=10

Response:
{
  "success": true,
  "customers": [...],
  "count": 10
}
```

### 6. إدارة Nginx
```bash
# حالة Nginx
GET /api/nginx/status

# إعادة تحميل
POST /api/nginx/reload

# قائمة المواقع
GET /api/nginx/sites

# اختبار التكوين
GET /api/nginx/test-config
```

## 🗄️ قاعدة البيانات

### جدول trial_customers

```sql
CREATE TABLE trial_customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    subdomain VARCHAR(100) NOT NULL UNIQUE,
    site_url VARCHAR(255) NOT NULL,
    site_name VARCHAR(255),
    admin_password VARCHAR(100),
    selected_apps TEXT,
    trial_days INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    status ENUM('active', 'expired', 'converted') DEFAULT 'active',
    frappe_site_created BOOLEAN DEFAULT FALSE
);
```

### الاتصال بقاعدة البيانات

```bash
# من داخل Docker
docker exec -it saas-database-v1 mysql -u root -p123456 saas_trialsv1

# من الخارج
mysql -h 172.22.0.102 -u root -p123456 saas_trialsv1
```

## 🔧 التكوين والإعدادات

### متغيرات البيئة

```bash
# Backend (docker-compose.yml)
FLASK_ENV=production
DB_HOST=172.22.0.102
DB_USER=root
DB_PASSWORD=123456
DB_NAME=saas_trialsv1
SECRET_KEY=your-secret-key-change-in-production
DOCKER_HOST=unix:///var/run/docker.sock
```

### تخصيص مدة التجربة

```python
# في backend/app.py
DEFAULT_TRIAL_DAYS = 14  # عدد الأيام الافتراضية
```

### تخصيص عناوين IP

```yaml
# في docker-compose.yml
networks:
  frappe-cluster-net:
    ipv4_address: 172.22.0.100  # للواجهة الأمامية
```

## 🔍 المراقبة والصيانة

### عرض السجلات

```bash
# سجلات Backend
docker logs -f saas-backend-v1

# سجلات Frontend
docker logs -f saas-frontend-v1

# سجلات قاعدة البيانات
docker logs -f saas-database-v1

# جميع السجلات
docker-compose logs -f
```

### مراقبة الأداء

```bash
# حالة الحاويات
docker stats

# استخدام الموارد
docker-compose top

# مساحة التخزين
docker system df
```

### النسخ الاحتياطي

```bash
# نسخ احتياطي لقاعدة البيانات
docker exec saas-database-v1 mysqldump -u root -p123456 saas_trialsv1 > backup_$(date +%Y%m%d).sql

# استعادة
docker exec -i saas-database-v1 mysql -u root -p123456 saas_trialsv1 < backup_20250108.sql

# نسخ احتياطي للـ volumes
docker run --rm -v saas_data-v1:/data -v $(pwd):/backup \
  alpine tar czf /backup/saas_data_backup.tar.gz /data
```

## 🛠️ استكشاف الأخطاء

### Backend لا يعمل

```bash
# التحقق من السجلات
docker logs saas-backend-v1

# إعادة التشغيل
docker-compose restart backend

# إعادة البناء
docker-compose up -d --build backend
```

### Frontend لا يظهر

```bash
# اختبار تكوين Nginx
docker exec saas-frontend-v1 nginx -t

# إعادة تحميل Nginx
docker exec saas-frontend-v1 nginx -s reload

# التحقق من الملفات
docker exec saas-frontend-v1 ls -la /usr/share/nginx/html
```

### مشاكل قاعدة البيانات

```bash
# التحقق من الاتصال
docker exec saas-database-v1 mysqladmin -u root -p123456 ping

# إصلاح الجداول
docker exec saas-database-v1 mysqlcheck -u root -p123456 --auto-repair saas_trialsv1

# إعادة إنشاء قاعدة البيانات
docker exec -it saas-database-v1 mysql -u root -p123456
DROP DATABASE saas_trialsv1;
CREATE DATABASE saas_trialsv1;
```

### مشاكل الشبكة

```bash
# التحقق من الشبكة
docker network inspect frappe-cluster-net

# إعادة إنشاء الشبكة
docker network rm frappe-cluster-net
docker network create --driver=bridge --subnet=172.22.0.0/16 frappe-cluster-net

# اختبار الاتصال
docker exec saas-backend-v1 ping -c 3 172.22.0.102
```

## 🔐 الأمان

### تغيير كلمات المرور

```bash
# كلمة مرور قاعدة البيانات
docker exec -it saas-database-v1 mysql -u root -p
ALTER USER 'root'@'%' IDENTIFIED BY 'NewSecurePassword';
FLUSH PRIVILEGES;

# تحديث في docker-compose.yml و app.py
```

### تفعيل HTTPS

```bash
# إضافة شهادات SSL
mkdir -p nginx/ssl
# ضع fullchain.pem و privkey.pem في nginx/ssl/

# تحديث nginx.conf
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
}
```

### Rate Limiting

```nginx
# في nginx/frontend.conf
limit_req_zone $binary_remote_addr zone=trial_limit:10m rate=5r/m;

location /api/create-trial {
    limit_req zone=trial_limit burst=3;
    proxy_pass http://backend:5000;
}
```

## 📈 التطوير والمساهمة

### إعداد بيئة التطوير

```bash
# استنساخ المشروع
git clone <repository-url>
cd saas-system-complete

# تثبيت المكتبات Python
cd backend
pip install -r requirements.txt

# تشغيل Backend في وضع التطوير
python app.py

# Frontend - لا يحتاج إعداد إضافي
```

### إضافة تطبيق جديد

```javascript
// في frontend/select-apps.html
const AVAILABLE_APPS = [
    // ... التطبيقات الموجودة
    { 
        id: 'new_app', 
        name: 'New App', 
        description: 'وصف التطبيق الجديد', 
        icon: '🆕'
    }
];
```

### إضافة API endpoint جديد

```python
# في backend/app.py
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    try:
        data = request.json
        # معالجة البيانات
        return jsonify({
            'success': True,
            'message': 'تم بنجاح'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

## 🧪 الاختبار

### اختبار Backend API

```bash
# فحص الصحة
curl http://localhost:5000/api/health

# إنشاء حساب تجريبي
curl -X POST http://localhost:5000/api/create-trial \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "full_name": "Test User",
    "email": "test@example.com",
    "password": "test123",
    "selected_apps": ["erpnext"],
    "trial_days": 14
  }'
```

### اختبار الأداء

```bash
# باستخدام Apache Bench
ab -n 100 -c 10 http://localhost:5000/api/health

# باستخدام wrk
wrk -t4 -c100 -d30s http://localhost:8082/
```

## 📊 الإحصائيات

```bash
# عدد العملاء النشطين
docker exec -it saas-database-v1 mysql -u root -p123456 -e \
  "SELECT COUNT(*) FROM saas_trialsv1.trial_customers WHERE status='active';"

# المواقع المنشأة اليوم
docker exec -it saas-database-v1 mysql -u root -p123456 -e \
  "SELECT COUNT(*) FROM saas_trialsv1.trial_customers WHERE DATE(created_at) = CURDATE();"

# أكثر التطبيقات طلباً
docker exec -it saas-database-v1 mysql -u root -p123456 -e \
  "SELECT selected_apps, COUNT(*) as count FROM saas_trialsv1.trial_customers GROUP BY selected_apps ORDER BY count DESC LIMIT 5;"
```

## 🔄 التحديث

```bash
# سحب أحدث التغييرات
git pull origin main

# إعادة البناء
docker-compose down
docker-compose up -d --build

# ترحيل قاعدة البيانات (إذا لزم)
# قم بتشغيل نصوص الترحيل هنا
```

## 📝 الترخيص

هذا المشروع مرخص تحت MIT License.

## 🤝 المساهمة

نرحب بالمساهمات! يرجى:
1. Fork المشروع
2. إنشاء فرع للميزة (`git checkout -b feature/NewFeature`)
3. Commit التغييرات (`git commit -m 'Add NewFeature'`)
4. Push للفرع (`git push origin feature/NewFeature`)
5. فتح Pull Request

## 📞 الدعم والتواصل

- 📧 البريد: support@example.com
- 💬 Discord: https://discord.gg/example
- 📖 التوثيق: https://docs.example.com
- 🐛 الأخطاء: https://github.com/example/issues

## 🙏 شكر وتقدير

- [Frappe Framework](https://frappeframework.com/)
- [ERPNext](https://erpnext.com/)
- [Flask](https://flask.palletsprojects.com/)
- [Bootstrap](https://getbootstrap.com/)
- [Docker](https://www.docker.com/)

---

Made with ❤️ for the Arabic Community

</div>
