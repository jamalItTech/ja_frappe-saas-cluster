import subprocess
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class NginxManager:
    """مدير لإعدادات Nginx"""

    def __init__(self):
        self.nginx_conf_dir = "/etc/nginx/conf.d/dynamic"
        self.proxy_server = "proxy-server"  # اسم حاوية nginx الرئيسية

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
                logger.info(f"✅ نجاح أمر Nginx: {command}")
                return True, result.stdout.strip()
            else:
                logger.error(f"❌ فشل أمر Nginx: {result.stderr.strip()}")
                return False, result.stderr.strip()

        except Exception as e:
            logger.exception("خطأ أثناء تنفيذ أمر Nginx")
            return False, str(e)

    def create_site_config(self, site_name: str) -> Tuple[bool, str]:
        """إنشاء تكوين Nginx للموقع الجديد"""
        try:
            config_filename = site_name.replace('.', '_') + ".conf"
            config_path = f"{self.nginx_conf_dir}/{config_filename}"

            nginx_config = f"""
# {site_name} - Auto-generated configuration
server {{
    listen 80;
    server_name {site_name};

    access_log /var/log/nginx/{site_name.replace('.', '_')}_access.log;
    error_log /var/log/nginx/{site_name.replace('.', '_')}_error.log;

    location / {{
        proxy_pass http://app-server-1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }}

    location /assets {{
        proxy_pass http://app-server-1:8000;
        proxy_set_header Host $host;
        expires 1y;
        add_header Cache-Control "public, immutable";
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

            logger.info(f"✅ تم إنشاء تكوين Nginx لـ: {site_name}")
            return True, f"تم إنشاء التكوين وإعادة تحميل Nginx: {config_filename}"

        except Exception as e:
            logger.exception("خطأ في إنشاء تكوين Nginx")
            return False, str(e)

    def remove_site_config(self, site_name: str) -> Tuple[bool, str]:
        """إزالة تكوين Nginx للموقع"""
        try:
            config_filename = site_name.replace('.', '_') + ".conf"
            config_path = f"{self.nginx_conf_dir}/{config_filename}"

            success, output = self.execute_nginx_command(f"rm -f {config_path}")
            if not success:
                return False, f"فشل إزالة ملف التكوين: {output}"

            # إعادة تحميل Nginx بعد الحذف
            reload_success, reload_output = self.execute_nginx_command("nginx -s reload")
            if not reload_success:
                return False, f"فشل إعادة تحميل Nginx: {reload_output}"

            logger.info(f"✅ تم إزالة تكوين Nginx لـ: {site_name}")
            return True, f"تم إزالة التكوين: {config_filename}"

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
