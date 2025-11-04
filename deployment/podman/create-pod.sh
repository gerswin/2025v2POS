#!/bin/bash
# Tiquemax POS System - Podman Pod Creation Script
# This script creates a native Podman Pod with all services

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
NETWORK_NAME="tiquemax-net"

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

# Load environment variables
if [ ! -f "$ENV_FILE" ]; then
    log_error "Environment file $ENV_FILE not found!"
    exit 1
fi

source "$ENV_FILE"

log_info "Creating Tiquemax POS Podman Pod..."

# Create pod with exposed ports
log_info "Creating pod: $POD_NAME"
podman pod create \
    --name "$POD_NAME" \
    --hostname tiquemax \
    -p 80:80 \
    -p 443:443 \
    -p 5555:5555 \
    --network bridge

log_success "Pod created: $POD_NAME"

# Create volumes if they don't exist
log_info "Creating volumes..."
podman volume create tiquemax-postgres-data 2>/dev/null || true
podman volume create tiquemax-redis-data 2>/dev/null || true
podman volume create tiquemax-static 2>/dev/null || true
podman volume create tiquemax-media 2>/dev/null || true
podman volume create tiquemax-logs 2>/dev/null || true
log_success "Volumes created"

# 1. PostgreSQL Container
log_info "Creating PostgreSQL container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-db" \
    --env-file "$ENV_FILE" \
    -e POSTGRES_DB="${DB_NAME}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
    -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=en_US.UTF-8" \
    -v tiquemax-postgres-data:/var/lib/postgresql/data:Z \
    -v "$(pwd)/../../docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
    --health-cmd="pg_isready -U ${DB_USER} -d ${DB_NAME}" \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=5 \
    docker.io/library/postgres:15-alpine

log_success "PostgreSQL container created"

# 2. Redis Container
log_info "Creating Redis container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-redis" \
    -v tiquemax-redis-data:/data:Z \
    --health-cmd="redis-cli --no-auth-warning -a ${REDIS_PASSWORD} ping || redis-cli ping" \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=5 \
    docker.io/library/redis:7-alpine \
    redis-server --requirepass "${REDIS_PASSWORD}" --appendonly yes

log_success "Redis container created"

# Wait for database to be ready
log_info "Waiting for PostgreSQL to be ready..."
sleep 10

# Check if we need to build the web image
if ! podman image exists tiquemax-web:latest; then
    log_info "Building web application image..."
    cd ../..
    podman build -t tiquemax-web:latest -f Dockerfile.prod .
    cd deployment/podman
    log_success "Web image built"
fi

# 3. Django Web Application
log_info "Creating Django web container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-web" \
    --env-file "$ENV_FILE" \
    -e DB_HOST=localhost \
    -e REDIS_HOST=localhost \
    -v tiquemax-static:/app/staticfiles:Z \
    -v tiquemax-media:/app/media:Z \
    -v tiquemax-logs:/app/logs:Z \
    --health-cmd="curl -f http://localhost:8000/health/ || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    tiquemax-web:latest

log_success "Django web container created"

# Wait for web to be ready
log_info "Waiting for Django to be ready..."
sleep 15

# Run migrations
log_info "Running database migrations..."
podman exec "${POD_NAME}-web" python manage.py migrate --noinput
log_success "Migrations completed"

# Collect static files
log_info "Collecting static files..."
podman exec "${POD_NAME}-web" python manage.py collectstatic --noinput
log_success "Static files collected"

# 4. Celery Worker
log_info "Creating Celery worker container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-celery-worker" \
    --env-file "$ENV_FILE" \
    -e DB_HOST=localhost \
    -e REDIS_HOST=localhost \
    -v tiquemax-media:/app/media:Z \
    -v tiquemax-logs:/app/logs:Z \
    tiquemax-web:latest \
    celery -A venezuelan_pos worker -l info --concurrency=4

log_success "Celery worker container created"

# 5. Celery Beat
log_info "Creating Celery beat container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-celery-beat" \
    --env-file "$ENV_FILE" \
    -e DB_HOST=localhost \
    -e REDIS_HOST=localhost \
    -v tiquemax-logs:/app/logs:Z \
    tiquemax-web:latest \
    celery -A venezuelan_pos beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

log_success "Celery beat container created"

# 6. Flower (Celery Monitoring)
log_info "Creating Flower container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-flower" \
    --env-file "$ENV_FILE" \
    -e DB_HOST=localhost \
    -e REDIS_HOST=localhost \
    tiquemax-web:latest \
    celery -A venezuelan_pos flower --port=5555 --basic_auth="${FLOWER_USER}:${FLOWER_PASSWORD}"

log_success "Flower container created"

# 7. Nginx Container
log_info "Creating Nginx container..."
podman run -d \
    --pod "$POD_NAME" \
    --name "${POD_NAME}-nginx" \
    -v tiquemax-static:/usr/share/nginx/html/static:ro \
    -v tiquemax-media:/usr/share/nginx/html/media:ro \
    -v "$(pwd)/../../docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
    -v "$(pwd)/../../docker/nginx/conf.d:/etc/nginx/conf.d:ro" \
    docker.io/library/nginx:1.25-alpine

log_success "Nginx container created"

# Display pod status
log_info "Pod Status:"
podman pod ps --filter name="$POD_NAME"

echo ""
log_info "Container Status:"
podman ps --filter pod="$POD_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
log_success "Tiquemax POS Pod created successfully!"
echo ""
log_info "Access URLs:"
echo "  - Application: http://localhost"
echo "  - Admin Panel: http://localhost/admin/"
echo "  - API: http://localhost/api/"
echo "  - Flower: http://localhost:5555"
echo ""
log_info "To create a superuser, run:"
echo "  podman exec -it ${POD_NAME}-web python manage.py createsuperuser"
echo ""
log_info "Management commands:"
echo "  - View logs: podman pod logs -f $POD_NAME"
echo "  - Stop pod: podman pod stop $POD_NAME"
echo "  - Start pod: podman pod start $POD_NAME"
echo "  - Remove pod: podman pod rm -f $POD_NAME"
