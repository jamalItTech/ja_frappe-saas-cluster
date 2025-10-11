import subprocess
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class NginxManager:
    """مدير لإعدادات Nginx"""

    def __init__(self):
        self.nginx_conf_dir = "/etc/nginx/conf.d/dynamic"
        self.proxy_server = "frappe-light-proxy"  # اسم حاوية الـ proxy الصحيح
        self.main_conf = "/etc/nginx/nginx.conf"
        self.dynamic_include = "include /etc/nginx/conf.d/dynamic/*.conf;"

    def execute_nginx_command(self, command: str) -> Tuple[bool, str]:
        """تنفيذ أوامر Nginx في حاوية proxy-server"""
        try:
            docker_cmd = [
                "docker", "exec", self.proxy_server,
                "bash", "-c", command
            ]

            logger.info(f"🔧 تنفيذ أمر Nginx: {command}")

            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except Exception as e:
            logger.exception("خطأ أثناء تنفيذ أمر Nginx")
            return False, str(e)

    def ensure_dynamic_include(self) -> Tuple[bool, str]:
        """يتأكد من أن nginx.conf يحتوي على include الخاص بالمجلد الديناميكي"""
        try:
            # قراءة الملف الحالي
            success, content = self.execute_nginx_command(f"cat {self.main_conf}")
            if not success:
                return False, f"فشل قراءة nginx.conf: {content}"

            if self.dynamic_include in content:
                logger.info("✅ ملف nginx.conf يحتوي على include الديناميكي بالفعل.")
                return True, "include موجود بالفعل."

            # إدراج include داخل كتلة http
            modified_content = ""
            inside_http = False
            for line in content.splitlines():
                modified_content += line + "\n"
                if line.strip().startswith("http {"):
                    inside_http = True
                elif inside_http and line.strip() == "}":
                    # قبل إغلاق http نضيف السطر المطلوب
                    modified_content += f"    {self.dynamic_include}\n"
                    inside_http = False

            # حفظ الملف المعدل
            temp_path = "/tmp/nginx.conf.tmp"
            cmd = f"echo '{modified_content}' > {temp_path} && mv {temp_path} {self.main_conf}"
            success, output = self.execute_nginx_command(cmd)
            if not success:
                return False, f"فشل تعديل nginx.conf: {output}"

            # اختبار Nginx بعد التعديل
            test_success, test_output = self.execute_nginx_command("nginx -t")
            if not test_success:
                return False, f"فشل اختبار Nginx بعد التعديل: {test_output}"

            # إعادة تحميل Nginx
            reload_success, reload_output = self.execute_nginx_command("nginx -s reload")
            if not reload_success:
                return False, f"فشل إعادة تحميل Nginx بعد التعديل: {reload_output}"

            logger.info("✅ تم تعديل nginx.conf وإضافة include الديناميكي.")
            return True, "تمت إضافة include بنجاح."

        except Exception as e:
            logger.exception("خطأ أثناء التحقق من include في nginx.conf")
            return False, str(e)

    def create_site_config(self, site_name: str) -> Tuple[bool, str]:
        """إنشاء تكوين Nginx للموقع الجديد"""
        try:
            # تأكد أولًا أن nginx.conf جاهز
            self.ensure_dynamic_include()

            config_filename = site_name.replace('.', '_') + ".conf"
            config_path = f"{self.nginx_conf_dir}/{config_filename}"

            # استخدام عنوان Frappe الصحيح من docker-compose.yml
            nginx_config = f"""
# {site_name} - Auto-generated configuration basada على docker-compose
server {{
    listen 80;
    server_name {site_name};

    access_log /var/log/nginx/{site_name.replace('.', '_')}_access.log;
    error_log /var/log/nginx/{site_name.replace('.', '_')}_error.log;

    location / {{
        proxy_pass http://172.25.3.10:8000;  # frappe-light-app-1 من docker-compose
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;

        # إعدادات إضافية لـ Frappe
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
    }}

    location /assets {{
        proxy_pass http://172.25.3.10:8000;  # frappe-light-app-1
        proxy_set_header Host $host;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}

    # معالجة المقابس والأصول الأخرى
    location /socket.io {{
        proxy_pass http://172.25.3.10:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

            command = f"mkdir -p {self.nginx_conf_dir} && echo \"{nginx_config}\" > {config_path}"
            success, output = self.execute_nginx_command(command)
            if not success:
                return False, f"فشل إنشاء ملف التكوين: {output}"

            # اختبار تكوين Nginx
            test_success, test_output = self.execute_nginx_command("nginx -t")
            if not test_success:
                return False, f"فشل اختبار تكوين Nginx: {test_output}"

            # إعادة تحميل Nginx
            reload_success, reload_output = self.execute_nginx_command("nginx -s reload")
            if not reload_success:
                return False, f"فشل إعادة تحميل Nginx: {reload_output}"

            return True, f"✅ تم إنشاء التكوين وإعادة تحميل Nginx: {config_filename}"

        except Exception as e:
            logger.exception("خطأ في إنشاء تكوين Nginx")
            return False, str(e)

    # باقي الدوال تبقى كما هي...
    def remove_site_config(self, site_name: str) -> Tuple[bool, str]:
        """إزالة تكوين Nginx للموقع"""
        try:
            config_filename = site_name.replace('.', '_') + ".conf"
            config_path = f"{self.nginx_conf_dir}/{config_filename}"

            success, output = self.execute_nginx_command(f"rm -f {config_path}")
            if not success:
                return False, f"فشل إزالة ملف التكوين: {output}"

            reload_success, reload_output = self.execute_nginx_command("nginx -s reload")
            if not reload_success:
                return False, f"فشل إعادة تحميل Nginx: {reload_output}"

            return True, f"✅ تم إزالة التكوين: {config_filename}"

        except Exception as e:
            logger.exception("خطأ في إزالة تكوين Nginx")
            return False, str(e)

    def list_site_configs(self) -> List[str]:
        """الحصول على قائمة تكوينات المواقع"""
        try:
            success, output = self.execute_nginx_command(f"ls -1 {self.nginx_conf_dir}/*.conf 2>/dev/null || true")
            if success and output:
                return [line.strip() for line in output.splitlines() if line.strip()]
            return []
        except Exception as e:
            logger.exception("فشل جرد تكوينات Nginx")
            return []

# إنشاء مدير Nginx
nginx_manager = NginxManager()
