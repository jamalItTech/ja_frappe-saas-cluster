import requests
import time
import logging
import json
import subprocess
from typing import Tuple, List, Dict
import mysql.connector
import os

logger = logging.getLogger(__name__)

class RealFrappeManager:
    """مدير فعلي إجباري لإنشاء مواقع Frappe حقيقية"""
    
    def __init__(self):
        self.bench_path = "/home/frappe/production"
        self.sites_path = "/home/frappe/production/sites"
        
        logger.info(f"🔧 [REAL] تهيئة RealFrappeManager الإجباري")
        logger.info(f"📁 المسار: {self.bench_path}")
        logger.info(f"📁 مواقع: {self.sites_path}")
        
        # التحقق الفوري من البيئة
        self._debug_environment()
    
    def _debug_environment(self):
        """تصحيح بيئة النظام"""
        logger.info("🔍 فحص بيئة النظام...")
        
        # التحقق من المسارات
        paths_to_check = [
            self.bench_path,
            self.sites_path,
            "/usr/local/bin/bench",
            "/home/frappe/.local/bin/bench"
        ]
        
        for path in paths_to_check:
            exists = os.path.exists(path)
            logger.info(f"   {'✅' if exists else '❌'} {path} - {'موجود' if exists else 'غير موجود'}")
        
        # التحقق من أوامر النظام
        commands_to_check = ["which bench", "bench --version", "python --version"]
        for cmd in commands_to_check:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                status = "✅" if result.returncode == 0 else "❌"
                logger.info(f"   {status} {cmd} - {result.returncode}")
                if result.stdout:
                    logger.info(f"      stdout: {result.stdout.strip()}")
                if result.stderr:
                    logger.info(f"      stderr: {result.stderr.strip()}")
            except Exception as e:
                logger.info(f"   ❌ {cmd} - خطأ: {str(e)}")

    def execute_bench_command(self, command: List[str], site: str = None) -> Tuple[bool, str]:
        """تنفيذ أوامر bench مع تتبع تفصيلي"""
        try:
            # بناء الأمر
            if site:
                full_command = ["bench", "--site", site] + command
            else:
                full_command = ["bench"] + command
            
            cmd_str = ' '.join(full_command)
            logger.info(f"🔧 [REAL] تنفيذ أمر: {cmd_str}")
            logger.info(f"📁 المجلد الحالي: {self.bench_path}")
            
            # تنفيذ الأمر مع تسجيل تفصيلي
            start_time = time.time()
            result = subprocess.run(
                full_command,
                cwd=self.bench_path,
                capture_output=True,
                text=True,
                timeout=300,
                env=os.environ.copy()
            )
            execution_time = time.time() - start_time
            
            # تسجيل النتيجة بالتفصيل
            logger.info(f"⏱️ وقت التنفيذ: {execution_time:.2f} ثانية")
            logger.info(f"📤 كود الخروج: {result.returncode}")
            
            if result.stdout:
                logger.info(f"📄 stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.info(f"📄 stderr: {result.stderr.strip()}")
            
            if result.returncode == 0:
                logger.info(f"✅ [REAL] أمر ناجح")
                return True, result.stdout
            else:
                logger.error(f"❌ [REAL] فشل الأمر: كود {result.returncode}")
                return False, result.stderr if result.stderr else result.stdout
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ [REAL] انتهت مهلة تنفيذ الأمر (300 ثانية)")
            return False, "انتهت مهلة تنفيذ الأمر"
        except Exception as e:
            logger.error(f"💥 [REAL] خطأ في التنفيذ: {str(e)}")
            return False, f"خطأ في التنفيذ: {str(e)}"

    def create_trial_site(self, subdomain: str, company_name: str, apps: List[str], admin_email: str, admin_password: str = "admin123") -> Tuple[bool, str]:
        """إنشاء موقع تجريبي فعلي مع تتبع كامل"""
        try:
            site_name = f"{subdomain}.trial.local"
            
            logger.info(f"🚀 [REAL] بدء إنشاء موقع فعلي: {site_name}")
            logger.info(f"   الشركة: {company_name}")
            logger.info(f"   التطبيقات: {apps}")
            logger.info(f"   البريد: {admin_email}")
            
            # 1. التحقق من bench أولاً
            logger.info("🔍 المرحلة 1: التحقق من نظام bench...")
            bench_success, bench_output = self.execute_bench_command(["--version"])
            if not bench_success:
                logger.error(f"❌ [REAL] نظام bench غير متاح")
                return False, f"نظام bench غير متاح: {bench_output}"
            
            logger.info("✅ [REAL] نظام bench جاهز")
            
            # 2. التحقق من المواقع الحالية
            logger.info("🔍 المرحلة 2: التحقق من المواقع الحالية...")
            current_sites = self.get_all_sites()
            logger.info(f"📋 المواقع الحالية: {current_sites}")
            
            if site_name in current_sites:
                logger.warning(f"⚠️ [REAL] الموقع موجود مسبقاً: {site_name}")
                return True, f"http://{site_name}"
            
            # 3. إنشاء الموقع
            logger.info("🔍 المرحلة 3: إنشاء الموقع...")
            create_cmd = [
                "new-site", site_name,
                "--admin-password", admin_password,
                "--db-root-password", "123456",
                "--force"
            ]
            
            success, message = self.execute_bench_command(create_cmd)
            if not success:
                logger.error(f"❌ [REAL] فشل إنشاء الموقع: {message}")
                return False, f"فشل إنشاء الموقع: {message}"
            
            logger.info(f"✅ [REAL] تم إنشاء الموقع الأساسي: {site_name}")
            
            # 4. تثبيت التطبيقات
            logger.info("🔍 المرحلة 4: تثبيت التطبيقات...")
            apps_to_install = apps if apps else ["erpnext"]
            installed_apps = []
            
            for app in apps_to_install:
                logger.info(f"📦 تثبيت التطبيق: {app}")
                app_success, app_message = self.execute_bench_command(["install-app", app], site_name)
                if app_success:
                    logger.info(f"✅ تم تثبيت {app}")
                    installed_apps.append(app)
                else:
                    logger.warning(f"⚠️ فشل تثبيت {app}: {app_message}")
            
            # 5. تمكين المجدول
            logger.info("🔍 المرحلة 5: تمكين المجدول...")
            self.execute_bench_command(["enable-scheduler"], site_name)
            
            # 6. التحقق النهائي
            logger.info("🔍 المرحلة 6: التحقق النهائي...")
            final_sites = self.get_all_sites()
            site_created = site_name in final_sites
            
            if site_created:
                # إنشاء بيانات الشركة
                self._create_site_metadata(site_name, company_name, admin_email, installed_apps)
                
                logger.info(f"🎉 [REAL] تم إنشاء الموقع الفعلي بنجاح: {site_name}")
                logger.info(f"📊 التطبيقات المثبتة: {installed_apps}")
                logger.info(f"📋 جميع المواقع: {final_sites}")
                
                return True, f"http://{site_name}"
            else:
                logger.error(f"❌ [REAL] الموقع غير موجود في القائمة النهائية")
                logger.error(f"📋 المواقع المتاحة: {final_sites}")
                return False, "الموقع غير موجود في القائمة النهائية"
            
        except Exception as e:
            logger.error(f"💥 [REAL] خطأ غير متوقع: {str(e)}")
            import traceback
            logger.error(f"📝 تفاصيل الخطأ: {traceback.format_exc()}")
            return False, f"خطأ غير متوقع: {str(e)}"

    def _create_site_metadata(self, site_name: str, company_name: str, email: str, apps: List[str]):
        """إنشاء بيانات وصفية للموقع"""
        try:
            site_dir = os.path.join(self.sites_path, site_name)
            os.makedirs(site_dir, exist_ok=True)
            
            metadata = {
                "company_name": company_name,
                "email": email,
                "apps_installed": apps,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "site_name": site_name,
                "manager": "RealFrappeManager"
            }
            
            metadata_file = os.path.join(site_dir, "site_metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💼 [REAL] تم حفظ بيانات الموقع: {metadata_file}")
            
        except Exception as e:
            logger.warning(f"⚠️ [REAL] فشل حفظ البيانات الوصفية: {str(e)}")

    def get_all_sites(self) -> List[str]:
        """الحصول على قائمة المواقع الفعلية"""
        try:
            success, output = self.execute_bench_command(["site", "list"])
            
            if success:
                sites = []
                for line in output.split('\n'):
                    site = line.strip()
                    if site and not site.startswith('#'):
                        sites.append(site)
                return sites
            else:
                logger.error(f"❌ [REAL] فشل جلب المواقع: {output}")
                return []
                
        except Exception as e:
            logger.error(f"❌ [REAL] خطأ في جلب المواقع: {e}")
            return []

    def get_site_info(self, site_name: str) -> Dict:
        """الحصول على معلومات الموقع"""
        try:
            sites = self.get_all_sites()
            if site_name in sites:
                return {
                    'name': site_name,
                    'status': 'active',
                    'url': f"http://{site_name}",
                    'exists': True,
                    'manager': 'RealFrappeManager'
                }
            else:
                return {'error': 'الموقع غير موجود', 'exists': False}
        except Exception as e:
            return {'error': str(e), 'exists': False}

# إجبار استخدام المدير الفعلي دائماً - لا محاكاة
frappe_direct_manager = RealFrappeManager()
logger.info("🎯 تم تحميل RealFrappeManager بشكل إجباري - لا محاكاة!")

# دالة مساعدة للاختبار السريع
def test_bench_connection():
    """اختبار سريع للاتصال"""
    logger.info("🧪 بدء اختبار الاتصال السريع...")
    manager = RealFrappeManager()
    
    # اختبار بسيط
    success, output = manager.execute_bench_command(["--version"])
    if success:
        logger.info("✅ اختبار الاتصال ناجح!")
        return True
    else:
        logger.error("❌ اختبار الاتصال فاشل!")
        return False

# تشغيل الاختبار عند التحميل
test_bench_connection()