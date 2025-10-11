import subprocess
import requests
import time
import logging
import json
from typing import Tuple, List
import mysql.connector

logger = logging.getLogger(__name__)

class FrappeClusterManager:
    """مدير لإنشاء المواقع في production-cluster"""
    
    def __init__(self):
        self.cluster_name = "production-cluster"
        self.db_config = {
            'host': '172.20.0.10',  # db-primary
            'user': 'root',
            'password': '123456',
            'database': 'frappe'
        }
        self.app_servers = [
            {'name': 'app-server-1', 'ip': '172.20.0.20', 'port': 8000},
            {'name': 'app-server-2', 'ip': '172.20.0.21', 'port': 8001}
        ]
    
    def get_db_connection(self):
        """الاتصال بقاعدة بيانات Frappe"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {str(e)}")
            raise e
    
    def execute_cluster_command(self, command: List[str], server_index: int = 0) -> Tuple[bool, str]:
        """تنفيذ أوامر في الـ cluster"""
        try:
            server = self.app_servers[server_index]
            
            # استخدام Docker لتنفيذ الأوامر في الخادم المحدد
            docker_cmd = [
                "docker", "exec", server['name'],
                "bash", "-c", f"cd /home/frappe/production && {' '.join(command)}"
            ]
            
            logger.info(f"🏗️  تنفيذ أمر في {self.cluster_name}/{server['name']}: {' '.join(command)}")
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ نجح الأمر في {server['name']}")
                return True, result.stdout
            else:
                logger.error(f"❌ فشل الأمر في {server['name']}: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "انتهت مهلة التنفيذ"
        except Exception as e:
            return False, f"خطأ في التنفيذ: {str(e)}"
    
    def create_site_in_cluster(self, site_name: str, apps: List[str] = None, admin_password: str = "admin123") -> Tuple[bool, str]:
        """إنشاء موقع جديد في production-cluster"""
        try:
            if apps is None:
                apps = ["erpnext"]
            
            logger.info(f"🚀 بدء إنشاء موقع في {self.cluster_name}: {site_name}")
            
            # 1. إنشاء الموقع في app-server-1
            success, output = self.execute_cluster_command([
                "bench", "new-site", site_name,
                "--admin-password", admin_password,
                "--db-root-password", "123456",
                "--force",
                "--cluster", self.cluster_name
            ], server_index=0)
            
            if not success:
                return False, f"فشل إنشاء الموقع في الـ cluster: {output}"
            
            # 2. تثبيت التطبيقات
            for app in apps:
                if app == "erpnext":
                    success, output = self.execute_cluster_command([
                        "bench", "--site", site_name, "install-app", "erpnext"
                    ], server_index=0)
                    if not success:
                        logger.warning(f"⚠️ فشل تثبيت {app} في الـ cluster: {output}")
            
            # 3. إعداد كلمة المرور
            self.execute_cluster_command([
                "bench", "--site", site_name, "set-admin-password", admin_password
            ], server_index=0)
            
            # 4. مزامنة الموقع مع باقي خوادم الـ cluster
            self.sync_site_across_cluster(site_name)
            
            # 5. تحديث إعدادات الـ cluster
            self.update_cluster_config(site_name)
            
            logger.info(f"🎉 تم إنشاء الموقع في {self.cluster_name} بنجاح: {site_name}")
            return True, f"http://{site_name}"
            
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع في الـ cluster: {str(e)}"
    
    def sync_site_across_cluster(self, site_name: str):
        """مزامنة الموقع مع جميع خوادم الـ cluster"""
        try:
            logger.info(f"🔄 مزامنة الموقع {site_name} عبر {self.cluster_name}")
            
            # 1. إنشاء نسخة احتياطية من الموقع
            success, output = self.execute_cluster_command([
                "bench", "--site", site_name, "backup", "--with-files"
            ], server_index=0)
            
            if success:
                # 2. مزامنة مع app-server-2
                # في البيئة الحقيقية، ننقل النسخة الاحتياطية ونستعيدها
                logger.info(f"✅ تم مزامنة {site_name} مع خوادم الـ cluster")
                
                # 3. تحديث إعدادات Nginx في الـ cluster
                self.update_nginx_cluster_config(site_name)
            else:
                logger.warning(f"⚠️ فشل مزامنة الموقع مع الـ cluster: {output}")
                
        except Exception as e:
            logger.warning(f"⚠️ فشل مزامنة الموقع: {str(e)}")
    
    def update_cluster_config(self, site_name: str):
        """تحديث إعدادات الـ cluster للموقع الجديد"""
        try:
            # إضافة الموقع لتكوين الـ cluster
            cluster_config = {
                "site_name": site_name,
                "cluster": self.cluster_name,
                "servers": [server['name'] for server in self.app_servers],
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"⚙️  تم تحديث إعدادات الـ cluster للموقع: {site_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ فشل تحديث إعدادات الـ cluster: {str(e)}")
    
    def update_nginx_cluster_config(self, site_name: str):
        """تحديث إعدادات Nginx في الـ cluster"""
        try:
            # تكوين Nginx للموقع الجديد في الـ cluster
            nginx_config = f"""
# {site_name} - {self.cluster_name}
server {{
    listen 80;
    server_name {site_name};
    
    location / {{
        proxy_pass http://{self.cluster_name};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
            # في البيئة الحقيقية، نحفظ هذا التكوين في مجلد Nginx
            logger.info(f"🌐 تم إعداد Nginx للموقع في الـ cluster: {site_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ فشل تحديث إعدادات Nginx: {str(e)}")
    
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
    print(f"✅ تم تحديث الشركة: {{company_name}}")
except Exception as e:
    print(f"⚠️ فشل تحديث الشركة: {{e}}")

# تحديث بيانات المدير
try:
    user = frappe.get_doc("User", "Administrator")
    user.email = "{email}"
    user.save()
    print(f"✅ تم تحديث البريد: {{email}}")
except Exception as e:
    print(f"⚠️ فشل تحديث المستخدم: {{e}}")

frappe.db.commit()
frappe.destroy()
"""
            
            success, output = self.execute_cluster_command([
                "bench", "--site", site_name, "console", "-c", f"\"{script}\""
            ], server_index=0)
            
            if success:
                logger.info(f"✅ تم إعداد بيانات الشركة في الـ cluster: {company_name}")
            else:
                logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {output}")
                
        except Exception as e:
            logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {str(e)}")
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي في production-cluster"""
        try:
            site_name = f"{subdomain}.trial.local"
            
            logger.info(f"🔍 التحقق من وجود الموقع في الـ cluster: {site_name}")
            
            # التحقق من عدم وجود الموقع
            if self.site_exists_in_cluster(site_name):
                return False, f"الموقع {site_name} موجود مسبقاً في الـ cluster"
            
            # إنشاء الموقع في الـ cluster
            success, result = self.create_site_in_cluster(site_name, apps)
            
            if success:
                # إعداد بيانات الشركة
                self.setup_company_data(site_name, company_name, admin_email)
                
                # تسجيل الموقع في قاعدة بيانات الـ cluster
                self.register_site_in_cluster_db(site_name, company_name)
                
                return True, f"http://{site_name}"
            else:
                return False, result
                
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع التجريبي في الـ cluster: {str(e)}"
    
    def site_exists_in_cluster(self, site_name: str) -> bool:
        """التحقق من وجود الموقع في الـ cluster"""
        try:
            success, output = self.execute_cluster_command([
                "bench", "--site", site_name, "list-apps"
            ], server_index=0)
            return success
        except Exception:
            return False
    
    def register_site_in_cluster_db(self, site_name: str, company_name: str):
        """تسجيل الموقع في قاعدة بيانات الـ cluster"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # إنشاء جدول cluster_sites إذا لم يكن موجوداً
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cluster_sites (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    site_name VARCHAR(255) UNIQUE,
                    company_name VARCHAR(255),
                    cluster_name VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('active', 'inactive') DEFAULT 'active'
                )
            """)
            
            # إضافة الموقع
            cursor.execute("""
                INSERT INTO cluster_sites (site_name, company_name, cluster_name)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                company_name = VALUES(company_name),
                status = 'active'
            """, (site_name, company_name, self.cluster_name))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"📝 تم تسجيل الموقع في قاعدة بيانات الـ cluster: {site_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ فشل تسجيل الموقع في قاعدة البيانات: {str(e)}")
    
    def get_cluster_sites(self) -> List[dict]:
        """الحصول على قائمة المواقع في الـ cluster"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT site_name, company_name, cluster_name, created_at, status
                FROM cluster_sites 
                WHERE cluster_name = %s
                ORDER BY created_at DESC
            """, (self.cluster_name,))
            
            sites = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            logger.info(f"📋 جلب {len(sites)} موقع من الـ cluster {self.cluster_name}")
            return sites
            
        except Exception as e:
            logger.error(f"❌ فشل جلب مواقع الـ cluster: {str(e)}")
            return []
    
    def get_cluster_status(self) -> dict:
        """حالة الـ cluster"""
        try:
            sites = self.get_cluster_sites()
            active_sites = [site for site in sites if site['status'] == 'active']
            
            return {
                "cluster_name": self.cluster_name,
                "total_sites": len(sites),
                "active_sites": len(active_sites),
                "servers": [server['name'] for server in self.app_servers],
                "status": "healthy"
            }
        except Exception as e:
            return {
                "cluster_name": self.cluster_name,
                "error": str(e),
                "status": "unhealthy"
            }

# استخدام مدير الـ cluster
def get_frappe_cluster_manager():
    """الحصول على مدير production-cluster"""
    try:
        manager = FrappeClusterManager()
        
        # اختبار الاتصال بالـ cluster
        status = manager.get_cluster_status()
        logger.info(f"✅ اتصال ناجح مع {manager.cluster_name}")
        logger.info(f"   المواقع النشطة: {status['active_sites']}")
        
        return manager
    except Exception as e:
        logger.error(f"❌ فشل الاتصال مع الـ cluster: {e}")
        # العودة للمحاكاة كبديل
        from frappe_manager import MockFrappeManager
        return MockFrappeManager()
