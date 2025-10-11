#!/bin/bash

# 🌟 SaaS Trial System - Ultimate Startup Script
# نظام SaaS Trial متطور ومتكامل مع Load Balancing و Auto-scaling

set -e  # Exit on any error

# ===============================================
# المتغيرات والإعدادات
# ===============================================

# ألوان للإخراج
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# متغيرات النظام
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR" && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker-compose.mock.yml"
COMPOSE_PROFILE="mock"

# =======================
# وظائف المساعدة
# =======================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

highlight() {
    echo -e "${CYAN}$1${NC}"
}

title() {
    echo -e "${WHITE}$1${NC}"
    echo "=================================================================="
}

subtitle() {
    echo -e "${PURPLE}$1${NC}"
    echo "----------------------------------------------------------"
}

check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        error "$1 is not installed"
        return 1
    fi
    success "$1 is available"
    return 0
}

check_service_health() {
    local service_name="$1"
    local url="$2"
    local timeout="${3:-30}"
    local expected_code="${4:-200}"

    log "Checking $service_name health at $url..."

    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null)

    if [ "$response_code" -eq "$expected_code" ]; then
        success "$service_name is healthy (HTTP $response_code)"
        return 0
    else
        warning "$service_name returned HTTP $response_code (expected $expected_code)"
        return 1
    fi
}

# =======================
# وظائف النظام
# =======================

show_banner() {
    clear
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                 🌟 SaaS Trial Ultimate System                   ║
║                                                              ║
║         Multi-tenant Platform with Load Balancing           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

EOF
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --help, -h          Show this help message"
    echo "  --build             Force rebuild of all services"
    echo "  --logs              Show logs after startup"
    echo "  --test              Run comprehensive tests after startup"
    echo "  --clean             Clean all containers and volumes before starting"
    echo "  --profile PROFILE   Use docker-compose profile (mock/cluster/postgres)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start with mock mode"
    echo "  $0 --build           # Force rebuild and start"
    echo "  $0 --test            # Start and run tests"
    echo "  $0 --clean           # Clean everything and start fresh"
    echo ""
}

pre_check() {
    subtitle "🔍 Pre-flight Checks"

    # Check required commands
    local commands=("docker" "docker-compose" "curl")
    local cmd
    for cmd in "${commands[@]}"; do
        if ! check_command "$cmd"; then
            return 1
        fi
    done

    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running"
        return 1
    fi
    success "Docker daemon is running"

    return 0
}

clean_environment() {
    subtitle "🧹 Cleaning Environment"

    log "Stopping all running containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true

    log "Removing unused networks..."
    docker network prune -f >/dev/null 2>&1 || true

    log "Removing stopped containers..."
    docker container prune -f >/dev/null 2>&1 || true

    success "Environment cleaned"
}

create_network() {
    subtitle "🌐 Setting Up Networks"

    local network_name="frappe-cluster-net"
    local subnet="172.25.0.0/16"
    local gateway="172.25.0.1"

    if docker network ls | grep -q "$network_name"; then
        log "Network $network_name already exists"
        return 0
    fi

    log "Creating network: $network_name (subnet: $subnet)"

    if docker network create \
        --driver=bridge \
        --subnet="$subnet" \
        --gateway="$gateway" \
        "$network_name"; then
        success "Network created successfully"
        return 0
    else
        error "Failed to create network"
        return 1
    fi
}

start_services() {
    local force_build="$1"
    subtitle "🚀 Starting Services"

    local compose_cmd="docker-compose -f $DOCKER_COMPOSE_FILE"

    # Add build flag if requested
    if [ "$force_build" = "true" ]; then
        compose_cmd="$compose_cmd --build"
    fi

    log "Starting services..."

    if $compose_cmd up -d 2>/dev/null; then
        success "Services started successfully"
        return 0
    else
        error "Failed to start services"
        show_service_logs 10
        return 1
    fi
}

wait_for_services() {
    subtitle "⏳ Waiting for Services to be Ready"

    local services=(
        "http://localhost:5000/api/health:Backend API:60"
        "http://localhost:8080:Frontend:30"
        "http://localhost:8090:Database Adminer:15"
    )

    local all_ready=true

    for service_info in "${services[@]}"; do
        IFS=':' read -r url name timeout <<< "$service_info"

        if ! check_service_health "$name" "$url" "$timeout"; then
            all_ready=false
            if [ "$name" = "Frontend" ] || [ "$name" = "Backend API" ]; then
                # Critical services
                error "Critical service $name failed to start"
                return 1
            else
                warning "Non-critical service $name may not be ready"
            fi
        fi

        sleep 2
    done

    if [ "$all_ready" = "true" ]; then
        success "All services are ready! 🎉"
        return 0
    fi

    return 0  # Don't fail for non-critical services
}

show_service_logs() {
    local tail_lines="${1:-20}"
    log "Fetching recent logs..."

    echo ""
    highlight "Recent Service Logs (last $tail_lines lines):"
    echo ""

    docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail="$tail_lines" 2>/dev/null || true
}

show_service_status() {
    subtitle "📊 Service Status"

    echo "Current container status:"
    echo ""

    docker-compose -f "$DOCKER_COMPOSE_FILE" ps

    echo ""
    echo "Network information:"
    echo ""

    docker network ls | grep frappe
}

show_access_urls() {
    subtitle "🌐 Access URLs"

    cat << EOF
🎨 Frontend (SaaS Trial Interface):
   ➤ http://localhost:8080

⚙️ Backend API:
   ➤ http://localhost:5000
   ➤ Health Check: http://localhost:5000/api/health

🗄️ Database Adminer:
   ➤ http://localhost:8090
   Server: 172.25.0.102
   Username: saas_user
   Password: saas123
   Database: saas_trials

📧 Email Testing (MailHog):
   ➤ http://localhost:8025

📈 Redis Cache:
   ➤ localhost:6380

🔧 Additional Services:
   ➤ Create Trial Customer:
     curl -X POST http://localhost:5000/api/create-trial \\
     -H "Content-Type: application/json" \\
     -d '{"company_name":"Test Company","full_name":"Test User","email":"test@company.com","selected_apps":["erpnext"]}'

EOF
}

run_comprehensive_tests() {
    subtitle "🧪 Running Comprehensive Tests"

    local test_passed=0
    local test_failed=0

    # Test 1: Health Check
    log "Test 1: Health Check API"
    if check_service_health "Health Check" "http://localhost:5000/api/health" 10 200; then
        ((test_passed++))
    else
        ((test_failed++))
    fi

    # Test 2: Recent Customers API
    log "Test 2: Recent Customers API"
    if check_service_health "Recent Customers" "http://localhost:5000/api/recent-customers" 10 200; then
        ((test_passed++))
    else
        ((test_failed++))
    fi

    # Test 3: Frontend
    log "Test 3: Frontend Content"
    if curl -s "http://localhost:8080" | grep -q "SaaS"; then
        success "Frontend served correct content"
        ((test_passed++))
    else
        error "Frontend not serving correct content"
        ((test_failed++))
    fi

    # Test 4: Database Connection
    log "Test 4: Database Connection"
    if docker exec saas-trial-database-mock mysql -u saas_user -psaas123 -e "SELECT 1;" >/dev/null 2>&1; then
        success "Database connection successful"
        ((test_passed++))
    else
        error "Database connection failed"
        ((test_failed++))
    fi

    # Summary
    echo ""
    highlight "Test Results:"
    echo "✅ Passed: $test_passed tests"
    echo "❌ Failed: $test_failed tests"
    echo "📊 Total:  $((test_passed + test_failed)) tests"

    if [ $test_failed -eq 0 ]; then
        success "All tests passed! 🎉"
        return 0
    else
        warning "Some tests failed. Check logs for details."
        return 1
    fi
}

create_demo_customer() {
    log "Creating demo customer..."

    local demo_data='{
        "company_name": "شركة التكنولوجيا المتقدمة",
        "full_name": "أحمد محمد السعدي",
        "email": "ahmed@advanced-tech.com",
        "phone": "+967-1-234567",
        "password": "demo123",
        "selected_apps": ["erpnext", "hrms", "crm"],
        "trial_days": 30
    }'

    local response
    if response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        http://localhost:5000/api/create-trial \
        -d "$demo_data" 2>/dev/null); then

        local body=$(echo "$response" | head -n -1)
        local status_code=$(echo "$response" | tail -n 1)

        if [ "$status_code" -eq 200 ] && echo "$body" | grep -q '"success":true'; then
            success "Demo customer created successfully"
            return 0
        else
            warning "Demo customer creation returned status $status_code"
            return 1
        fi
    else
        error "Failed to create demo customer"
        return 1
    fi
}

show_final_summary() {
    subtitle "🎯 Final Summary"

    cat << EOF
✅ System Status: RUNNING
🚀 SaaS Trial Platform is ready for use!

Next steps you can try:

1. 🌐 Open Frontend: http://localhost:8080
2. 📝 Create Trial Account using the web interface
3. 🔍 Check Database: http://localhost:8090
4. 📊 Monitor Services: docker-compose -f $DOCKER_COMPOSE_FILE ps
5. 📝 View Logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f

Useful commands:
• Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down
• View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f backend
• Health check: curl http://localhost:5000/api/health

EOF
}

# =======================
# معالجة المعاملات
# =======================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_banner
                show_usage
                exit 0
                ;;
            --build)
                FORCE_BUILD=true
                shift
                ;;
            --logs)
                SHOW_LOGS=true
                shift
                ;;
            --test)
                RUN_TESTS=true
                shift
                ;;
            --clean)
                DO_CLEAN=true
                shift
                ;;
            --profile)
                COMPOSE_PROFILE="$2"
                if [ "$COMPOSE_PROFILE" = "cluster" ]; then
                    DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker-compose.cluster.yml"
                elif [ "$COMPOSE_PROFILE" = "postgres" ]; then
                    DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker-compose.postgres.yml"
                fi
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# =======================
# التنفيذ الرئيسي
# =======================

main() {
    # Parse arguments
    parse_args "$@"

    # Show banner
    show_banner

    # Pre-flight checks
    if ! pre_check; then
        error "Pre-flight checks failed"
        exit 1
    fi

    # Clean environment if requested
    if [ "$DO_CLEAN" = "true" ]; then
        clean_environment
    fi

    # Create network
    if ! create_network; then
        error "Failed to create Docker network"
        exit 1
    fi

    # Start services
    if ! start_services "$FORCE_BUILD"; then
        error "Failed to start services"
        exit 1
    fi

    # Wait for services
    if ! wait_for_services; then
        error "Services failed to become ready"
        show_service_logs 20
        exit 1
    fi

    # Show service status
    show_service_status

    # Show access URLs
    show_access_urls

    # Create demo customer
    if [ "$COMPOSE_PROFILE" = "mock" ] && [ "$SKIP_DEMO" != "true" ]; then
        create_demo_customer
    fi

    # Run tests if requested
    if [ "$RUN_TESTS" = "true" ]; then
        if ! run_comprehensive_tests; then
            warning "Some tests failed"
        fi
    fi

    # Show logs if requested
    if [ "$SHOW_LOGS" = "true" ]; then
        echo ""
        highlight "Service Logs (Press Ctrl+C to exit):"
        echo ""
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
    else
        # Show final summary
        show_final_summary
    fi
}

# =======================
# تشغيل السكريبت
# =======================

# Set error handler
trap 'error "Script failed at line $LINENO"; exit 1' ERR

# Change to project directory
cd "$SCRIPT_DIR"

# Export variables
export DOCKER_COMPOSE_FILE
export COMPOSE_PROFILE

# Run main function
main "$@"

success "SaaS Trial System started successfully! 🚀"
exit 0
