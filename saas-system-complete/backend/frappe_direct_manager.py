import os
import requests
import time
import logging
import json
from typing import Tuple, List
import mysql.connector

logger = logging.getLogger(__name__)

class FrappeDirectManager:
    """مدير للاتصال المباشر مع حاويات Frappe"""

    def __init__(self):
        # استخدام عناوين IP الصحيحة من شبكة frappe-light-net بناًء على docker-compose.yml
        self.app_servers = [
            {'ip': '172.25.3.10', 'port': 8000, 'name': 'frappe-light-app-1'},  # frappe-app-1 من docker-compose
        ]

        # إعدادات قاعدة بيانات Frappe
        self.db_config = {
            'host': '172.25.0.10',  # frappe-db من docker-compose
            'port': int(os.getenv('DB_PORT', '3306')),  # البورت من المتغير البيئي
            'user': 'root',
            'password': os.getenv('MYSQL_ROOT_PASSWORD', 'light_frappe_password_2025'),  # كلمة المرور من متغير البيئة
            'database': 'frappe'
        }

        # إعدادات قاعدة بيانات SaaS
        self.saas_db_config = {
            'host': '172.25.0.100',  # saas-database من docker-compose
            'port': 3306,  # البورت الافتراضي لـ MariaDB
            'user': os.getenv('SAAS_DB_USER', 'saas_user'),
            'password': os.getenv('SAAS_DB_PASSWORD', 'saas_db_pass_2025'),  # كلمة المرور من متغير البيئة
            'database': os.getenv('SAAS_DB_NAME', 'saas_trials_light')
        }

        # إعدادات Redis
        self.redis_config = {
            'host': '172.25.0.11',  # frappe-redis من docker-compose
            'port': 6379,  # البورت الافتراضي لـ Redis
            'password': os.getenv('REDIS_PASSWORD'),  # كلمة المرور من متغير البيئة
            'db': 0
        }

        self.session = requests.Session()
        self.session.timeout = 30
    
    def test_frappe_connection(self) -> bool:
        """اختبار الاتصال بخادم Frappe"""
        try:
            server = self.app_servers[0]
            test_url = f"http://{server['ip']}:{server['port']}/api/method/version"
            
            logger.info(f"🔧 اختبار الاتصال بـ Frappe: {test_url}")
            
            response = self.session.get(test_url, timeout=10)
            
            if response.status_code == 200:
                version_info = response.json()
                logger.info(f"✅ اتصال Frappe ناجح - الإصدار: {version_info.get('version', 'Unknown')}")
                return True
            else:
                logger.warning(f"⚠️ خادم Frappe متاح ولكن الاستجابة: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"❌ لا يمكن الاتصال بخادم Frappe: {str(e)}")
            return False
    
    def test_database_connection(self, db_type='frappe') -> bool:
        """اختبار الاتصال بقاعدة البيانات"""
        try:
            if db_type == 'frappe':
                config = self.db_config
                db_name = 'Frappe'
            else:
                config = self.saas_db_config
                db_name = 'SaaS'
            
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            logger.info(f"✅ اتصال {db_name} Database ناجح")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ {db_name} Database: {str(e)}")
            return False
    
    def call_frappe_api(self, server: dict, endpoint: str, method: str = 'GET', data: dict = None) -> Tuple[bool, dict]:
        """استدعاء واجهات Frappe API"""
        try:
            url = f"http://{server['ip']}:{server['port']}{endpoint}"
            
            logger.info(f"🌐 استدعاء API: {method} {url}")
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            else:
                return False, {"error": f"Method {method} not supported"}
            
            # التحقق من أن الاستجابة هي JSON
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                return False, {
                    "error": f"Expected JSON but got {content_type}",
                    "content": response.text[:500]
                }
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text[:500]
                }
                
        except requests.exceptions.RequestException as e:
            return False, {"error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError as e:
            return False, {"error": f"JSON decode error: {str(e)}", "content": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)}
    
    def create_site_via_api(self, site_name: str, apps: List[str] = None) -> Tuple[bool, str]:
        """إنشاء موقع عبر Frappe API"""
        try:
            if apps is None:
                apps = ["erpnext"]
            
            logger.info(f"🚀 إنشاء موقع عبر API: {site_name}")
            
            server = self.app_servers[0]
            
            # اختبار الاتصال أولاً
            if not self.test_frappe_connection():
                return False, "خادم Frappe غير متاح"
            
            # محاولة إنشاء الموقع باستخدام bench command عبر Docker exec
            try:
                # استخدام Docker exec لتنفيذ أمر bench داخل الحاوية
                import subprocess
                
                docker_cmd = [
                    "docker", "exec", "frappe-light-app-1",
                    "bash", "-c", 
                    f"cd /home/frappe/frappe-bench && bench new-site {site_name} "
                    f"--mariadb-root-password light_frappe_password_2025 "
                    f"--admin-password admin123 --force"
                ]
                
                logger.info(f"🔧 تنفيذ أمر Bench: {' '.join(docker_cmd)}")
                
                result = subprocess.run(
                    docker_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    site_url = f"http://{site_name}"
                    logger.info(f"✅ تم إنشاء الموقع بنجاح: {site_url}")
                    
                    # إعداد الموقع الافتراضي
                    subprocess.run([
                        "docker", "exec", "frappe-light-app-1",
                        "bash", "-c",
                        f"cd /home/frappe/frappe-bench && bench use {site_name}"
                    ], timeout=30)
                    
                    return True, site_url
                else:
                    error_msg = result.stderr or result.stdout
                    logger.error(f"❌ فشل إنشاء الموقع: {error_msg}")
                    return False, f"فشل إنشاء الموقع: {error_msg}"
                    
            except subprocess.TimeoutExpired:
                return False, "انتهت مهلة إنشاء الموقع"
            except Exception as e:
                return False, f"خطأ في تنفيذ الأمر: {str(e)}"
            
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع عبر API: {str(e)}"
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي"""
        try:
            site_name = f"{subdomain}.trial.local"
            
            logger.info(f"🎯 إنشاء موقع تجريبي: {site_name}")
            logger.info(f"   الشركة: {company_name}")
            logger.info(f"   التطبيقات: {apps}")
            logger.info(f"   البريد: {admin_email}")
            
            # إنشاء الموقع
            success, site_url = self.create_site_via_api(site_name, apps)
            
            if success:
                logger.info(f"✅ تم إنشاء الموقع التجريبي: {site_url}")
                return True, site_url
            else:
                return False, site_url
                
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع التجريبي: {str(e)}"
    
    def get_all_sites(self) -> List[str]:
        """الحصول على قائمة المواقع"""
        try:
            # استخدام Docker exec للحصول على قائمة المواقع
            import subprocess
            
            docker_cmd = [
                "docker", "exec", "frappe-light-app-1",
                "bash", "-c", 
                "cd /home/frappe/frappe-bench && ls sites/ 2>/dev/null | grep -v __pycache__ || echo ''"
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                sites = [site.strip() for site in result.stdout.splitlines() if site.strip()]
                logger.info(f"📋 جلب {len(sites)} موقع من Frappe")
                return sites
            else:
                logger.warning("⚠️ لا توجد مواقع أو فشل في الجلب")
                return []
            
        except Exception as e:
            logger.error(f"❌ فشل جلب المواقع: {str(e)}")
            return []

class MockFrappeManager:
    """مدير وهمي لاستخدامه عندما يكون Frappe غير متاح"""
    
    def __init__(self):
        logger.info("🔧 استخدام MockFrappeManager للاختبار")
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي وهمي"""
        try:
            site_name = f"{subdomain}.trial.local"
            logger.info(f"🎯 [MOCK] إنشاء موقع تجريبي: {site_name}")
            logger.info(f"   الشركة: {company_name}")
            logger.info(f"   التطبيقات: {apps}")
            
            time.sleep(2)
            
            site_url = f"http://{site_name}"
            logger.info(f"✅ [MOCK] تم إنشاء الموقع: {site_url}")
            
            return True, site_url
            
        except Exception as e:
            return False, f"خطأ في المحاكاة: {str(e)}"
    
    def get_all_sites(self) -> List[str]:
        """الحصول على قائمة مواقع وهمية"""
        return ["mock1.trial.local", "mock2.trial.local", "mock3.trial.local"]

def get_frappe_direct_manager():
    """الحصول على مدير الاتصال المباشر"""
    try:
        manager = FrappeDirectManager()
        
        # اختبار الاتصال بخادم Frappe
        if manager.test_frappe_connection():
            # اختبار الاتصال بقاعدة البيانات
            manager.test_database_connection('frappe')
            manager.test_database_connection('saas')
            
            sites = manager.get_all_sites()
            logger.info(f"✅ اتصال ناجح مع Frappe - {len(sites)} مواقع")
            return manager
        else:
            logger.warning("⚠️ خادم Frappe غير متاح، استخدام المحاكاة")
            return MockFrappeManager()
            
    except Exception as e:
        logger.warning(f"⚠️ فشل الاتصال المباشر: {e}, استخدام المحاكاة")
        return MockFrappeManager()
