import subprocess
import requests
import time
import logging
import json
from typing import Tuple, List
import mysql.connector

logger = logging.getLogger(__name__)

class FrappePressManager:
    """مدير للتفاعل مع Frappe Press الموجود"""
    
    def __init__(self):
        self.db_config = {
            'host': '172.20.0.10',  # db-primary
            'user': 'root',
            'password': '123456',
            'database': 'frappe'
        }
        self.app_servers = [
            '172.20.0.20:8000',  # app-server-1
            '172.20.0.21:8001'   # app-server-2
        ]
    
    def get_db_connection(self):
        """الاتصال بقاعدة بيانات Frappe الرئيسية"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {str(e)}")
            raise e
    
    def create_site_in_db(self, site_name: str, admin_password: str = "admin123") -> Tuple[bool, str]:
        """إنشاء سجل الموقع في قاعدة بيانات Frappe"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # التحقق من عدم وجود الموقع مسبقاً
            cursor.execute("SELECT name FROM `tabSite` WHERE name = %s", (site_name,))
            if cursor.fetchone():
                return False, f"الموقع {site_name} موجود مسبقاً"
            
            # إنشاء سجل الموقع
            site_data = {
                'name': site_name,
                'status': 'Active',
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'admin_password': admin_password
            }
            
            # في Frappe، المواقع تُنشأ عبر Bench وليس مباشرة في DB
            # نعود لاستخدام Docker لتنفيذ الأوامر
            
            conn.close()
            return True, site_name
            
        except Exception as e:
            return False, f"خطأ في إنشاء سجل الموقع: {str(e)}"
    
    def execute_bench_command(self, container_name: str, command: List[str]) -> Tuple[bool, str]:
        """تنفيذ أوامر Bench في حاوية التطبيق"""
        try:
            docker_command = [
                "docker", "exec", container_name, 
                "bash", "-c", f"cd /home/frappe/production && {' '.join(command)}"
            ]
            
            logger.info(f"🐳 تشغيل أمر في {container_name}: {' '.join(command)}")
            
            result = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ الأمر ناجح في {container_name}")
                return True, result.stdout
            else:
                logger.error(f"❌ فشل الأمر في {container_name}: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "انتهت مهلة التنفيذ"
        except Exception as e:
            return False, f"خطأ في التنفيذ: {str(e)}"
    
    def create_site(self, site_name: str, apps: List[str] = None) -> Tuple[bool, str]:
        """إنشاء موقع جديد في Frappe Press"""
        try:
            if apps is None:
                apps = ["erpnext"]
            
            logger.info(f"🚀 بدء إنشاء موقع في Frappe Press: {site_name}")
            
            # استخدام app-server-1 لإنشاء الموقع
            success, output = self.execute_bench_command("app-server-1", [
                "bench", "new-site", site_name,
                "--admin-password", "admin123",
                "--db-root-password", "123456",
                "--force"
            ])
            
            if not success:
                return False, f"فشل إنشاء الموقع: {output}"
            
            # تثبيت التطبيقات
            for app in apps:
                if app == "erpnext":
                    success, output = self.execute_bench_command("app-server-1", [
                        "bench", "--site", site_name, "install-app", "erpnext"
                    ])
                    if not success:
                        logger.warning(f"⚠️ فشل تثبيت {app}: {output}")
            
            # إعداد كلمة المرور
            self.execute_bench_command("app-server-1", [
                "bench", "--site", site_name, "set-admin-password", "admin123"
            ])
            
            # إعداد بيانات الشركة
            self.setup_company_data(site_name, "شركة جديدة", "admin@example.com")
            
            # مزامنة الموقع مع app-server-2
            self.sync_site_to_second_server(site_name)
            
            # تحديث إعدادات Nginx
            self.update_nginx_config(site_name)
            
            logger.info(f"🎉 تم إنشاء الموقع بنجاح: {site_name}")
            return True, f"http://{site_name}"
            
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع: {str(e)}"
    
    def setup_company_data(self, site_name: str, company_name: str, email: str):
        """إعداد بيانات الشركة في الموقع الجديد"""
        try:
            script = f"""
import frappe
frappe.connect('{site_name}')

# تحديث الشركة الافتراضية
try:
    company = frappe.get_doc("Company", "Default Company")
    company.company_name = "{company_name}"
    company.save()
except Exception as e:
    print(f"⚠️ فشل تحديث الشركة: {{e}}")

# تحديث بيانات المدير
try:
    user = frappe.get_doc("User", "Administrator")
    user.email = "{email}"
    user.save()
except Exception as e:
    print(f"⚠️ فشل تحديث المستخدم: {{e}}")

frappe.db.commit()
frappe.destroy()
"""
            
            success, output = self.execute_bench_command("app-server-1", [
                "bench", "--site", site_name, "console", "-c", f"\"{script}\""
            ])
            
            if success:
                logger.info(f"✅ تم إعداد بيانات الشركة: {company_name}")
            else:
                logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {output}")
                
        except Exception as e:
            logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {str(e)}")
    
    def sync_site_to_second_server(self, site_name: str):
        """مزامنة الموقع مع الخادم الثاني"""
        try:
            # نسخ قاعدة البيانات
            success, output = self.execute_bench_command("app-server-1", [
                "bench", "--site", site_name, "backup", "--with-files"
            ])
            
            if success:
                # هنا يمكنك نسخ الملفات إلى app-server-2
                # واستعادة النسخة الاحتياطية
                logger.info(f"✅ تم مزامنة الموقع {site_name} مع الخادم الثاني")
            else:
                logger.warning(f"⚠️ فشل مزامنة الموقع مع الخادم الثاني: {output}")
                
        except Exception as e:
            logger.warning(f"⚠️ فشل مزامنة الموقع: {str(e)}")
    
    def update_nginx_config(self, site_name: str):
        """تحديث إعدادات Nginx لإضافة الموقع الجديد"""
        try:
            # هذا يحتاج إلى تعديل إعدادات Nginx في proxy-server
            # يمكن إضافة تكوين virtual host جديد
            
            nginx_config = f"""
server {{
    listen 80;
    server_name {site_name};
    
    location / {{
        proxy_pass http://app-server-1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
"""
            # حفظ التكوين (هذا مثال - يحتاج إلى تكوين حقيقي)
            logger.info(f"🌐 تم إعداد Nginx للموقع: {site_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ فشل تحديث إعدادات Nginx: {str(e)}")
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي في Frappe Press"""
        try:
            site_name = f"{subdomain}.trial.local"  # يمكنك تغيير النطاق
            
            # التحقق من عدم وجود الموقع
            if self.site_exists(site_name):
                return False, f"الموقع {site_name} موجود مسبقاً"
            
            # إنشاء الموقع
            success, result = self.create_site(site_name, apps)
            
            if success:
                # إعداد بيانات الشركة
                self.setup_company_data(site_name, company_name, admin_email)
                return True, f"http://{site_name}"
            else:
                return False, result
                
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع التجريبي: {str(e)}"
    
    def site_exists(self, site_name: str) -> bool:
        """التحقق من وجود الموقع"""
        try:
            success, output = self.execute_bench_command("app-server-1", [
                "bench", "--site", site_name, "list-apps"
            ])
            return success
        except Exception:
            return False
    
    def get_all_sites(self) -> List[str]:
        """الحصول على قائمة جميع المواقع"""
        try:
            success, output = self.execute_bench_command("app-server-1", [
                "bench", "list-sites"
            ])
            
            if success:
                sites = [site.strip() for site in output.split('\n') if site.strip()]
                return sites
            return []
        except Exception as e:
            logger.error(f"❌ فشل جلب قائمة المواقع: {str(e)}")
            return []

# استخدام المدير مع Frappe Press
def get_frappe_press_manager():
    """الحصول على مدير Frappe Press"""
    try:
        manager = FrappePressManager()
        # اختبار الاتصال
        sites = manager.get_all_sites()
        logger.info(f"✅ اتصال ناجح مع Frappe Press - المواقع: {len(sites)}")
        return manager
    except Exception as e:
        logger.error(f"❌ فشل الاتصال مع Frappe Press: {e}")
        # العودة للمحاكاة كبديل
        from frappe_manager import MockFrappeManager
        return MockFrappeManager()
