#!/bin/bash
# Tiquemax POS System - Podman Pod Management Script
# Usage: ./manage-pod.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POD_NAME="tiquemax-pos"
ENV_FILE="../../.env.production"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_pod_exists() {
    if ! podman pod exists "$POD_NAME"; then
        log_error "Pod '$POD_NAME' does not exist!"
        log_info "Create it first with: ./create-pod.sh"
        exit 1
    fi
}

# Commands
cmd_start() {
    log_info "Starting Tiquemax POS Pod..."
    check_pod_exists
    podman pod start "$POD_NAME"
    log_success "Pod started successfully"
    cmd_status
}

cmd_stop() {
    log_info "Stopping Tiquemax POS Pod..."
    check_pod_exists
    podman pod stop "$POD_NAME"
    log_success "Pod stopped successfully"
}

cmd_restart() {
    log_info "Restarting Tiquemax POS Pod..."
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    log_info "Pod Status:"
    podman pod ps --filter name="$POD_NAME"
    echo ""
    log_info "Container Status:"
    podman ps --filter pod="$POD_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

cmd_logs() {
    local service=$1
    check_pod_exists

    if [ -z "$service" ]; then
        log_info "Showing logs for all containers in pod..."
        podman pod logs -f "$POD_NAME"
    else
        local container_name="${POD_NAME}-${service}"
        log_info "Showing logs for $container_name..."
        podman logs -f "$container_name"
    fi
}

cmd_shell() {
    check_pod_exists
    log_info "Opening Django shell..."
    podman exec -it "${POD_NAME}-web" python manage.py shell
}

cmd_dbshell() {
    check_pod_exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
    source "$ENV_FILE"
    log_info "Opening database shell..."
    podman exec -it "${POD_NAME}-db" psql -U "$DB_USER" -d "$DB_NAME"
}

cmd_migrate() {
    check_pod_exists
    log_info "Running database migrations..."
    podman exec "${POD_NAME}-web" python manage.py migrate --noinput
    log_success "Migrations completed"
}

cmd_collectstatic() {
    check_pod_exists
    log_info "Collecting static files..."
    podman exec "${POD_NAME}-web" python manage.py collectstatic --noinput
    log_success "Static files collected"
}

cmd_createsuperuser() {
    check_pod_exists
    log_info "Creating superuser..."
    podman exec -it "${POD_NAME}-web" python manage.py createsuperuser
}

cmd_backup() {
    check_pod_exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
    source "$ENV_FILE"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="../../backups"
    local backup_file="$backup_dir/tiquemax_pod_backup_$timestamp.sql"

    mkdir -p "$backup_dir"

    log_info "Creating database backup..."
    podman exec "${POD_NAME}-db" pg_dump -U "$DB_USER" "$DB_NAME" > "$backup_file"

    if [ -f "$backup_file" ]; then
        gzip "$backup_file"
        log_success "Backup created: ${backup_file}.gz"

        # Clean old backups (older than 30 days)
        find "$backup_dir" -name "*.sql.gz" -mtime +30 -delete 2>/dev/null || true
        log_info "Old backups cleaned up"
    else
        log_error "Backup failed!"
        exit 1
    fi
}

cmd_restore() {
    local backup_file=$1

    if [ -z "$backup_file" ]; then
        log_error "Please specify backup file to restore"
        log_info "Usage: ./manage-pod.sh restore <backup-file.sql.gz>"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    check_pod_exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
    source "$ENV_FILE"

    log_warning "This will overwrite the current database!"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database from $backup_file..."

    if [[ $backup_file == *.gz ]]; then
        gunzip -c "$backup_file" | podman exec -i "${POD_NAME}-db" psql -U "$DB_USER" "$DB_NAME"
    else
        cat "$backup_file" | podman exec -i "${POD_NAME}-db" psql -U "$DB_USER" "$DB_NAME"
    fi

    log_success "Database restored successfully!"
}

cmd_update() {
    log_info "Updating Tiquemax POS System..."

    # Pull latest code if git repo
    if [ -d "../../.git" ]; then
        log_info "Pulling latest code..."
        cd ../..
        git pull
        cd deployment/podman
    fi

    # Rebuild web image
    log_info "Rebuilding web image..."
    cd ../..
    podman build -t tiquemax-web:latest -f Dockerfile.prod .
    cd deployment/podman

    # Restart web containers
    log_info "Restarting web containers..."
    podman restart "${POD_NAME}-web"
    podman restart "${POD_NAME}-celery-worker"
    podman restart "${POD_NAME}-celery-beat"
    podman restart "${POD_NAME}-flower"

    sleep 5

    # Run migrations
    cmd_migrate

    # Collect static files
    cmd_collectstatic

    log_success "System updated successfully!"
}

cmd_remove() {
    log_warning "This will remove the pod and all containers (data in volumes will be preserved)"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Remove cancelled"
        exit 0
    fi

    log_info "Removing pod..."
    podman pod rm -f "$POD_NAME" 2>/dev/null || true
    log_success "Pod removed"
}

cmd_clean() {
    log_warning "This will remove the pod, containers, AND all volumes (all data will be lost!)"
    read -p "Are you ABSOLUTELY sure? Type 'DELETE ALL DATA' to confirm: " -r
    if [[ ! $REPLY == "DELETE ALL DATA" ]]; then
        log_info "Clean cancelled"
        exit 0
    fi

    log_info "Removing pod and volumes..."
    podman pod rm -f "$POD_NAME" 2>/dev/null || true
    podman volume rm tiquemax-postgres-data tiquemax-redis-data tiquemax-static tiquemax-media tiquemax-logs 2>/dev/null || true
    log_success "Pod and volumes removed"
}

cmd_exec() {
    local container=$1
    shift
    local command="$@"

    if [ -z "$container" ]; then
        log_error "Please specify container name"
        log_info "Usage: ./manage-pod.sh exec <container> <command>"
        log_info "Containers: web, db, redis, celery-worker, celery-beat, flower, nginx"
        exit 1
    fi

    check_pod_exists
    local container_name="${POD_NAME}-${container}"

    if [ -z "$command" ]; then
        podman exec -it "$container_name" /bin/sh
    else
        podman exec -it "$container_name" $command
    fi
}

cmd_healthcheck() {
    check_pod_exists
    log_info "Running health checks..."
    echo ""

    # Check web
    echo -n "Web (Django): "
    if podman healthcheck run "${POD_NAME}-web" &>/dev/null; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi

    # Check PostgreSQL
    echo -n "Database (PostgreSQL): "
    if podman healthcheck run "${POD_NAME}-db" &>/dev/null; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi

    # Check Redis
    echo -n "Cache (Redis): "
    if podman healthcheck run "${POD_NAME}-redis" &>/dev/null; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi

    # Check containers are running
    echo -n "Celery Worker: "
    if podman ps --filter name="${POD_NAME}-celery-worker" --filter status=running --quiet | grep -q .; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi

    echo -n "Celery Beat: "
    if podman ps --filter name="${POD_NAME}-celery-beat" --filter status=running --quiet | grep -q .; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi

    echo -n "Flower: "
    if podman ps --filter name="${POD_NAME}-flower" --filter status=running --quiet | grep -q .; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi

    echo -n "Nginx: "
    if podman ps --filter name="${POD_NAME}-nginx" --filter status=running --quiet | grep -q .; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi
}

show_help() {
    echo "Tiquemax POS System - Podman Pod Management"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start                 Start the pod"
    echo "  stop                  Stop the pod"
    echo "  restart               Restart the pod"
    echo "  status                Show pod and container status"
    echo "  logs [service]        Show logs (optionally for specific service)"
    echo "  shell                 Open Django shell"
    echo "  dbshell               Open database shell"
    echo "  migrate               Run database migrations"
    echo "  collectstatic         Collect static files"
    echo "  createsuperuser       Create Django superuser"
    echo "  backup                Create database backup"
    echo "  restore <file>        Restore database from backup"
    echo "  update                Update system (pull code, rebuild, migrate)"
    echo "  remove                Remove pod (keeps volumes)"
    echo "  clean                 Remove pod and volumes (DELETES ALL DATA)"
    echo "  exec <container> [cmd] Execute command in container"
    echo "  healthcheck           Check health of all services"
    echo "  help                  Show this help message"
    echo ""
    echo "Services: web, db, redis, celery-worker, celery-beat, flower, nginx"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs web"
    echo "  $0 backup"
    echo "  $0 restore backups/tiquemax_pod_backup_20231103_120000.sql.gz"
    echo "  $0 exec web python manage.py check"
}

# Main script
case "${1:-help}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs $2
        ;;
    shell)
        cmd_shell
        ;;
    dbshell)
        cmd_dbshell
        ;;
    migrate)
        cmd_migrate
        ;;
    collectstatic)
        cmd_collectstatic
        ;;
    createsuperuser)
        cmd_createsuperuser
        ;;
    backup)
        cmd_backup
        ;;
    restore)
        cmd_restore $2
        ;;
    update)
        cmd_update
        ;;
    remove)
        cmd_remove
        ;;
    clean)
        cmd_clean
        ;;
    exec)
        shift
        cmd_exec "$@"
        ;;
    healthcheck)
        cmd_healthcheck
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
