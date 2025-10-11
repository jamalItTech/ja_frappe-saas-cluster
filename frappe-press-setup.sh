#!/bin/bash

# Frappe Press Production Setup Script
# Complete Frappe Bench + Press deployment

set -e

echo "🔧 إعداد Frappe Press الإنتاجي الكامل"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

highlight() {
    echo -e "${CYAN}$1${NC}"
}

# Verify prerequisites
check_prerequisites() {
    log "فحص المتطلبات الأساسية..."

    if ! command -v docker >/dev/null; then
        error "Docker غير مثبت"
        exit 1
    fi

    if ! command -v docker-compose >/dev/null; then
        error "docker-compose غير مثبت"
        exit 1
    fi

    # Check memory
    mem_gb=$(docker system info --format '{{.MemTotal}}' 2>/dev/null | sed 's/ //g' | awk '{print int($1/1024/1024/1024)}' 2>/dev/null || echo "4")
    if [ "$mem_gb" -lt 16 ]; then
        warning "⚠️ تحذير: ${mem_gb}GB RAM غير كافية لـ Production. يُفضل 16GB+"
        read -p "هل تريد المتابعة؟ (y/n): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "تم إلغاء الإعداد"
            exit 1
        fi
    fi

    success "✅ المتطلبات متوفرة"
}

# Create production environment configuration
create_env_file() {
    log "إنشاء ملف المتغيرات البيئية للإنتاج..."

    cat > .env << EOF
# Frappe Press Production Environment Variables

# ========== DATABASE ==========
MYSQL_ROOT_PASSWORD=frappe_prod_root_2025_secure_$(openssl rand -hex 8)
DB_HOST_USER=frappe_user
MYSQL_PASSWORD=prod_frappe_pass_$(openssl rand -hex 12)
FRAPPE_DEV_PASSWORD=dev_admin_secure_$(openssl rand -hex 8)
PRESS_DB_PASSWORD=press_prod_password_$(openssl rand -hex 12)

# ========== REDIS ==========
REDIS_PASSWORD=redis_prod_key_$(openssl rand -hex 16)
REDIS_CACHE_URL=redis://frappe-redis:6379/0
REDIS_QUEUE_URL=redis://frappe-redis:6379/1
REDIS_SOCKETIO_URL=redis://frappe-redis:6379/2

# ========== FRAPPE CONFIG ==========
CLUSTER_NAME=frappe-production-cluster
FRAPPE_SITE=erpnext.local
FRAPPE_ADMIN_PASSWORD=admin_prod_secure_$(openssl rand -hex 8)
FRAPPE_VERSION=v15.6.2
FRAPPE_APPS=erpnext,hrms,crm,wiki

# ========== PRESS CONFIG ==========
PRESS_SERVER_URL=http://frappe-press:8088
PRESS_ADMIN_EMAIL=admin@production.com
PRESS_ADMIN_PASSWORD=press_admin_secure_$(openssl rand -hex 12)

# ========== SERVICES CONFIG ==========
PROMETHEUS_RETENTION=365d  # 1 year
ELASTICSEARCH_JAVA_OPTS=-Xms2g -Xmx4g
GRAFANA_ADMIN_PASSWORD=grafana_prod_secure_$(openssl rand -hex 12)

# ========== SSL & SECURITY ==========
SSL_CERT_PATH=/etc/ssl/certs/frappe_press.crt
SSL_KEY_PATH=/etc/ssl/private/frappe_press.key
LETSENCRYPT_EMAIL=ssl@production.com
JWT_SECRET=jwt_prod_secret_$(openssl rand -hex 32)

# ========== RESOURCE LIMITS ==========
FRAPPE_MEMORY_LIMIT=4g
FRAPPE_CPU_LIMIT=2.0
PRESS_MEMORY_LIMIT=2g
PRESS_CPU_LIMIT=1.0
DB_MEMORY_LIMIT=8g
DB_CPU_LIMIT=2.0
REDIS_MEMORY_LIMIT=1g

# ========== MONITORING ==========
MONITORING_RETENTION_DAYS=90
LOG_RETENTION_DAYS=30
BACKUP_RETENTION_DAYS=60

# ========== NETWORKING ==========
FRAPPE_DB_IP=172.20.0.10
FRAPPE_REDIS_IP=172.20.0.11
FRAPPE_APP_01_IP=172.20.3.10
FRAPPE_APP_02_IP=172.20.3.11
FRAPPE_PRESS_IP=172.20.3.15
FRAPPE_LOAD_BALANCER_IP=172.20.0.2
SAAS_BACKEND_IP=172.20.0.200
SAAS_FRONTEND_IP=172.20.0.201

# ========== PORTS ==========
FRAPPE_APP_01_PORT=8001
FRAPPE_APP_02_PORT=8002
FRAPPE_PRESS_PORT=8088
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
SAAS_BACKEND_PORT=5000
SAAS_FRONTEND_PORT=8080

# ========== BACKUP CONFIG ==========
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_REMOTE_URL=s3://frappe-press-backups/production/
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# ========== ALERTING ==========
SLACK_WEBHOOK_URL=your_slack_webhook_url
ALERT_EMAIL_FROM=alerts@production.com
ALERT_EMAIL_TO=admin@production.com

# ========== AUTO SCALING ==========
AUTO_SCALE_ENABLED=true
MIN_APP_SERVERS=2
MAX_APP_SERVERS=10
SCALE_UP_CPU_THRESHOLD=75
SCALE_DOWN_CPU_THRESHOLD=30
SCALE_CHECK_INTERVAL=300

# ========== SECURITY ==========
FIREWALL_ENABLED=true
SSH_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/24
VPN_CERT_PATH=/etc/easy-rsa/keys
FAIL2BAN_ENABLED=true
LOG_SURVEILLANCE=true

EOF

    success "✅ تم إنشاء .env الإنتاجي مع كلمات مرور عشوائية آمنة"
    warning "⚠️ يرجى الاحتفاظ بملف .env آمن - يحتوي على كلمات مرور حيوية!"
}

# Setup network
setup_network() {
    highlight "تهيئة الشبكة الداخلية..."
    if ! docker network ls | grep -q frappe-production-net; then
        docker network create \
            --driver=bridge \
            --subnet=172.20.0.0/16 \
            --gateway=172.20.0.1 \
            --opt com.docker.network.bridge.name=br-frappe-prod \
            frappe-production-net
        success "✅ تم إنشاء شبكة frappe-production-net"
    else
        success "✅ شبكة frappe-production-net موجودة بالفعل"
    fi
}

# Create directories structure
create_directories() {
    highlight "إنشاء هيكل الملفات..."

    directories=(
        "volumes/frappe-db"
        "volumes/frappe-redis"
        "volumes/frappe-sites"
        "volumes/frappe-logs"
        "volumes/frappe-backups"
        "volumes/nginx-logs"
        "volumes/letsencrypt"
        "volumes/prometheus"
        "volumes/grafana"
        "volumes/elasticsearch"
        "config/nginx/sites"
        "config/nginx/ssl"
        "config/prometheus"
        "config/grafana/dashboards"
        "config/grafana/datasources"
        "scripts/backup"
        "scripts/monitoring"
        "scripts/security"
        "certs"
        "logs"
    )

    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            success "✅ تم إنشاء دليل: $dir"
        fi
    done
}

# Generate SSL certificates for development
generate_ssl_certs() {
    highlight "توليد شهادات SSL للتطوير..."

    if [ ! -f "certs/frappe-press.crt" ]; then
        log "توليد شهادات SSL self-signed..."

        # Generate private key
        openssl genrsa -out certs/frappe-press.key 2048

        # Generate certificate
        openssl req -new -x509 -key certs/frappe-press.key \
            -out certs/frappe-press.crt \
            -days 365 \
            -subj "/C=YE/ST=Aden/L=Aden/O=Frappe Press/CN=*.$CLUSTER_NAME" \
            -addext "subjectAltName = DNS:*.$CLUSTER_NAME, DNS:*.trial.$CLUSTER_NAME"

        success "✅ تم توليد شهادات SSL"
        warning "⚠️ هذه شهادات تجريبية فقط - استبدلها بشهادات Let's Encrypt في الإنتاج"
    else
        success "✅ شهادات SSL موجودة مسبقاً"
    fi
}

# Build custom Frappe images
build_custom_images() {
    highlight "بناء صور Docker مخصصة..."

    # Build Frappe Bench image with customizations
    log "بناء صورة Frappe Bench المخصصة..."
    cat > Dockerfile.frappe-custom << EOF
FROM frappe/bench:latest

# Install additional system packages
USER root
RUN apt-get update && apt-get install -y \\
    htop \\
    vim \\
    curl \\
    wget \\
    net-tools \\
    dnsutils \\
    iputils-ping \\
    traceroute \\
    telnet \\
    openssh-client \\
    mysql-client \\
    postgresql-client \\
    redis-tools \\
    git \\
    supervisor \\
    cron \\
    logrotate \\
    && rm -rf /var/lib/apt/lists/*

# Create directories for production
RUN mkdir -p /home/frappe/production \\
    /home/frappe/backups \\
    /home/frappe/logs \\
    /etc/supervisor/conf.d

# Configure supervisor
COPY config/supervisor/*.conf /etc/supervisor/conf.d/

# Configure crontab for scheduled tasks
COPY config/cron/production-cron /etc/cron.d/production-cron
RUN chmod 0644 /etc/cron.d/production-cron

# Security hardening
RUN sed -i 's/PermitRootLogin yes/PermitRootLogin no/g' /etc/ssh/sshd_config \\
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config

# Optimize for production
RUN echo "vm.swappiness=10" >> /etc/sysctl.conf \\
    && echo "net.core.somaxconn=65536" >> /etc/sysctl.conf

# Set proper permissions
RUN chown -R frappe:frappe /home/frappe

USER frappe
WORKDIR /home/frappe/frappe-bench

# Install common apps
RUN bench get-app hrms \\
    && bench get-app crm \\
    && bench get-app wiki \\
    && bench get-app payments

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
EOF

    # Build the image
    if docker build -t frappe/bench:production -f Dockerfile.frappe-custom .; then
        success "✅ تم بناء صورة Frappe Bench المخصصة"
    else
        error "❌ فشل في بناء صورة Frappe Bench"
        exit 1
    fi
}

# Setup Frappe Bench and Press
setup_frappe() {
    highlight "إعداد Frappe Bench والـ Press..."

    cat > docker-compose.production.yml << EOF
version: '3.8'

services:
  # Production Database Layer
  frappe-db:
    image: mariadb:10.6
    container_name: frappe-prod-db
    restart: unless-stopped
    networks:
      frappe-production-net:
        ipv4_address: \${FRAPPE_DB_IP}
    environment:
      - MYSQL_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=frappe
      - MYSQL_USER=\${DB_HOST_USER}
      - MYSQL_PASSWORD=\${MYSQL_PASSWORD}
    volumes:
      - ./volumes/frappe-db:/var/lib/mysql
      - ./config/mysql:/etc/mysql/conf.d:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p\${MYSQL_ROOT_PASSWORD}"]
      interval: 30s
      timeout: 10s
      retries: 5
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --innodb-buffer-pool-size=4G
      --innodb-log-file-size=512M
      --max-connections=500
      --query-cache-size=256M
      --slow-query-log=1
      --slow-query-log-file=/var/lib/mysql/mysql-slow.log
      --long-query-time=2
    deploy:
      resources:
        limits:
          memory: \${DB_MEMORY_LIMIT}
          cpus: \${DB_CPU_LIMIT}
        reservations:
          memory: 4g
          cpus: '1.0'

  # Redis Cache Layer
  frappe-redis:
    image: redis:7-alpine
    container_name: frappe-prod-redis
    restart: unless-stopped
    networks:
      frappe-production-net:
        ipv4_address: \${FRAPPE_REDIS_IP}
    command: >
      --requirepass \${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --save 900 1
      --save 300 10
      --save 60 10000
    volumes:
      - ./volumes/frappe-redis:/data
      - ./config/redis/redis.conf:/etc/redis/redis.conf:ro
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: \${REDIS_MEMORY_LIMIT}
          cpus: '0.5'
        reservations:
          memory: 256m
          cpus: '0.25'

  # Application Server 1
  frappe-app-1:
    image: frappe/bench:production
    container_name: frappe-prod-app-1
    restart: unless-stopped
    depends_on:
      frappe-db:
        condition: service_healthy
      frappe-redis:
        condition: service_healthy
    networks:
      frappe-production-net:
        ipv4_address: \${FRAPPE_APP_01_IP}
    ports:
      - "\${FRAPPE_APP_01_PORT}:8000"
    environment:
      - DB_HOST=\${FRAPPE_DB_IP}
      - DB_PORT=3306
      - DB_USER=\${DB_HOST_USER}
      - DB_PASSWORD=\${MYSQL_PASSWORD}
      - REDIS_CACHE=\${REDIS_CACHE_URL}
      - REDIS_QUEUE=\${REDIS_QUEUE_URL}
      - REDIS_SOCKETIO=\${REDIS_SOCKETIO_URL}
      - APP_SERVER=true
      - AUTO_MIGRATE=true
    volumes:
      - ./volumes/frappe-sites:/home/frappe/frappe-bench/sites
      - ./volumes/frappe-logs/app1:/home/frappe/frappe-bench/logs
      - ./volumes/frappe-backups:/home/frappe/frappe-bench/backups
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/method/version"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: \${FRAPPE_MEMORY_LIMIT}
          cpus: \${FRAPPE_CPU_LIMIT}
        reservations:
          memory: 2g
          cpus: '1.0'

  # Application Server 2 (For load balancing)
  frappe-app-2:
    image: frappe/bench:production
    container_name: frappe-prod-app-2
    restart: unless-stopped
    depends_on:
      frappe-db:
        condition: service_healthy
      frappe-redis:
        condition: service_healthy
    networks:
      frappe-production-net:
        ipv4_address: \${FRAPPE_APP_02_IP}
    ports:
      - "\${FRAPPE_APP_02_PORT}:8000"
    environment:
      - DB_HOST=\${FRAPPE_DB_IP}
      - DB_PORT=3306
      - DB_USER=\${DB_HOST_USER}
      - DB_PASSWORD=\${MYSQL_PASSWORD}
      - REDIS_CACHE=\${REDIS_CACHE_URL}
      - REDIS_QUEUE=\${REDIS_QUEUE_URL}
      - REDIS_SOCKETIO=\${REDIS_SOCKETIO_URL}
      - APP_SERVER=true
      - AUTO_MIGRATE=true
    volumes:
      - ./volumes/frappe-sites:/home/frappe/frappe-bench/sites
      - ./volumes/frappe-logs/app2:/home/frappe/frappe-bench/logs
      - ./volumes/frappe-backups:/home/frappe/frappe-bench/backups
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/method/version"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: \${FRAPPE_MEMORY_LIMIT}
          cpus: \${FRAPPE_CPU_LIMIT}
        reservations:
          memory: 2g
          cpus: '1.0'

  # Frappe Press Server (Site Manager)
  frappe-press:
    image: frappe/bench:production
    container_name: frappe-prod-press
    restart: unless-stopped
    depends_on:
      frappe-app-1:
        condition: service_healthy
      frappe-app-2:
        condition: service_healthy
    networks:
      frappe-production-net:
        ipv4_address: \${FRAPPE_PRESS_IP}
    ports:
      - "\${FRAPPE_PRESS_PORT}:8000"
    environment:
      - PRESS_SERVER=true
      - ADMIN_EMAIL=\${PRESS_ADMIN_EMAIL}
      - ADMIN_PASSWORD=\${PRESS_ADMIN_PASSWORD}
      - JWT_SECRET=\${JWT_SECRET}
      - CLUSTER_SITES_URL=\${FRAPPE_LOAD_BALANCER_IP}
      - ENABLE_SSL=true
    volumes:
      - ./volumes/frappe-sites:/home/frappe/frappe-bench/sites
      - ./volumes/frappe-logs/press:/home/frappe/frappe-bench/logs
      - ./config/nginx/press-nginx.conf:/etc/nginx/sites-available/press.conf:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/method/press.version"]
      interval: 45s
      timeout: 15s
      retries: 3
    deploy:
      resources:
        limits:
          memory: \${PRESS_MEMORY_LIMIT}
          cpus: \${PRESS_CPU_LIMIT}
        reservations:
          memory: 1g
          cpus: '0.5'

  # Load Balancer
  frappe-load-balancer:
    image: nginx:1.25-alpine
    container_name: frappe-prod-lb
    restart: unless-stopped
    depends_on:
      - frappe-app-1
      - frappe-app-2
      - frappe-press
    networks:
      frappe-production-net:
        ipv4_address: \${FRAPPE_LOAD_BALANCER_IP}
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/sites:/etc/nginx/conf.d:ro
      - ./certs:/etc/ssl/certs:ro
      - ./volumes/nginx-logs:/var/log/nginx
      - ./volumes/letsencrypt:/etc/letsencrypt
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  # SaaS Trial Backend
  saas-backend:
    build: ./saas-system-complete/backend
    container_name: saas-prod-backend
    restart: unless-stopped
    depends_on:
      frappe-db:
        condition: service_healthy
      frappe-press:
        condition: service_healthy
    networks:
      frappe-production-net:
        ipv4_address: \${SAAS_BACKEND_IP}
    ports:
      - "\${SAAS_BACKEND_PORT}:5000"
    environment:
      - FLASK_ENV=production
      - DB_HOST=\${FRAPPE_DB_IP}
      - DB_USER=\${DB_HOST_USER}
      - DB_PASSWORD=\${MYSQL_PASSWORD}
      - DB_NAME=saas_trials_prod
      - SECRET_KEY=\${JWT_SECRET}
      - FRAPPE_PRESS_URL=\${PRESS_SERVER_URL}
      - FRAPPE_LOAD_BALANCER=\${FRAPPE_LOAD_BALANCER_IP}
      - PRODUCTION_MODE=true
    volumes:
      - ./saas-system-complete/backend:/app:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 15s
      retries: 3

  # SaaS Trial Frontend
  saas-frontend:
    build: ./saas-system-complete/frontend
    container_name: saas-prod-frontend
    restart: unless-stopped
    depends_on:
      - saas-backend
    networks:
      frappe-production-net:
        ipv4_address: \${SAAS_FRONTEND_IP}
    ports:
      - "\${SAAS_FRONTEND_PORT}:80"
    environment:
      - API_BASE_URL=http://\${SAAS_BACKEND_IP}:5000
    volumes:
      - ./saas-system-complete/frontend:/usr/share/nginx/html:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  frappe-production-net:
    external: true

volumes:
  frappe-db-volume:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./volumes/frappe-db
  frappe-sites-volume:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./volumes/frappe-sites
EOF

    success "✅ تم إنشاء docker-compose.production.yml للإنتاج"
}

# Create configuration files
create_config_files() {
    highlight "إنشاء ملفات التكوين..."

    # Nginx configuration for load balancer
    cat > config/nginx/nginx.conf << EOF
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    log_format upstream '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                        '\$status \$body_bytes_sent "\$http_referer" '
                        '"\$http_user_agent" "upstream: \$upstream_addr" '
                        'rt=\$request_time ua=\$upstream_response_time"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        text/plain
        text/css
        application/json
        application/javascript
        text/xml
        application/xml
        application/xml+rss
        text/javascript;

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;

    # Upstream servers
    upstream frappe_backend {
        ip_hash;
        server \${FRAPPE_APP_01_IP}:8000 max_fails=3 fail_timeout=30s;
        server \${FRAPPE_APP_02_IP}:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # LuaJIT for dynamic configurations
    lua_package_path "/etc/nginx/lua/?.lua;;";
    init_by_lua_block {
        require "cjson"
    }

    include /etc/nginx/conf.d/*.conf;
}
EOF

    # Nginx site configuration
    cat > config/nginx/sites/default.conf << EOF
server {
    listen 80;
    server_name ~^(?<subdomain>.+)\.\${CLUSTER_NAME}$ ~^\${CLUSTER_NAME}$;
    root /usr/share/nginx/html;
    index index.html index.htm;

    # SSL configuration
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/certs/frappe-press.crt;
    ssl_certificate_key /etc/ssl/private/frappe_press.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

    # Security
    ssl_prefer_server_ciphers off;

    # Rate limiting
    limit_req zone=api burst=20 nodelay;

    # Static files with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Frappe Press admin
    location /press {
        proxy_pass http://\${FRAPPE_PRESS_IP}:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Websocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        client_max_body_size 50M;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Trial sites
    location / {
        # Rate limiting for login pages
        location ~* /login|/app/login {
            limit_req zone=login burst=5 nodelay;
        }

        proxy_pass http://frappe_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;

        # Websocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Performance optimizations
        proxy_buffering off;
        proxy_request_buffering off;
        client_max_body_size 100M;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # Health checks from load balancer
        location /nginx-health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Monitoring endpoint
    location /metrics {
        allow 172.20.0.0/16;
        deny all;
        stub_status on;
        access_log off;
    }
}

# SaaS Trial System Server
server {
    listen 8080;
    server_name saas.\${CLUSTER_NAME};
    root /usr/share/nginx/html;
    index index.html;

    # SSL
    listen 8443 ssl http2;
    ssl_certificate /etc/ssl/certs/frappe-press.crt;
    ssl_certificate_key /etc/ssl/private/frappe_press.key;

    location /api {
        proxy_pass http://\${SAAS_BACKEND_IP}:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Prometheus configuration
    cat > config/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

scrape_configs:
  # Frappe Application Servers
  - job_name: 'frappe-app-1'
    static_configs:
      - targets: ['\${FRAPPE_APP_01_IP}:8000']
    scrape_interval: 30s
    metrics_path: /metrics

  - job_name: 'frappe-app-2'
    static_configs:
      - targets: ['\${FRAPPE_APP_02_IP}:8000']
    scrape_interval: 30s
    metrics_path: /metrics

  # Frappe Press
  - job_name: 'frappe-press'
    static_configs:
      - targets: ['\${FRAPPE_PRESS_IP}:8000']
    scrape_interval: 45s
    metrics_path: /metrics

  # SaaS Backend
  - job_name: 'saas-backend'
    static_configs:
      - targets: ['\${SAAS_BACKEND_IP}:5000']
    scrape_interval: 30s
    metrics_path: /metrics

  # Load Balancer metrics
  - job_name: 'nginx-lb'
    static_configs:
      - targets: ['\${FRAPPE_LOAD_BALANCER_IP}:80']
    scrape_interval: 30s
    metrics_path: /metrics

  # Database metrics
  - job_name: 'frappe-db'
    static_configs:
      - targets: ['\${FRAPPE_DB_IP}:3306']
    scrape_interval: 60s
    params:
      collect[]:
        - global_status
        - global_variables
        - engine_innodb_status

  # Container metrics
  - job_name: 'docker'
    static_configs:
      - targets: ['host.docker.internal:9323']
EOF

    success "✅ تم إنشاء ملفات التكوين الأساسية"
}

# Main setup function
main() {
    highlight "=============================================="
    highlight "🚀 إعداد Frappe Press الإنتاجي الكامل"
    highlight "=============================================="

    check_prerequisites
    create_env_file
    setup_network
    create_directories
    generate_ssl_certs
    build_custom_images
    setup_frappe
    create_config_files

    echo ""
    highlight "=============================================="
    success "🎊 تم إعداد Frappe Press الإنتاجي بنجاح!"
    highlight "=============================================="

    echo ""
    log "الخطوات التالية:"
    echo "1. قم بمراجعة ملف .env والمتغيرات الحساسة"
    echo "2. تشغيل النظام: docker-compose -f docker-compose.production.yml up -d"
    echo "3. إعداد أول Site: ./scripts/frappe-bench-init.sh"
    echo "4. اختبار النظام: ./scripts/test-cluster.sh"
    echo ""
    log "أوامر مفيدة:"
    echo "  عرض الحالة: docker-compose -f docker-compose.production.yml ps"
    echo "  عرض السجلات: docker-compose -f docker-compose.production.yml logs -f"
    echo "  إيقاف النظام: docker-compose -f docker-compose.production.yml down"
    echo ""
    warning "⚠️ هذا إعداد إنتاجي متقدم - تأكد من فهمك للمتطلبات الأمنية"
}

# Handle errors
trap 'error "فشل في إعداد Frappe Press"' ERR

# Run setup
main "$@"
