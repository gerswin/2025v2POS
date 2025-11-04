#!/bin/bash
# Tiquemax POS System - Deployment Script for Podman
# Usage: ./deploy.sh [start|stop|restart|update|logs|backup|restore]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="tiquemax"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"

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

check_podman() {
    if ! command -v podman &> /dev/null; then
        log_error "Podman is not installed. Please install it first."
        exit 1
    fi
    log_success "Podman is installed"
}

check_compose() {
    if ! command -v podman-compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        log_error "Neither podman-compose nor docker-compose is installed."
        log_info "Install with: pip install podman-compose"
        exit 1
    fi

    # Determine which compose command to use
    if command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman-compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    log_success "Using: $COMPOSE_CMD"
}

check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found!"
        log_info "Copy .env.production.example to $ENV_FILE and configure it."
        exit 1
    fi
    log_success "Environment file found"
}

load_env() {
    if [ -f "$ENV_FILE" ]; then
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    fi
}

create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log_info "Backup directory created/verified"
}

# Deployment functions
deploy_start() {
    log_info "Starting Tiquemax POS System..."

    check_podman
    check_compose
    check_env_file
    load_env
    create_backup_dir

    # Build images
    log_info "Building images..."
    $COMPOSE_CMD -f $COMPOSE_FILE build --no-cache

    # Start services
    log_info "Starting services..."
    $COMPOSE_CMD -f $COMPOSE_FILE up -d

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10

    # Run migrations
    log_info "Running database migrations..."
    $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py migrate --noinput

    # Collect static files
    log_info "Collecting static files..."
    $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py collectstatic --noinput

    # Create superuser if needed
    log_info "Checking for superuser..."
    $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py shell << EOF || true
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print("No superuser found. Please create one manually.")
EOF

    log_success "Tiquemax POS System started successfully!"
    log_info "Access the application at: http://localhost:${HTTP_PORT:-80}"
    log_info "Access Flower (Celery monitoring) at: http://localhost:${FLOWER_PORT:-5555}"
    log_info ""
    log_info "To create a superuser, run:"
    log_info "  $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py createsuperuser"
}

deploy_stop() {
    log_info "Stopping Tiquemax POS System..."
    $COMPOSE_CMD -f $COMPOSE_FILE down
    log_success "System stopped"
}

deploy_restart() {
    log_info "Restarting Tiquemax POS System..."
    deploy_stop
    deploy_start
}

deploy_update() {
    log_info "Updating Tiquemax POS System..."

    # Pull latest code (assumes git repo)
    if [ -d ".git" ]; then
        log_info "Pulling latest code..."
        git pull
    fi

    # Rebuild images
    log_info "Rebuilding images..."
    $COMPOSE_CMD -f $COMPOSE_FILE build --no-cache

    # Stop services
    log_info "Stopping services..."
    $COMPOSE_CMD -f $COMPOSE_FILE down

    # Start services
    log_info "Starting services..."
    $COMPOSE_CMD -f $COMPOSE_FILE up -d

    # Run migrations
    log_info "Running migrations..."
    sleep 5
    $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py migrate --noinput

    # Collect static files
    log_info "Collecting static files..."
    $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py collectstatic --noinput

    log_success "System updated successfully!"
}

show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        log_info "Showing logs for all services..."
        $COMPOSE_CMD -f $COMPOSE_FILE logs -f
    else
        log_info "Showing logs for $service..."
        $COMPOSE_CMD -f $COMPOSE_FILE logs -f $service
    fi
}

backup_database() {
    log_info "Creating database backup..."
    load_env

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/tiquemax_backup_$TIMESTAMP.sql"

    $COMPOSE_CMD -f $COMPOSE_FILE exec -T db pg_dump -U ${DB_USER} ${DB_NAME} > $BACKUP_FILE

    if [ -f "$BACKUP_FILE" ]; then
        # Compress backup
        gzip $BACKUP_FILE
        log_success "Database backup created: ${BACKUP_FILE}.gz"

        # Remove backups older than 30 days
        find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
        log_info "Old backups cleaned up"
    else
        log_error "Backup failed!"
        exit 1
    fi
}

restore_database() {
    local backup_file=$1

    if [ -z "$backup_file" ]; then
        log_error "Please specify backup file to restore"
        log_info "Usage: ./deploy.sh restore <backup-file.sql.gz>"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warning "This will overwrite the current database!"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database from $backup_file..."
    load_env

    # Decompress if needed
    if [[ $backup_file == *.gz ]]; then
        gunzip -c $backup_file | $COMPOSE_CMD -f $COMPOSE_FILE exec -T db psql -U ${DB_USER} ${DB_NAME}
    else
        cat $backup_file | $COMPOSE_CMD -f $COMPOSE_FILE exec -T db psql -U ${DB_USER} ${DB_NAME}
    fi

    log_success "Database restored successfully!"
}

show_status() {
    log_info "Tiquemax POS System Status:"
    $COMPOSE_CMD -f $COMPOSE_FILE ps
}

show_help() {
    echo "Tiquemax POS System - Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start the system"
    echo "  stop        Stop the system"
    echo "  restart     Restart the system"
    echo "  update      Update and restart the system"
    echo "  status      Show system status"
    echo "  logs [svc]  Show logs (optionally for specific service)"
    echo "  backup      Create database backup"
    echo "  restore     Restore database from backup"
    echo "  shell       Open Django shell"
    echo "  dbshell     Open database shell"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs web"
    echo "  $0 backup"
    echo "  $0 restore backups/tiquemax_backup_20231103_120000.sql.gz"
}

open_shell() {
    log_info "Opening Django shell..."
    $COMPOSE_CMD -f $COMPOSE_FILE exec web python manage.py shell
}

open_dbshell() {
    log_info "Opening database shell..."
    load_env
    $COMPOSE_CMD -f $COMPOSE_FILE exec db psql -U ${DB_USER} ${DB_NAME}
}

# Main script
case "${1:-help}" in
    start)
        deploy_start
        ;;
    stop)
        deploy_stop
        ;;
    restart)
        deploy_restart
        ;;
    update)
        deploy_update
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs $2
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database $2
        ;;
    shell)
        open_shell
        ;;
    dbshell)
        open_dbshell
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
