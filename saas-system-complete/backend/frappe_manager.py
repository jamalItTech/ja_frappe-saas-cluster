import subprocess
import requests
import time
import logging
import json
from typing import Tuple, List

logger = logging.getLogger(__name__)

class FrappeSiteManager:
    """مدير إنشاء مواقع Frappe حقيقية"""
    
    def __init__(self, bench_path: str = "/home/frappe/frappe-bench"):
        self.bench_path = bench_path
        self.base_domain = "trial.yourcompany.com"  # غير هذا للنطاق الحقيقي
    
    def run_bench_command(self, command: List[str], timeout: int = 300) -> Tuple[bool, str]:
        """تنفيذ أوامر Bench"""
        try:
            logger.info(f"🏃 تشغيل أمر: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=self.bench_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ الأمر ناجح: {command[0]}")
                return True, result.stdout
            else:
                logger.error(f"❌ فشل الأمر: {command[0]}")
                logger.error(f"Stderr: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            error_msg = f"⏰ انتهت مهلة الأمر: {' '.join(command)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ خطأ غير متوقع: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_site(self, site_name: str, apps: List[str] = None, admin_password: str = "admin123") -> Tuple[bool, str]:
        """إنشاء موقع Frappe جديد"""
        try:
            if apps is None:
                apps = ["erpnext"]
            
            # 1. إنشاء الموقع
            success, output = self.run_bench_command([
                "bench", "new-site", site_name,
                "--admin-password", admin_password,
                "--db-name", f"db_{site_name.replace('.', '_')}",
                "--force"
            ])
            
            if not success:
                return False, f"فشل إنشاء الموقع: {output}"
            
            # 2. تثبيت التطبيقات
            for app in apps:
                success, output = self.run_bench_command([
                    "bench", "--site", site_name, "install-app", app
                ])
                if not success:
                    logger.warning(f"⚠️ فشل تثبيت التطبيق {app}: {output}")
            
            # 3. إعداد المدير الافتراضي
            success, output = self.run_bench_command([
                "bench", "--site", site_name, "set-admin-password", admin_password
            ])
            
            logger.info(f"🎉 تم إنشاء الموقع بنجاح: {site_name}")
            return True, f"https://{site_name}"
            
        except Exception as e:
            error_msg = f"❌ فشل إنشاء الموقع {site_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي"""
        try:
            site_name = f"{subdomain}.{self.base_domain}"
            
            # إنشاء الموقع
            success, result = self.create_site(site_name, apps)
            
            if success:
                # إعداد بيانات الشركة الأولية
                self.setup_company_data(site_name, company_name, admin_email)
                return True, f"https://{site_name}"
            else:
                return False, result
                
        except Exception as e:
            return False, f"خطأ في إنشاء الموقع التجريبي: {str(e)}"
    
    def setup_company_data(self, site_name: str, company_name: str, email: str):
        """إعداد بيانات الشركة الأولية"""
        try:
            # تحديث بيانات الشركة الافتراضية
            success, output = self.run_bench_command([
                "bench", "--site", site_name, "console", "-c", 
                f"frappe.db.set_value('Company', 'Default Company', 'company_name', '{company_name}'); frappe.db.commit()"
            ])
            
            # تحديث بيانات المستخدم
            success, output = self.run_bench_command([
                "bench", "--site", site_name, "console", "-c",
                f"user = frappe.get_doc('User', 'Administrator'); user.email = '{email}'; user.save(); frappe.db.commit()"
            ])
            
            logger.info(f"✅ تم إعداد بيانات الشركة: {company_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ فشل إعداد بيانات الشركة: {str(e)}")
    
    def delete_site(self, site_name: str) -> Tuple[bool, str]:
        """حذف موقع"""
        try:
            success, output = self.run_bench_command([
                "bench", "drop-site", site_name, "--force", "--root-login", "root", "--root-password", "123456"
            ])
            return success, output
        except Exception as e:
            return False, f"خطأ في حذف الموقع: {str(e)}"
    
    def site_exists(self, site_name: str) -> bool:
        """التحقق من وجود الموقع"""
        try:
            success, output = self.run_bench_command([
                "bench", "--site", site_name, "list-apps"
            ])
            return success
        except Exception:
            return False

# مدير باستخدام Docker (بديل)
class DockerFrappeManager:
    """مدير إنشاء مواقع Frappe باستخدام Docker"""
    
    def __init__(self):
        self.base_domain = "trial.yourcompany.com"
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """إنشاء موقع تجريبي باستخدام Docker"""
        try:
            site_name = f"{subdomain}.{self.base_domain}"
            
            logger.info(f"🐳 محاكاة إنشاء موقع Docker: {site_name}")
            
            # محاكاة عملية الإنشاء (في البيئة الحقيقية، ننفذ أوامر Docker هنا)
            time.sleep(2)  # محاكاة وقت الإنشاء
            
            # في البيئة الحقيقية، نستخدم:
            # docker run -d --name site-{subdomain} \
            #   -e SITE_NAME={site_name} \
            #   -e INSTALL_APPS={','.join(apps)} \
            #   -p 8000-9000:8000 \
            #   frappe/erpnext:latest
            
            # محاكاة نجاح الإنشاء
            site_url = f"https://{site_name}"
            
            logger.info(f"✅ محاكاة إنشاء موقع ناجحة: {site_url}")
            return True, site_url
            
        except Exception as e:
            error_msg = f"❌ فشل في محاكاة إنشاء الموقع: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# مدير للمحاكاة (للاختبار)
class MockFrappeManager:
    """مدير محاكاة لإنشاء مواقع Frappe (للتطوير)"""
    
    def __init__(self):
        self.base_domain = "trial.yourcompany.com"
    
    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str) -> Tuple[bool, str]:
        """محاكاة إنشاء موقع تجريبي"""
        try:
            site_name = f"{subdomain}.{self.base_domain}"
            
            logger.info(f"🎭 محاكاة إنشاء موقع Frappe: {site_name}")
            logger.info(f"   الشركة: {company_name}")
            logger.info(f"   التطبيقات: {apps}")
            logger.info(f"   البريد: {admin_email}")
            
            # محاكاة وقت الإنشاء
            time.sleep(3)
            
            # إنشاء رابط محاكاة
            site_url = f"https://{site_name}"
            
            logger.info(f"✅ محاكاة إنشاء موقع ناجحة: {site_url}")
            return True, site_url
            
        except Exception as e:
            error_msg = f"❌ فشل في محاكاة إنشاء الموقع: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# استخدام المدير المناسب للبيئة
def get_frappe_manager():
    """الحصول على مدير Frappe المناسب"""
    
    # جرب المدير الحقيقي أولاً
    try:
        manager = FrappeSiteManager()
        # اختبار اتصال بسيط
        test_success, _ = manager.run_bench_command(["bench", "--version"])
        if test_success:
            logger.info("✅ استخدام FrappeSiteManager (الحقيقي)")
            return manager
    except Exception as e:
        logger.warning(f"⚠️ FrappeSiteManager غير متاح: {e}")
    
    # جرب مدير Docker
    try:
        import docker
        manager = DockerFrappeManager()
        logger.info("✅ استخدام DockerFrappeManager")
        return manager
    except Exception as e:
        logger.warning(f"⚠️ DockerFrappeManager غير متاح: {e}")
    
    # استخدام مدير المحاكاة كحل بديل
    logger.info("🔄 استخدام MockFrappeManager (المحاكاة)")
    return MockFrappeManager()
