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
        ]
        
        self.db_config = {
            'host': '172.20.0.10',
            'user': 'root', 
            'password': '123456',
            'database': 'frappe'
        }
        self.session = requests.Session()
        self.session.timeout = 30
    
    def get_available_server(self):
        """العثور على خادم Frappe متاح"""
        for server in self.app_servers:
            try:
                test_url = f"http://{server['ip']}:{server['port']}/api/method/version"
                response = self.session.get(test_url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ وجد خادم نشط: {server['name']} - {server['ip']}:{server['port']}")
                    return server
            except Exception as e:
                logger.warning(f"⚠️ الخادم {server['name']} غير متاح: {e}")
        
        logger.error("❌ لا توجد خوادم Frappe متاحة")
        return None
    
    def call_frappe_api(self, server: dict, endpoint: str, method: str = 'GET', data: dict = None) -> Tuple[bool, dict]:
        """استدعاء واجهات Frappe API"""
        try:
            url = f"http://{server['ip']}:{server['port']}{endpoint}"
            
            logger.info(f"🌐 استدعاء Frappe API: {method} {url}")
            
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
                    "content": response.text[:500],  # أول 500 حرف فقط للتصحيح
                    "status_code": response.status_code
                }
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ استدعاء API ناجح: {endpoint}")
                return True, result
            else:
                error_msg = {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text[:500],
                    "endpoint": endpoint
                }
                logger.error(f"❌ فشل استدعاء API: {error_msg}")
                return False, error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = {"error": f"Request failed: {str(e)}", "server": server['name']}
            logger.error(f"❌ فشل طلب API: {error_msg}")
            return False, error_msg
        except json.JSONDecodeError as e:
            error_msg = {"error": f"JSON decode error: {str(e)}", "content": response.text[:500]}
            logger.error(f"❌ خطأ في فك JSON: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = {"error": str(e), "server": server['name']}
            logger.error(f"❌ خطأ غير متوقع: {error_msg}")
            return False, error_msg
    
    def create_site_via_api(self, site_name: str, apps: List[str] = None) -> Tuple[bool, str]:
        """إنشاء موقع عبر Frappe API"""
        try:
            if apps is None:
                apps = ["erpnext"]
            
            logger.info(f"🚀 محاولة إنشاء موقع حقيقي: {site_name}")
            
            # العثور على خادم متاح
            server = self.get_available_server()
            if not server:
                return False, "❌ لا توجد خوادم Frappe متاحة"
            
            logger.info(f"🎯 استخدام الخادم: {server['name']} لإنشاء الموقع")
            
            # بيانات إنشاء الموقع
            site_data = {
                "site_name": site_name,
                "apps": apps,
                "admin_password": "admin123",
                "install_apps": True,
                "db_name": site_name.replace('.', '_'),
                "db_password": "admin123",
                "db_type": "mariadb"
            }
            
            # استدعاء API إنشاء الموقع
            success, result = self.call_frappe_api(
                server, 
                "/api/method/frappe.utils.installer.create_site", 
                "POST", 
                site_data
            )
            
            if success:
                site_url = f"http://{site_name}"
                logger.info(f"✅ تم إنشاء موقع Frappe حقيقي: {site_url}")
                logger.info(f"   الاستجابة: {json.dumps(result, ensure_ascii=False)[:200]}...")
                return True, site_url
            else:
                logger.error(f"❌ فشل إنشاء الموقع: {result}")
                
                # محاولة بديلة باستخدام bench
                logger.info("🔄 محاولة استخدام طريقة بديلة...")
                alternative_success, alternative_result = self.create_site_alternative(site_name, apps, server)
                if alternative_success:
                    return True, alternative_result
                
                return False, f"فشل إنشاء الموقع: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الموقع: {str(e)}")
            return False, f"خطأ في إنشاء الموقع: {str(e)}"
    
    def create_site_alternative(self, site_name: str, apps: List[str], server: dict) -> Tuple[bool, str]:
        """طريقة بديلة لإنشاء الموقع"""
        try:
            logger.info(f"🔄 محاولة بديلة لإنشاء الموقع: {site_name}")
            
            # استخدام واجهة مختلفة أو طريقة بديلة
            site_data = {
                "name": site_name,
                "apps": apps,
                "admin_password": "admin123"
            }
            
            success, result = self.call_frappe_api(
                server,
                "/api/method/press.api.site.create",
                "POST",
                site_data
            )
            
            if success:
                site_url = f"http://{site_name}"
                logger.info(f"✅ تم إنشاء الموقع بالطريقة البديلة: {site_url}")
                return True, site_url
            else:
                logger.warning(f"⚠️ فشل الطريقة البديلة: {result}")
                return False, "فشل جميع طرق إنشاء الموقع"
                
        except Exception as e:
            logger.error(f"❌ خطأ في الطريقة البديلة: {str(e)}")
            return False, f"خطأ في الطريقة البديلة: {str(e)}"
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي"""
        try:
            site_name = f"{subdomain}.trial.local"
            
            logger.info(f"🎯 بدء إنشاء موقع تجريبي حقيقي: {site_name}")
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
                
                logger.info(f"🎉 تم إنشاء موقع Frappe حقيقي بنجاح: {site_url}")
                return True, site_url
            else:
                logger.error(f"❌ فشل إنشاء الموقع التجريبي: {site_url}")
                return False, site_url
                
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الموقع التجريبي: {str(e)}")
            return False, f"خطأ في إنشاء الموقع التجريبي: {str(e)}"
    
    def setup_company_data(self, site_name: str, company_name: str, email: str):
        """إعداد بيانات الشركة"""
        try:
            logger.info(f"🏢 إعداد بيانات الشركة: {company_name}")
            
            # العثور على خادم متاح
            server = self.get_available_server()
            if not server:
                logger.warning("⚠️ لا يوجد خادم متاح لإعداد بيانات الشركة")
                return
            
            # تحديث بيانات الشركة في Frappe
            company_data = {
                "company_name": company_name,
                "email": email,
                "abbr": company_name[:4].upper()
            }
            
            success, result = self.call_frappe_api(
                server,
                f"/api/method/frappe.client.set_value",
                "POST",
                {
                    "doctype": "Company",
                    "name": company_name,
                    "fieldname": "company_name",
                    "value": company_name
                }
            )
            
            if success:
                logger.info("✅ تم إعداد بيانات الشركة بنجاح")
            else:
                logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {result}")
            
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
            # العثور على خادم متاح
            server = self.get_available_server()
            if not server:
                logger.warning("⚠️ لا يوجد خادم متاح لجلب المواقع")
                return ["لا توجد خوادم متاحة"]
            
            # جلب المواقع من Frappe
            success, result = self.call_frappe_api(
                server,
                "/api/method/frappe.utils.installer.get_sites",
                "GET"
            )
            
            if success:
                sites = result.get("message", [])
                logger.info(f"📋 جلب {len(sites)} موقع من Frappe")
                return sites
            else:
                logger.warning(f"⚠️ فشل جلب المواقع: {result}")
                return ["فشل جلب المواقع"]
            
        except Exception as e:
            logger.error(f"❌ فشل جلب المواقع: {str(e)}")
            return [f"خطأ في جلب المواقع: {str(e)}"]

class MockFrappeManager:
    """مدير وهمي لاستخدامه عندما يكون Frappe غير متاح"""
    
    def __init__(self):
        logger.info("🔧 استخدام MockFrappeManager للاختبار - لن يتم إنشاء مواقع حقيقية!")
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي وهمي"""
        try:
            site_name = f"{subdomain}.trial.local"
            logger.info(f"🎯 [MOCK] إنشاء موقع تجريبي: {site_name}")
            logger.info(f"   الشركة: {company_name}")
            logger.info(f"   التطبيقات: {apps}")
            logger.info("   ⚠️ هذا موقع وهمي ولن يكون متاحاً فعلياً")
            
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
        
        # اختبار مفصل للاتصال بجميع الخوادم
        available_servers = []
        for server in manager.app_servers:
            try:
                test_url = f"http://{server['ip']}:{server['port']}/api/method/version"
                logger.info(f"🔍 اختبار اتصال بـ: {server['name']} - {test_url}")
                response = manager.session.get(test_url, timeout=5)
                
                if response.status_code == 200:
                    available_servers.append({
                        'server': server,
                        'status': 'connected',
                        'version': response.json().get('version', 'Unknown')
                    })
                    logger.info(f"✅ اتصال ناجح مع {server['name']}: {response.json().get('version', 'Unknown')}")
                else:
                    available_servers.append({
                        'server': server,
                        'status': f'failed_{response.status_code}',
                        'error': response.text[:100]
                    })
                    logger.warning(f"⚠️ {server['name']} غير متاح: HTTP {response.status_code}")
                    
            except Exception as e:
                available_servers.append({
                    'server': server,
                    'status': 'error',
                    'error': str(e)
                })
                logger.warning(f"❌ فشل الاتصال بـ {server['name']}: {e}")
        
        # إذا وجدنا خادم متاح، استخدم المدير الحقيقي
        if any(s['status'] == 'connected' for s in available_servers):
            logger.info(f"🎯 استخدام FrappeDirectManager مع {len([s for s in available_servers if s['status'] == 'connected'])} خوادم نشطة")
            return manager
        else:
            logger.error("🚨 جميع خوادم Frappe غير متاحة، استخدام المحاكاة")
            logger.error("   تفاصيل الخوادم:")
            for server_info in available_servers:
                logger.error(f"   - {server_info['server']['name']}: {server_info['status']} - {server_info.get('error', '')}")
            return MockFrappeManager()
            
    except Exception as e:
        logger.error(f"🚨 فشل تهيئة FrappeDirectManager: {e}")
        return MockFrappeManager()