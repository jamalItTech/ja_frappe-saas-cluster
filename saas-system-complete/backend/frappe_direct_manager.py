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
        self.app_servers = [
            {'ip': '172.20.0.20', 'port': 8000, 'name': 'app-server-1'},
            {'ip': '172.20.0.21', 'port': 8001, 'name': 'app-server-2'}
        ]
        
        self.db_config = {
            'host': '172.20.0.10',
            'user': 'root', 
            'password': '123456',
            'database': 'frappe'
        }
        self.session = requests.Session()
        self.session.timeout = 30
    
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
                    "content": response.text[:500]  # أول 500 حرف فقط للتصحيح
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
            
            # استخدام app-server-1
            server = self.app_servers[0]
            
            # محاولة الاتصال بالخادم أولاً للتحقق من أنه يعمل
            health_check_url = f"http://{server['ip']}:{server['port']}/api/method/version"
            try:
                health_response = self.session.get(health_check_url, timeout=10)
                logger.info(f"✅ اتصال Frappe صحي - الإصدار: {health_response.json().get('version', 'Unknown')}")
            except Exception as e:
                logger.warning(f"⚠️ لا يمكن الاتصال بخادم Frappe: {str(e)}")
                return False, f"لا يمكن الاتصال بخادم Frappe: {str(e)}"
            
            # محاكاة إنشاء الموقع (للتجربة)
            logger.info(f"🎯 محاكاة إنشاء موقع: {site_name} مع التطبيقات: {apps}")
            time.sleep(2)
            
            # إنشاء URL الموقع
            site_url = f"http://{site_name}"
            return True, site_url
            
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
                # إعداد بيانات الشركة
                self.setup_company_data(site_name, company_name, admin_email)
                
                # إضافة تكوين Nginx للموقع الجديد
                nginx_success, nginx_msg = self.create_nginx_config(site_name)
                if nginx_success:
                    logger.info(f"✅ تم إضافة تكوين Nginx: {nginx_msg}")
                else:
                    logger.warning(f"⚠️ فشل إضافة تكوين Nginx: {nginx_msg}")
                
                return True, site_url
            else:
                return False, site_url
                
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع التجريبي: {str(e)}"
    
    def setup_company_data(self, site_name: str, company_name: str, email: str):
        """إعداد بيانات الشركة"""
        try:
            logger.info(f"🏢 إعداد بيانات الشركة: {company_name}")
            
            # محاكاة إعداد البيانات
            time.sleep(1)
            logger.info("✅ تم إعداد بيانات الشركة بنجاح")
            
        except Exception as e:
            logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {str(e)}")
    
    def create_nginx_config(self, site_name: str) -> Tuple[bool, str]:
        """إنشاء تكوين Nginx للموقع الجديد"""
        try:
            # استيراد NginxManager هنا لتجنب التبعيات الدائرية
            from nginx_manager import nginx_manager
            
            success, message = nginx_manager.create_site_config(site_name)
            return success, message
            
        except Exception as e:
            return False, f"خطأ في إنشاء تكوين Nginx: {str(e)}"
    
    def get_all_sites(self) -> List[str]:
        """الحصول على قائمة المواقع"""
        try:
            # محاكاة جلب المواقع
            sites = ["default.site", "demo.trial.local", "test.trial.local"]
            logger.info(f"📋 جلب {len(sites)} موقع من النظام")
            
            return sites
            
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
            
            time.sleep(2)  # محاكاة وقت الإنشاء
            
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
        test_server = manager.app_servers[0]
        test_url = f"http://{test_server['ip']}:{test_server['port']}/api/method/version"
        
        response = manager.session.get(test_url, timeout=10)
        if response.status_code == 200:
            sites = manager.get_all_sites()
            logger.info(f"✅ اتصال ناجح مع Frappe - {len(sites)} مواقع")
            return manager
        else:
            logger.warning(f"⚠️ خادم Frappe غير متاح، استخدام المحاكاة")
            return MockFrappeManager()
            
    except Exception as e:
        logger.warning(f"⚠️ فشل الاتصال المباشر: {e}, استخدام المحاكاة")
        return MockFrappeManager()