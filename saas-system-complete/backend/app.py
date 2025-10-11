from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import json
import random
import string
import logging
import time
import os
from datetime import datetime, timedelta
from nginx_manager import nginx_manager

from frappe_direct_manager import get_frappe_direct_manager
import requests

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# إعدادات قاعدة البيانات SaaS من docker-compose.yml
DB_CONFIG = {
    'host': os.getenv('SAAS_DB_HOST', '172.25.0.100'),  # saas-database من docker-compose
    'user': os.getenv('SAAS_DB_USER', 'saas_user'),
    'password': os.getenv('SAAS_DB_PASSWORD', 'saas_db_pass_2025'),  # كلمة المرور من متغير البيئة
    'database': os.getenv('SAAS_DB_NAME', 'saas_trials_light'),  # اسم قاعدة البيانات
    'port': int(os.getenv('SAAS_DB_PORT', 3306)),  # البورت من متغير البيئة
    'connect_timeout': 30,
}

def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {str(e)}")
        raise e

class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """تهيئة قاعدة البيانات"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Ensure the database is using the correct database from config
            cursor.execute(f"USE {DB_CONFIG['database']}")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trial_customers (
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
                trial_days INT NOT NULL DEFAULT 14,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                status ENUM('active', 'expired', 'converted') DEFAULT 'active',
                frappe_site_created BOOLEAN DEFAULT FALSE,
                notes TEXT,
                INDEX idx_status (status),
                INDEX idx_expires_at (expires_at),
                INDEX idx_created_at (created_at),
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Check cluster_servers table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_servers (
                server_id VARCHAR(50) PRIMARY KEY,
                ip_address VARCHAR(15) NOT NULL,
                port INT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                role ENUM('active', 'standby', 'maintenance') DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_health_check TIMESTAMP NULL,
                cpu_percent FLOAT DEFAULT 0.0,
                memory_percent FLOAT DEFAULT 0.0,
                sites_count INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'unknown',
                INDEX idx_active (active),
                INDEX idx_role (role),
                INDEX idx_last_health_check (last_health_check)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ فشل تهيئة قاعدة البيانات: {str(e)}")
            return False
    
    def create_customer(self, customer_data):
        """إنشاء عميل جديد"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            trial_days = int(customer_data.get('trial_days', 14))
            expires_at = datetime.now() + timedelta(days=trial_days)
            
            query = """
            INSERT INTO trial_customers 
            (company_name, contact_name, email, phone, subdomain, site_url, site_name, 
             admin_password, selected_apps, trial_days, expires_at, frappe_site_created)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                customer_data['company_name'],
                customer_data['full_name'],
                customer_data['email'],
                customer_data.get('phone', ''),
                customer_data['subdomain'],
                customer_data['site_url'],
                customer_data['site_name'],
                customer_data.get('admin_password', 'admin123'),
                json.dumps(customer_data.get('selected_apps', [])),
                trial_days,
                expires_at,
                customer_data.get('frappe_site_created', False)
            ))
            
            customer_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ تم حفظ العميل برقم: {customer_id}")
            return customer_id
            
        except Exception as e:
            logger.error(f"❌ فشل حفظ العميل: {str(e)}")
            raise e

    def get_recent_customers(self, limit=10):
        """الحصول على أحدث العملاء"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT * FROM trial_customers 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            
            customers = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return customers
        except Exception as e:
            logger.error(f"❌ فشل جلب العملاء: {str(e)}")
            return []

class TrialManager:
    """مدير التجارب"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.frappe_manager = get_frappe_direct_manager()
        logger.info(f"✅ تم تهيئة مدير Frappe المباشر: {type(self.frappe_manager).__name__}")
    
    def generate_subdomain(self, company_name):
        """إنشاء subdomain فريد"""
        base_name = company_name.lower().strip()
        base_name = ''.join(c for c in base_name if c.isalnum() or c in ['-', '_'])
        base_name = base_name.replace(' ', '-')[:15]
        
        timestamp = datetime.now().strftime("%m%d%H%M")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        
        subdomain = f"{base_name}-{timestamp}-{random_suffix}"
        logger.info(f"📝 تم إنشاء subdomain: {subdomain}")
        
        return subdomain
    
    def create_trial_account(self, data):
        """إنشاء حساب تجريبي"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['company_name', 'full_name', 'email', 'password']
            for field in required_fields:
                if not data.get(field):
                    return False, f'حقل {field} مطلوب'
            
            # إنشاء subdomain فريد
            subdomain = self.generate_subdomain(data['company_name'])
            site_name = f"{subdomain}.trial.local"
            
            logger.info(f"🚀 بدء إنشاء موقع تجريبي لـ: {data['company_name']}")
            logger.info(f"   Subdomain: {subdomain}")
            logger.info(f"   Site Name: {site_name}")
            logger.info(f"   التطبيقات: {data.get('selected_apps', [])}")
            
            # إنشاء الموقع
            success, site_url = self.frappe_manager.create_trial_site(
                subdomain=subdomain,
                company_name=data['company_name'],
                apps=data.get('selected_apps', ['erpnext']),
                admin_email=data['email']
            )
            
            if not success:
                logger.error(f"❌ فشل إنشاء الموقع: {site_url}")
                return False, f"فشل إنشاء الموقع: {site_url}"
            
            # إعداد بيانات العميل
            customer_data = {
                'company_name': data['company_name'],
                'full_name': data['full_name'],
                'email': data['email'],
                'phone': data.get('phone', ''),
                'subdomain': subdomain,
                'site_url': site_url,
                'site_name': site_name,
                'admin_password': 'admin123',
                'selected_apps': data.get('selected_apps', []),
                'trial_days': data.get('trial_days', 14),
                'frappe_site_created': True
            }
            
            # حفظ في قاعدة البيانات
            customer_id = self.db.create_customer(customer_data)
            
            # إضافة تكوين Nginx للموقع الجديد
            nginx_success, nginx_msg = nginx_manager.create_site_config(site_name)
            if nginx_success:
                logger.info(f"✅ تم إضافة تكوين Nginx: {nginx_msg}")
            else:
                logger.warning(f"⚠️ فشل إضافة تكوين Nginx: {nginx_msg}")
            
            logger.info(f"🎉 تم إنشاء حساب تجريبي بنجاح: {site_url}")
            return True, site_url
            
        except mysql.connector.IntegrityError as e:
            if "Duplicate entry" in str(e):
                return False, 'البريد الإلكتروني مسجل مسبقاً'
            return False, f'خطأ في قاعدة البيانات: {str(e)}'
        except Exception as e:
            logger.error(f"❌ فشل إنشاء الحساب: {str(e)}")
            return False, f'حدث خطأ: {str(e)}'

# إنشاء المانجر
trial_manager = TrialManager()

# نقاط النهاية
@app.route('/api/health', methods=['GET'])
def health_check():
    """التحقق من صحة النظام"""
    print("Health check start", flush=True)
    try:
        print("Connecting to DB", flush=True)
        # اختبار اتصال قاعدة البيانات
        conn = get_db_connection()
        print("Connected, execute SELECT 1", flush=True)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        print("SELECT 1 done", flush=True)
        
        # اختبار اتصال Frappe Press
        print("Getting frappe sites", flush=True)
        sites = trial_manager.frappe_manager.get_all_sites()
        print(f"Sites got: {len(sites)}", flush=True)
        
        cursor.close()
        conn.close()
        print("Connection closed, success", flush=True)
        
        return jsonify({
            'success': True,
            'message': '✅ النظام يعمل بشكل صحيح',
            'database': '✅ متصل',
            'frappe_press': f'✅ متصل ({len(sites)} مواقع)',
            'frappe_manager': type(trial_manager.frappe_manager).__name__,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Health check exception: {str(e)}", flush=True)
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': '❌ نظام قاعدة البيانات غير متصل',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/create-trial', methods=['POST'])
def create_trial():
    """إنشاء حساب تجريبي"""
    start_time = time.time()

    # التأكد من أن الطلب يحتوي على JSON
    if not request.is_json:
        logger.error("❌ Request is not JSON")
        return jsonify({
            'success': False,
            'message': 'طلب غير صحيح - يجب أن يكون JSON',
            'error': 'invalid_content_type'
        }), 400

    try:
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data received")
            return jsonify({
                'success': False,
                'message': 'لم يتم استلام بيانات صحيحة',
                'error': 'no_data'
            }), 400

        logger.info(f"📥 استلام طلب إنشاء حساب لـ: {data.get('company_name', 'غير محدد')}")

        # التحقق من الحقول المطلوبة
        required_fields = ['company_name', 'full_name', 'email']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'الحقول المطلوبة مفقودة: {", ".join(missing_fields)}',
                'error': 'missing_fields'
            }), 400

        success, result = trial_manager.create_trial_account(data)

        execution_time = time.time() - start_time
        logger.info(f"⏱️ وقت تنفيذ الطلب: {execution_time:.2f} ثانية")

        if success:
            response_data = {
                'success': True,
                'site_url': result,
                'message': '🎉 تم إنشاء موقعك التجريبي بنجاح!',
                'type': 'trial_account',
                'execution_time': f"{execution_time:.2f} ثانية"
            }
            logger.info(f"✅ نجح إنشاء الحساب: {response_data}")
            return jsonify(response_data)
        else:
            error_response = {
                'success': False,
                'message': str(result) if result else 'فشل في إنشاء الحساب التجريبي',
                'type': 'creation_error',
                'execution_time': f"{execution_time:.2f} ثانية"
            }
            logger.error(f"❌ فشل إنشاء الحساب: {error_response}")
            return jsonify(error_response), 400

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON Decode Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'بيانات JSON غير صحيحة',
            'error': 'json_decode_error'
        }), 400
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ خطأ في API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في الخادم: {str(e)}',
            'error': 'server_error',
            'execution_time': f"{execution_time:.2f} ثانية"
        }), 500

@app.route('/api/frappe-sites', methods=['GET'])
def get_frappe_sites():
    """الحصول على قائمة المواقع من Frappe Press"""
    try:
        sites = trial_manager.frappe_manager.get_all_sites()
        return jsonify({
            'success': True,
            'sites': sites,
            'count': len(sites)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب المواقع: {str(e)}'
        }), 500

# نقاط نهاية جديدة للتحقق من حالة المواقع وإصلاحها
@app.route('/api/site-status/<path:site_name>', methods=['GET'])
def check_site_status(site_name):
    """التحقق من حالة موقع معين"""
    try:
        # التحقق من وجود تكوين Nginx
        nginx_configs = nginx_manager.list_site_configs()
        has_nginx_config = any(site_name.replace('http://', '').replace('https://', '') in config for config in nginx_configs)
        
        # التحقق من اتصال Frappe
        frappe_status = "unknown"
        frappe_response = ""
        
        try:
            test_url = f"http://{site_name}/api/method/version"
            response = requests.get(test_url, timeout=10)
            frappe_status = "connected" if response.status_code == 200 else "failed"
            frappe_response = response.text[:200] if response.text else "empty"
        except requests.exceptions.ConnectionError:
            frappe_status = "unreachable"
        except requests.exceptions.Timeout:
            frappe_status = "timeout"
        except Exception as e:
            frappe_status = f"error: {str(e)}"
        
        return jsonify({
            'success': True,
            'site_name': site_name,
            'nginx_config': has_nginx_config,
            'frappe_status': frappe_status,
            'frappe_response': frappe_response,
            'nginx_configs': nginx_configs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/fix-site/<path:site_name>', methods=['POST'])
def fix_site_config(site_name):
    """إصلاح تكوين موقع معين"""
    try:
        # تنظيف اسم الموقع من http://
        clean_site_name = site_name.replace('http://', '').replace('https://', '')
        
        # إنشاء تكوين Nginx للموقع
        success, message = nginx_manager.create_site_config(clean_site_name)
        
        if success:
            # اختبار الموقع بعد الإصلاح
            time.sleep(2)
            frappe_status = "unknown"
            try:
                test_url = f"http://{clean_site_name}/api/method/version"
                response = requests.get(test_url, timeout=10)
                frappe_status = "connected" if response.status_code == 200 else "failed"
            except:
                frappe_status = "unreachable"
            
            return jsonify({
                'success': True,
                'message': f'تم إصلاح تكوين الموقع: {message}',
                'frappe_status': frappe_status,
                'site_name': clean_site_name
            })
        else:
            return jsonify({
                'success': False,
                'message': f'فشل إصلاح الموقع: {message}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/recent-customers', methods=['GET'])
def get_recent_customers():
    """الحصول على أحدث العملاء"""
    try:
        customers = trial_manager.db.get_recent_customers(10)
        return jsonify({
            'success': True,
            'customers': customers,
            'count': len(customers)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب العملاء: {str(e)}'
        }), 500

# نقاط نهاية إدارة Nginx
@app.route('/api/nginx/status', methods=['GET'])
def nginx_status():
    """حالة Nginx"""
    try:
        status = nginx_manager.get_nginx_status()
        metrics = nginx_manager.get_nginx_metrics()
        
        return jsonify({
            'success': True,
            'nginx_status': status,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب حالة Nginx: {str(e)}'
        }), 500

@app.route('/api/nginx/reload', methods=['POST'])
def nginx_reload():
    """إعادة تحميل Nginx"""
    try:
        success, message = nginx_manager.reload_nginx()
        
        if success:
            return jsonify({
                'success': True,
                'message': '✅ تم إعادة تحميل Nginx بنجاح'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'❌ فشل إعادة تحميل Nginx: {message}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إعادة تحميل Nginx: {str(e)}'
        }), 500

@app.route('/api/nginx/sites', methods=['GET'])
def nginx_sites():
    """قائمة تكوينات المواقع في Nginx"""
    try:
        configs = nginx_manager.list_site_configs()
        
        return jsonify({
            'success': True,
            'sites_count': len(configs),
            'configs': configs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جرد المواقع: {str(e)}'
        }), 500

@app.route('/api/nginx/test-config', methods=['GET'])
def test_nginx_config():
    """اختبار تكوين Nginx"""
    try:
        success, message = nginx_manager.test_nginx_config()
        
        if success:
            return jsonify({
                'success': True,
                'message': '✅ تكوين Nginx سليم'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'❌ تكوين Nginx غير سليم: {message}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في اختبار التكوين: {str(e)}'
        }), 500

@app.route('/api/debug/frappe-connection', methods=['GET'])
def debug_frappe_connection():
    """تصحيح اتصال Frappe"""
    try:
        # اختبار الاتصال المباشر إلى frappe-app-1 من docker-compose
        frappe_app_ip = '172.25.3.10'  # frappe-light-app-1
        frappe_app_port = 8000

        test_url = f"http://{frappe_app_ip}:{frappe_app_port}/api/method/version"

        response = requests.get(test_url, timeout=10)

        return jsonify({
            'success': True,
            'frappe_host': f"{frappe_app_ip}:{frappe_app_port}",
            'frappe_status': 'connected' if response.status_code == 200 else 'failed',
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', 'unknown'),
            'response_preview': response.text[:200] if response.text else 'empty'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'frappe_status': 'error',
            'frappe_host': '172.25.3.10:8000',
            'error': str(e)
        }), 500

@app.route('/api/book-demo', methods=['POST'])
def book_demo():
    """حجز عرض تجريبي"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'بيانات الطلب مفقودة'
            }), 400

        # التحقق من الحقول المطلوبة
        required_fields = ['company_name', 'full_name', 'email', 'phone']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'الحقول المطلوبة مفقودة: {", ".join(missing_fields)}'
            }), 400

        # حفظ بيانات طلب العرض في قاعدة البيانات
        logger.info(f"📞 طلب عرض تجريبي من: {data['company_name']} - {data['email']}")

        # إنشاء سجل في جدول demo_requests (إذا لم يكن موجوداً)
        cursor = get_db_connection().cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS demo_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    company_name VARCHAR(255) NOT NULL,
                    contact_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    employee_count VARCHAR(50),
                    industry VARCHAR(255),
                    interested_apps TEXT,
                    notes TEXT,
                    source VARCHAR(100) DEFAULT 'website',
                    status ENUM('pending', 'contacted', 'completed', 'cancelled') DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                INSERT INTO demo_requests
                (company_name, contact_name, email, phone, employee_count, industry, interested_apps, notes, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['company_name'],
                data['full_name'],
                data['email'],
                data['phone'],
                data.get('employee_count', ''),
                data.get('industry', ''),
                json.dumps(data.get('interested_apps', [])),
                data.get('notes', ''),
                data.get('source', 'book_demo_form')
            ))

            demo_id = cursor.lastrowid
            get_db_connection().commit()

            # محاكاة إرسال بريد إلكتروني للإشعار
            logger.info(f"📧 تم حفظ طلب العرض التجريبي رقم {demo_id}")

            return jsonify({
                'success': True,
                'message': 'تم إرسال طلب العرض التجريبي بنجاح. سيتصل بك فريقنا قريباً.',
                'demo_request_id': demo_id
            })

        finally:
            cursor.close()

    except mysql.connector.IntegrityError as e:
        logger.error(f"❌ خطأ في حفظ طلب العرض: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'البريد الإلكتروني مسجل مسبقاً'
        }), 400
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة طلب العرض: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في الخادم: {str(e)}'
        }), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """الحصول على إحصائيات النظام"""
    try:
        cursor = get_db_connection().cursor(dictionary=True)
        try:
            # عدد الحسابات التجريبية النشطة
            cursor.execute("""
                SELECT COUNT(*) as count FROM trial_customers
                WHERE status = 'active' AND expires_at > NOW()
            """)
            trial_users = cursor.fetchone()['count']

            # عدد المواقع التي تم إنشاؤها
            cursor.execute("""
                SELECT COUNT(*) as count FROM trial_customers
                WHERE frappe_site_created = 1
            """)
            sites_created = cursor.fetchone()['count']

            # عدد طلبات العروض التجريبية
            cursor.execute("""
                SELECT COUNT(*) as count FROM demo_requests
                WHERE status = 'pending'
            """)
            demo_requests = cursor.fetchone()['count']

            return jsonify({
                'success': True,
                'data': {
                    'trial_users': trial_users,
                    'sites_created': sites_created,
                    'demo_requests': demo_requests
                }
            })

        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في الخادم: {str(e)}'
        }), 500

@app.route('/api/apps', methods=['GET'])
def get_available_apps():
    """الحصول على قائمة التطبيقات المتاحة"""
    try:
        apps = [
            {
                'id': 'erpnext',
                'name': 'ERPNext',
                'description': 'نظام تخطيط الموارد المتكامل - إدارة الحسابات والمخزون والمبيعات',
                'icon': '📊',
                'features': ['المحاسبة', 'المخزون', 'المبيعات', 'المشتريات']
            },
            {
                'id': 'hrms',
                'name': 'HRMS',
                'description': 'نظام إدارة الموارد البشرية - إدارة الموظفين والرواتب والحضور',
                'icon': '👥',
                'features': ['إدارة الموظفين', 'الرواتب', 'الحضور', 'التقييمات']
            },
            {
                'id': 'crm',
                'name': 'CRM',
                'description': 'نظام إدارة علاقات العملاء - متابعة العملاء والمبيعات والتسويق',
                'icon': '🤝',
                'features': ['إدارة العملاء', 'المبيعات', 'التسويق', 'الدعم']
            },
            {
                'id': 'lms',
                'name': 'LMS',
                'description': 'نظام إدارة التعلم - إنشاء وإدارة الدورات التدريبية',
                'icon': '🎓',
                'features': ['الدورات', 'الاختبارات', 'الشهادات', 'التقارير']
            },
            {
                'id': 'website',
                'name': 'Website',
                'description': 'منشئ مواقع الويب - إنشاء موقع شركتك بسهولة',
                'icon': '🌐',
                'features': ['منشئ المواقع', 'التصميم', 'المحتوى', 'SEO']
            }
        ]

        return jsonify({
            'success': True,
            'apps': apps
        })

    except Exception as e:
        logger.error(f"❌ خطأ في جلب التطبيقات: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في الخادم: {str(e)}'
        }), 500

if __name__ == '__main__':
    logger.info("🚀 بدء تشغيل خادم SaaS Trial مع Frappe Press...")
    app.run(host='0.0.0.0', port=5000, debug=False)
