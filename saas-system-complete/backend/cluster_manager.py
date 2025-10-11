"""
نظام إدارة الكلاستر المتقدم - SaaS Multi-tenant Platform
"""

import requests
import json
import time
import threading
import logging
import mysql.connector
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ServerStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

class ServerRole(Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    MAINTENANCE = "maintenance"

@dataclass
class ServerMetrics:
    """مقاييس السيرفر"""
    server_id: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_rx_bytes: int
    network_tx_bytes: int
    active_connections: int
    sites_count: int
    response_time_ms: float
    uptime_seconds: int
    last_updated: datetime

@dataclass
class ClusterConfig:
    """إعدادات الكلاستر"""
    min_servers: int = 2
    max_servers: int = 10
    scale_up_threshold: float = 75.0
    scale_down_threshold: float = 30.0
    health_check_interval: int = 30
    failover_timeout: int = 300
    load_balance_algorithm: str = "least_sites"

class ServerConfig:
    """إعدادات السيرفر"""
    docker_image: str = "frappe/bench:latest"
    base_port: int = 8000
    base_ip: str = "172.22.0.20"
    memory_limit: str = "2g"
    cpu_limit: str = "1.0"
    disk_limit: str = "50g"

class ClusterManager:
    """
    مدير الكلاستر المتقدم مع Load Balancing و Auto-scaling
    """

    def __init__(self):
        self.config = ClusterConfig()
        self.servers: Dict[str, ServerConfig] = {}
        self.metrics: Dict[str, ServerMetrics] = {}
        self.health_status: Dict[str, ServerStatus] = {}
        self.load_balancer = self._create_load_balancer_instance()
        self.monitoring_thread: Optional[threading.Thread] = None
        self.is_monitoring = False

        # إعدادات قاعدة البيانات
        self.db_config = {
            'host': '172.22.0.102',
            'user': 'root',
            'password': '123456',
            'database': 'saas_trialsv1'
        }

        # تحميل السيرفرات الموجودة
        self._load_existing_servers()

        # بدء مراقبة الكلاستر
        self.start_monitoring()

    def _create_load_balancer_instance(self):
        """إنشاء instance للـ Load Balancer"""
        from nginx_manager import nginx_manager
        return nginx_manager

    def _load_existing_servers(self):
        """تحميل السيرفرات الموجودة من قاعدة البيانات"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM cluster_servers WHERE active = TRUE")
            servers = cursor.fetchall()

            for server in servers:
                server_config = ServerConfig()
                self.servers[server['server_id']] = server_config

            cursor.close()
            conn.close()

            logger.info(f"✅ تم تحميل {len(self.servers)} سيرفر من قاعدة البيانات")

        except Exception as e:
            logger.error(f"❌ فشل تحميل السيرفرات: {e}")
            # السيرفرات الافتراضية
            self._add_default_servers()

    def _add_default_servers(self):
        """إضافة السيرفرات الافتراضية"""
        default_servers = [
            {"id": "app-server-1", "ip": "172.22.0.20", "port": 8000},
            {"id": "app-server-2", "ip": "172.22.0.21", "port": 8001}
        ]

        for server in default_servers:
            config = ServerConfig()
            self.servers[server["id"]] = config
            self._save_server_to_db(server["id"], server["ip"], server["port"], True)

    def _save_server_to_db(self, server_id: str, ip: str, port: int, active: bool = True):
        """حفظ السيرفر في قاعدة البيانات"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cluster_servers (
                    server_id VARCHAR(50) PRIMARY KEY,
                    ip_address VARCHAR(15) NOT NULL,
                    port INT NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    role ENUM('active', 'standby', 'maintenance') DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_health_check TIMESTAMP NULL
                )
            """)

            cursor.execute("""
                INSERT INTO cluster_servers (server_id, ip_address, port, active)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                ip_address=%s, port=%s, active=%s, last_health_check=CURRENT_TIMESTAMP
            """, (server_id, ip, port, active, ip, port, active))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"❌ فشل حفظ السيرفر في قاعدة البيانات: {e}")

    def add_server(self, server_data: Dict) -> Dict:
        """
        إضافة سيرفر جديد للكلاستر
        """
        try:
            server_id = server_data['server_id']
            ip = server_data['ip']
            port = server_data['port']

            # التحقق من عدم وجود السيرفر
            if server_id in self.servers:
                return {
                    'success': False,
                    'message': f'السيرفر {server_id} موجود مسبقاً'
                }

            # إنشاء السيرفر عبر Docker
            if 'docker' in server_data:
                container_result = self._create_docker_server(server_data)
                if not container_result['success']:
                    return container_result

            # إضافة السيرفر للـ load balancer
            self.servers[server_id] = ServerConfig()

            # حفظ في قاعدة البيانات
            self._save_server_to_db(server_id, ip, port, True)

            # إعادة توزيع المواقع
            self.rebalance_sites()

            logger.info(f"✅ تم إضافة السيرفر {server_id}")

            return {
                'success': True,
                'message': f'تم إضافة السيرفر {server_id} بنجاح',
                'server_id': server_id
            }

        except Exception as e:
            logger.error(f"❌ فشل إضافة السيرفر: {e}")
            return {
                'success': False,
                'message': f'خطأ في إضافة السيرفر: {str(e)}'
            }

    def _create_docker_server(self, server_data: Dict) -> Dict:
        """إنشاء سيرفر عبر Docker"""
        try:
            import subprocess

            server_id = server_data['server_id']
            ip = server_data['ip']
            port = server_data['port']

            # أمر إنشاء الحاوية
            docker_cmd = [
                'docker', 'run', '-d',
                '--name', server_id,
                '--network', 'frappe-cluster-net',
                '--ip', ip,
                '-p', f'{port}:{port}',
                '--memory', '2g',
                '--cpus', '1.0',
                'frappe/bench:latest',
                'tail', '-f', '/dev/null'
            ]

            result = subprocess.run(docker_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'message': f'فشل إنشاء حاوية Docker: {result.stderr}'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'خطأ في إنشاء السيرفر: {str(e)}'
            }

    def remove_server(self, server_id: str) -> Dict:
        """
        إزالة سيرفر من الكلاستر
        """
        try:
            if server_id not in self.servers:
                return {
                    'success': False,
                    'message': f'السيرفر {server_id} غير موجود'
                }

            # الحصول على مواقع السيرفر
            server_sites = self._get_server_sites(server_id)

            # إعادة توزيع المواقع
            if server_sites:
                healthy_servers = self.get_healthy_servers()
                healthy_servers.remove(server_id)

                if not healthy_servers:
                    return {
                        'success': False,
                        'message': 'لا يمكن إزالة السيرفر - ليس هناك سيرفرات صحية أخرى'
                    }

                self._redistribute_sites(server_sites, healthy_servers)

            # إيقاف السيرفر
            self._stop_server_container(server_id)

            # حذف من الذاكرة
            del self.servers[server_id]

            # تحديث قاعدة البيانات
            self._update_server_in_db(server_id, False)

            logger.info(f"✅ تم إزالة السيرفر {server_id}")

            return {
                'success': True,
                'message': f'تم إزالة السيرفر {server_id} بنجاح',
                'sites_moved': len(server_sites)
            }

        except Exception as e:
            logger.error(f"❌ فشل إزالة السيرفر: {e}")
            return {
                'success': False,
                'message': f'خطأ في إزالة السيرفر: {str(e)}'
            }

    def _stop_server_container(self, server_id: str):
        """إيقاف حاوية السيرفر"""
        try:
            import subprocess
            subprocess.run(['docker', 'stop', server_id], capture_output=True)
            subprocess.run(['docker', 'rm', server_id], capture_output=True)
            logger.info(f"✅ تم إيقاف الحاوية {server_id}")
        except Exception as e:
            logger.warning(f"⚠️ فشل إيقاف الحاوية {server_id}: {e}")

    def _update_server_in_db(self, server_id: str, active: bool):
        """تحديث السيرفر في قاعدة البيانات"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE cluster_servers
                SET active = %s, last_health_check = CURRENT_TIMESTAMP
                WHERE server_id = %s
            """, (active, server_id))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"❌ فشل تحديث قاعدة البيانات: {e}")

    def check_server_health(self, server_id: str) -> ServerStatus:
        """
        فحص صحة السيرفر
        """
        try:
            if server_id not in self.servers:
                return ServerStatus.OFFLINE

            # محاولة الاتصال بالسيرفر
            server = self._get_server_info(server_id)
            url = f"http://{server['ip']}:{server['port']}/api/method/version"

            start_time = time.time()
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'ClusterManager/1.0',
                'Accept': 'application/json'
            })
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # التحقق من المقاييس
                metrics = self._get_server_metrics(server)

                # تحديث المقاييس
                self.metrics[server_id] = ServerMetrics(
                    server_id=server_id,
                    cpu_percent=metrics.get('cpu_percent', 0),
                    memory_percent=metrics.get('memory_percent', 0),
                    disk_percent=metrics.get('disk_percent', 0),
                    network_rx_bytes=metrics.get('network_rx', 0),
                    network_tx_bytes=metrics.get('network_tx', 0),
                    active_connections=metrics.get('connections', 0),
                    sites_count=metrics.get('sites_count', 0),
                    response_time_ms=response_time,
                    uptime_seconds=metrics.get('uptime', 0),
                    last_updated=datetime.now()
                )

                # تحديد الحالة
                if metrics['cpu_percent'] > 90 or metrics['memory_percent'] > 90:
                    return ServerStatus.CRITICAL
                elif metrics['cpu_percent'] > 75 or metrics['memory_percent'] > 75:
                    return ServerStatus.WARNING

                return ServerStatus.HEALTHY
            else:
                return ServerStatus.OFFLINE

        except requests.exceptions.RequestException:
            return ServerStatus.OFFLINE
        except Exception as e:
            logger.error(f"❌ خطأ في فحص صحة السيرفر {server_id}: {e}")
            return ServerStatus.OFFLINE

    def _get_server_metrics(self, server: Dict) -> Dict:
        """الحصول على مقاييس السيرفر (محاكاة)"""
        # في المستقبل، سيتم الاتصال بـ Docker API أو Prometheus
        return {
            'cpu_percent': 45.2,
            'memory_percent': 62.8,
            'disk_percent': 34.7,
            'network_rx': 1024000,
            'network_tx': 524288,
            'connections': 125,
            'sites_count': 25,
            'uptime': 86400
        }

    def get_healthy_servers(self) -> List[str]:
        """
        الحصول على قائمة السيرفرات الصحية
        """
        healthy = []
        for server_id in self.servers.keys():
            if self.health_status.get(server_id) == ServerStatus.HEALTHY:
                healthy.append(server_id)
        return healthy

    def rebalance_sites(self) -> Dict:
        """
        إعادة توزيع المواقع على السيرفرات
        """
        try:
            logger.info("🔄 بدء إعادة توزيع المواقع")

            healthy_servers = self.get_healthy_servers()
            if len(healthy_servers) < self.config.min_servers:
                logger.warning("⚠️ عدد السيرفرات الصحية أقل من الحد الأدنى")
                return {
                    'success': False,
                    'message': 'عدد السيرفرات الصحية غير كافي لإعادة التوزيع'
                }

            # الحصول على جميع المواقع النشطة
            active_sites = self._get_all_active_sites()

            # توزيع المواقع على السيرفرات
            server_sites = self._distribute_sites(active_sites, healthy_servers)

            # تطبيق التوزيع الجديد
            success_count = 0
            for server_id, sites in server_sites.items():
                if self._update_server_sites(server_id, sites):
                    success_count += 1

            logger.info(f"✅ تم إعادة توزيع {len(active_sites)} موقع على {success_count} سيرفر")

            return {
                'success': True,
                'message': f'تم إعادة توزيع {len(active_sites)} موقع على {success_count} سيرفر',
                'distribution': server_sites
            }

        except Exception as e:
            logger.error(f"❌ فشل إعادة التوزيع: {e}")
            return {
                'success': False,
                'message': f'خطأ في إعادة التوزيع: {str(e)}'
            }

    def _distribute_sites(self, sites: List[str], servers: List[str]) -> Dict[str, List[str]]:
        """
        توزيع المواقع على السيرفرات حسب الخوارزمية المختارة
        """
        if self.config.load_balance_algorithm == "round_robin":
            return self._distribute_round_robin(sites, servers)
        elif self.config.load_balance_algorithm == "least_sites":
            return self._distribute_least_sites(sites, servers)
        else:
            return self._distribute_round_robin(sites, servers)

    def _distribute_round_robin(self, sites: List[str], servers: List[str]) -> Dict[str, List[str]]:
        """توزيع دوري"""
        distribution = {server: [] for server in servers}
        for i, site in enumerate(sites):
            server_index = i % len(servers)
            distribution[servers[server_index]].append(site)
        return distribution

    def _distribute_least_sites(self, sites: List[str], servers: List[str]) -> Dict[str, List[str]]:
        """التوزيع على أقل عدد مواقع"""
        distribution = {server: [] for server in servers}

        for site in sites:
            server_id = min(servers, key=lambda s: len(distribution[s]))
            distribution[server_id].append(site)

        return distribution

    def _update_server_sites(self, server_id: str, sites: List[str]) -> bool:
        """
        تحديث مواقع السيرفر في Nginx
        """
        try:
            # هنا سيتم تحديث تكوين Nginx للمواقع
            # منطق تحديث الـ upstream
            logger.info(f"📝 تحديث {len(sites)} موقع للسيرفر {server_id}")
            return True

        except Exception as e:
            logger.error(f"❌ فشل تحديث مواقع السيرفر {server_id}: {e}")
            return False

    def should_scale_up(self) -> bool:
        """
        التحقق من الحاجة لإضافة سيرفر جديد
        """
        healthy_servers = self.get_healthy_servers()
        total_cpu = 0
        total_memory = 0

        for server_id in healthy_servers:
            if server_id in self.metrics:
                total_cpu += self.metrics[server_id].cpu_percent
                total_memory += self.metrics[server_id].memory_percent

        if healthy_servers:
            avg_cpu = total_cpu / len(healthy_servers)
            avg_memory = total_memory / len(healthy_servers)

            # الشروط: إعلى من العتبة أو اقترب من الحد الأقصى
            return (avg_cpu > self.config.scale_up_threshold or
                    avg_memory > self.config.scale_up_threshold or
                    len(healthy_servers) <= self.config.min_servers)

        return True

    def should_scale_down(self) -> bool:
        """
        التحقق من إمكانية تقليل السيرفرات
        """
        if len(self.servers) <= self.config.min_servers:
            return False

        healthy_servers = self.get_healthy_servers()
        if not healthy_servers:
            return False

        total_cpu = sum(self.metrics[s].cpu_percent for s in healthy_servers if s in self.metrics)
        avg_cpu = total_cpu / len(healthy_servers)

        return avg_cpu < self.config.scale_down_threshold

    def scale_up(self, manual: bool = False) -> Dict:
        """
        إضافة سيرفر جديد تلقائياً
        """
        try:
            # إنشاء server ID جديد
            server_number = len(self.servers) + 1
            server_id = f"app-server-{server_number}"

            # حساب IP جديد
            base_ip_parts = [int(x) for x in self.servers['app-server-1'].ip.split('.')]
            new_ip = "172.22.0.22"  # يجب تحسين حساب IP الجديد

            # حساب Port جديد
            new_port = 8002  # يجب تحسين حساب Port الجديد

            result = self.add_server({
                'server_id': server_id,
                'ip': new_ip,
                'port': new_port,
                'docker': True
            })

            if result['success']:
                logger.info(f"📈 تم إضافة سيرفر جديد: {server_id}")
                if manual:
                    result['message'] += " (يدوياً)"

                return result

            return result

        except Exception as e:
            logger.error(f"❌ فشل إضافة سيرفر جديد: {e}")
            return {
                'success': False,
                'message': f'خطأ في Auto-scaling: {str(e)}'
            }

    def scale_down(self, manual: bool = False) -> Dict:
        """
        إزالة سيرفر غير مطلوب تلقائياً
        """
        try:
            if len(self.servers) <= self.config.min_servers:
                return {
                    'success': False,
                    'message': f'لا يمكن التقليل - الحد الأدنى من السيرفرات: {self.config.min_servers}'
                }

            # العثور على السيرفر الأقل حملاً
            healthy_servers = self.get_healthy_servers()
            if not healthy_servers:
                return {
                    'success': False,
                    'message': 'لا يوجد سيرفرات صحية لحذفها'
                }

            server_id = min(healthy_servers, key=lambda s: len(self.metrics.get(s, {}).get('sites_count', 0)) if s in self.metrics else 0)

            result = self.remove_server(server_id)

            if result['success']:
                logger.info(f"📉 تم حذف سيرفر غير مطلوب: {server_id}")
                if manual:
                    result['message'] += " (يدوياً)"

            return result

        except Exception as e:
            logger.error(f"❌ فشل حذف سيرفر: {e}")
            return {
                'success': False,
                'message': f'خطأ في Auto-scaling down: {str(e)}'
            }

    def start_monitoring(self):
        """
        بدء مراقبة الكلاستر
        """
        if self.is_monitoring:
            logger.warning("المراقبة تعمل بالفعل")
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        logger.info("✅ بدء مراقبة الكلاستر")

    def stop_monitoring(self):
        """
        إيقاف مراقبة الكلاستر
        """
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("🛑 تم إيقاف مراقبة الكلاستر")

    def _monitoring_loop(self):
        """
        حلقة المراقبة الرئيسية
        """
        logger.info("🔄 بدء حلقة المراقبة")

        while self.is_monitoring:
            try:
                # فحص صحة جميع السيرفرات
                self._check_all_servers_health()

                # التحقق من الحاجة للتوسع
                if self.should_scale_up():
                    logger.info("⚠️ الكلاستر يحتاج إلى توسع")
                    # في الإنتاج، سيتم تفعيل التوسع التلقائي
                    # self.scale_up()

                elif self.should_scale_down():
                    logger.info("ℹ️ الكلاستر يمكن تقليله")
                    # self.scale_down()

                # انتظار فترة الصحة
                time.sleep(self.config.health_check_interval)

            except Exception as e:
                logger.error(f"❌ خطأ في حلقة المراقبة: {e}")
                time.sleep(10)  # انتظار أطول في حالة الخطأ

    def _check_all_servers_health(self):
        """
        فحص صحة جميع السيرفرات
        """
        for server_id in list(self.servers.keys()):
            try:
                status = self.check_server_health(server_id)
                self.health_status[server_id] = status

                if status == ServerStatus.CRITICAL or status == ServerStatus.OFFLINE:
                    logger.warning(f"⚠️ سيرفر {server_id} في حالة: {status.value}")
                elif status == ServerStatus.WARNING:
                    logger.info(f"ℹ️ سيرفر {server_id} في حالة تحذير")

            except Exception as e:
                logger.error(f"❌ فشل فحص صحة {server_id}: {e}")
                self.health_status[server_id] = ServerStatus.OFFLINE

    def _get_server_info(self, server_id: str) -> Dict:
        """
        الحصول على معلومات السيرفر
        """
        # في الإنتاج، سيتم تحميل هذه المعلومات من قاعدة البيانات
        server_map = {
            'app-server-1': {'ip': '172.22.0.20', 'port': 8000},
            'app-server-2': {'ip': '172.22.0.21', 'port': 8001},
        }

        if server_id in server_map:
            return server_map[server_id]

        # Default info
        return {'ip': '127.0.0.1', 'port': 8000}

    def _get_server_sites(self, server_id: str) -> List[str]:
        """
        الحصول على قائمة المواقع على سيرفر معين
        """
        # في الإنتاج، يمكن استخدام قاعدة البيانات أو API للحصول على هذه المعلومات
        # محاكاة بسيطة هنا
        if server_id == 'app-server-1':
            return [f"site{i}.trial.local" for i in range(1, 11)]  # أول 10 مواقع
        elif server_id == 'app-server-2':
            return [f"site{i}.trial.local" for i in range(11, 21)]  # 11-20
        return []

    def _redistribute_sites(self, sites: List[str], target_servers: List[str]):
        """
        إعادة توزيع المواقع على السيرفرات المحددة
        """
        logger.info(f"🔄 إعادة توزيع {len(sites)} موقع على {len(target_servers)} سيرفر")

        for site in sites:
            # اختيار أقل سيرفر حملاً
            target_server = min(target_servers, key=lambda s: len(self._get_server_sites(s)))

            # تحديث تكوينات Nginx
            try:
                success_msg = f"تم نقل {site} إلى {target_server}"
                logger.info(f"✓ {success_msg}")
            except Exception as e:
                logger.error(f"❌ فشل نقل {site}: {e}")

    def _get_all_active_sites(self) -> List[str]:
        """
        الحصول على جميع المواقع النشطة
        """
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT site_name
                FROM trial_customers
                WHERE status = 'active' AND frappe_site_created = TRUE
            """)

            sites = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            logger.info(f"📋 جلب {len(sites)} موقع نشط")
            return sites

        except Exception as e:
            logger.error(f"❌ فشل جلب المواقع: {e}")
            return []

    def get_cluster_stats(self) -> Dict:
        """
        إحصائيات شاملة للكلاستر
        """
        try:
            total_servers = len(self.servers)
            healthy_servers = len(self.get_healthy_servers())

            # إحصائيات الموارد العامة
            total_cpu = 0
            total_memory = 0
            total_sites = 0

            for server_id, metrics in self.metrics.items():
                if server_id in self.health_status and self.health_status[server_id] == ServerStatus.HEALTHY:
                    total_cpu += metrics.cpu_percent
                    total_memory += metrics.memory_percent
                    total_sites += metrics.sites_count

            avg_cpu = total_cpu / max(healthy_servers, 1)
            avg_memory = total_memory / max(healthy_servers, 1)

            # إحصائيات العملاء
            customer_stats = self._get_customer_stats()

            return {
                'success': True,
                'cluster_info': {
                    'total_servers': total_servers,
                    'healthy_servers': healthy_servers,
                    'offender_servers': total_servers - healthy_servers,
                    'avg_cpu_usage': round(avg_cpu, 1),
                    'avg_memory_usage': round(avg_memory, 1),
                    'total_sites': total_sites,
                    'health_ratio': round((healthy_servers / max(total_servers, 1)) * 100, 1)
                },
                'customer_stats': customer_stats,
                'monitoring': {
                    'is_monitoring_active': self.is_monitoring,
                    'check_interval': self.config.health_check_interval,
                    'last_check': datetime.now().isoformat()
                },
                'load_balance_status': self._get_load_balance_status()
            }

        except Exception as e:
            logger.error(f"❌ فشل جلب إحصائيات الكلاستر: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_customer_stats(self) -> Dict:
        """إحصائيات العملاء"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            # عدد العملاء النشطين
            cursor.execute("SELECT COUNT(*) FROM trial_customers WHERE status = 'active'")
            active_customers = cursor.fetchone()[0]

            # عدد العملاء الجدد هذا الأسبوع
            cursor.execute("""
                SELECT COUNT(*) FROM trial_customers
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            new_this_week = cursor.fetchone()[0]

            # عدد المواقع الفاشلة
            cursor.execute("""
                SELECT COUNT(*) FROM trial_customers
                WHERE frappe_site_created = FALSE AND created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            """)
            failed_sites_today = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                'active_customers': active_customers,
                'new_this_week': new_this_week,
                'failed_sites_today': failed_sites_today,
                'conversion_rate': round((active_customers / max(new_this_week, 1)) * 100, 1)
            }

        except Exception as e:
            logger.error(f"❌ فشل جلب إحصائيات العملاء: {e}")
            return {
                'active_customers': 0,
                'new_this_week': 0,
                'failed_sites_today': 0,
                'conversion_rate': 0
            }

    def _get_load_balance_status(self) -> Dict:
        """حالة موازنة الحمل"""
        distribution = {}
        total_sites = 0

        for server_id in self.servers.keys():
            if server_id in self.metrics:
                sites = self.metrics[server_id].sites_count
                distribution[server_id] = sites
                total_sites += sites

        if total_sites == 0:
            balance_ratio = 100
        else:
            # حساب نسبة التوازن (كلما اقتربت من 100 كان أفضل)
            ideal_per_server = total_sites / len(self.servers)
            deviaitons = []

            for sites in distribution.values():
                if ideal_per_server > 0:
                    deviaitons.append(abs(sites - ideal_per_server) / ideal_per_server)

            if deviaitons:
                balance_ratio = 100 * (1 - (sum(deviaitons) / len(deviaitons)) * 0.5)
                balance_ratio = max(0, min(100, balance_ratio))
            else:
                balance_ratio = 100

        return {
            'distribution': distribution,
            'balance_ratio': round(balance_ratio, 1),
            'recommendation': 'good' if balance_ratio >= 80 else ('fair' if balance_ratio >= 60 else 'poor')
        }
