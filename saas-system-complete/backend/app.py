from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import json
import random
import string
import logging
import time
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

# إعدادات قاعدة البيانات
DB_CONFIG = {
    'host': '172.20.0.102',
    'user': 'root',
    'password': '123456',
    'database': 'saas_trialsv1',
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
            
            cursor.execute("CREATE DATABASE IF NOT EXISTS saas_trialsv1")
            cursor.execute("USE saas_trialsv1")
            
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
                trial_days INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                status ENUM('active', 'expired', 'converted') DEFAULT 'active',
                frappe_site_created BOOLEAN DEFAULT FALSE
            )
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
    try:
        # اختبار اتصال قاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        
        # اختبار اتصال Frappe Press
        sites = trial_manager.frappe_manager.get_all_sites()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '✅ النظام يعمل بشكل صحيح',
            'database': '✅ متصل',
            'frappe_press': f'✅ متصل ({len(sites)} مواقع)',
            'frappe_manager': type(trial_manager.frappe_manager).__name__,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
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
    try:
        data = request.json
        logger.info(f"📥 استلام طلب إنشاء حساب لـ: {data.get('company_name')}")
        
        success, result = trial_manager.create_trial_account(data)
        
        execution_time = time.time() - start_time
        logger.info(f"⏱️ وقت تنفيذ الطلب: {execution_time:.2f} ثانية")
        
        if success:
            return jsonify({
                'success': True,
                'site_url': result,
                'message': '🎉 تم إنشاء موقعك التجريبي بنجاح!',
                'type': 'frappe_press_site',
                'execution_time': f"{execution_time:.2f} ثانية"
            })
        else:
            return jsonify({
                'success': False,
                'message': result,
                'type': 'error',
                'execution_time': f"{execution_time:.2f} ثانية"
            }), 400
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ خطأ في API: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في الخادم: {str(e)}',
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
        # اختبار الاتصال المباشر
        test_url = "http://172.20.0.20:8000/api/method/version"
        
        response = requests.get(test_url, timeout=10)
        
        return jsonify({
            'success': True,
            'frappe_status': 'connected' if response.status_code == 200 else 'failed',
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', 'unknown'),
            'response_preview': response.text[:200] if response.text else 'empty'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'frappe_status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("🚀 بدء تشغيل خادم SaaS Trial مع Frappe Press...")
    app.run(host='0.0.0.0', port=5000, debug=False)