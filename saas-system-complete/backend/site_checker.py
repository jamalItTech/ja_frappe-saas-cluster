import mysql.connector
import logging
from typing import dict, List, Optional

logger = logging.getLogger(__name__)

class SiteChecker:
    """مدير للتحقق من إنشاء المواقع في Frappe Press"""
    
    def __init__(self):
        self.frappe_db_config = {
            'host': '172.20.0.10',
            'user': 'root',
            'password': '123456',
            'database': 'frappe'
        }
        
        self.saas_db_config = {
            'host': '172.20.0.102',
            'user': 'root',
            'password': '123456',
            'database': 'saas_trialsv1'
        }
    
    def check_site_in_frappe_db(self, site_name: str) -> dict:
        """التحقق من وجود الموقع في قاعدة بيانات Frappe"""
        try:
            conn = mysql.connector.connect(**self.frappe_db_config)
            cursor = conn.cursor(dictionary=True)
            
            # التحقق من جدول المواقع
            cursor.execute("SHOW TABLES LIKE 'tabSite'")
            site_table_exists = cursor.fetchone() is not None
            
            if not site_table_exists:
                return {"exists": False, "error": "جدول المواقع غير موجود"}
            
            # البحث عن الموقع
            cursor.execute("SELECT name, creation, modified FROM `tabSite` WHERE name = %s", (site_name,))
            site_record = cursor.fetchone()
            
            # التحقق من وجود جداول الموقع
            cursor.execute("SHOW TABLES LIKE %s", (f"{site_name}%",))
            site_tables = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return {
                "exists": site_record is not None,
                "site_record": site_record,
                "site_tables": site_tables,
                "tables_count": len(site_tables)
            }
            
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def check_site_in_saas_db(self, subdomain: str) -> dict:
        """التحقق من سجل الموقع في قاعدة بيانات SaaS"""
        try:
            conn = mysql.connector.connect(**self.saas_db_config)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, company_name, subdomain, site_url, site_name, 
                       created_at, frappe_site_created
                FROM trial_customers 
                WHERE subdomain = %s
            """, (subdomain,))
            
            customer_record = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                "exists": customer_record is not None,
                "customer_record": customer_record
            }
            
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def verify_site_creation(self, subdomain: str) -> dict:
        """التحقق الشامل من إنشاء الموقع"""
        site_name = f"{subdomain}.trial.local"
        
        logger.info(f"🔍 بدء التحقق من الموقع: {site_name}")
        
        # 1. التحقق من قاعدة بيانات SaaS
        saas_check = self.check_site_in_saas_db(subdomain)
        logger.info(f"📊 تحقق SaaS: {saas_check['exists']}")
        
        # 2. التحقق من قاعدة بيانات Frappe
        frappe_check = self.check_site_in_frappe_db(site_name)
        logger.info(f"🗄️ تحقق Frappe DB: {frappe_check['exists']}")
        
        # 3. نتيجة التحقق الشامل
        overall_success = saas_check['exists'] and frappe_check['exists']
        
        result = {
            "overall_success": overall_success,
            "site_name": site_name,
            "saas_database": saas_check,
            "frappe_database": frappe_check,
            "details": {
                "saas_record_exists": saas_check['exists'],
                "frappe_record_exists": frappe_check['exists'],
                "frappe_tables_count": frappe_check.get('tables_count', 0)
            }
        }
        
        if overall_success:
            logger.info(f"✅ التحقق ناجح: تم إنشاء الموقع {site_name}")
        else:
            logger.warning(f"⚠️ التحقق غير كامل: {site_name}")
            
            if not saas_check['exists']:
                logger.error("❌ لم يتم العثور على سجل في قاعدة بيانات SaaS")
            if not frappe_check['exists']:
                logger.error("❌ لم يتم العثور على سجل في قاعدة بيانات Frappe")
        
        return result
    
    def get_recent_sites(self, limit: int = 10) -> List[dict]:
        """الحصول على أحدث المواقع"""
        try:
            conn = mysql.connector.connect(**self.saas_db_config)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, company_name, subdomain, site_url, site_name, 
                       created_at, frappe_site_created
                FROM trial_customers 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            
            sites = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # التحقق من كل موقع في Frappe
            verified_sites = []
            for site in sites:
                verification = self.verify_site_creation(site['subdomain'])
                site['verification'] = verification
                verified_sites.append(site)
            
            return verified_sites
            
        except Exception as e:
            logger.error(f"❌ فشل جلب المواقع: {str(e)}")
            return []

# إنشاء مدير التحقق
site_checker = SiteChecker()
