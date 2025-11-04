.PHONY: help build start stop restart update status logs shell dbshell test backup restore clean

# Variables
COMPOSE = podman-compose -f docker-compose.prod.yml
DEPLOY_SCRIPT = ./deployment/scripts/deploy.sh

# Default target
help:
	@echo "Tiquemax POS System - Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev-start       Start development environment"
	@echo "  make dev-stop        Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make build           Build Docker images"
	@echo "  make start           Start production system"
	@echo "  make stop            Stop production system"
	@echo "  make restart         Restart production system"
	@echo "  make update          Update and restart system"
	@echo ""
	@echo "Management:"
	@echo "  make status          Show services status"
	@echo "  make logs            Show logs (all services)"
	@echo "  make logs-web        Show web logs"
	@echo "  make logs-celery     Show celery logs"
	@echo "  make logs-db         Show database logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate         Run database migrations"
	@echo "  make makemigrations  Create new migrations"
	@echo "  make shell           Open Django shell"
	@echo "  make dbshell         Open database shell"
	@echo "  make backup          Create database backup"
	@echo "  make restore         Restore database backup"
	@echo ""
	@echo "Utilities:"
	@echo "  make collectstatic   Collect static files"
	@echo "  make createsuperuser Create Django superuser"
	@echo "  make test            Run tests"
	@echo "  make clean           Clean up containers and volumes"
	@echo ""

# Development
dev-start:
	podman-compose -f docker-compose.yml up -d

dev-stop:
	podman-compose -f docker-compose.yml down

# Production Build & Deploy
build:
	$(COMPOSE) build --no-cache

start:
	$(DEPLOY_SCRIPT) start

stop:
	$(DEPLOY_SCRIPT) stop

restart:
	$(DEPLOY_SCRIPT) restart

update:
	$(DEPLOY_SCRIPT) update

# Status & Logs
status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

logs-web:
	$(COMPOSE) logs -f web

logs-celery:
	$(COMPOSE) logs -f celery_worker

logs-db:
	$(COMPOSE) logs -f db

logs-nginx:
	$(COMPOSE) logs -f nginx

# Database Operations
migrate:
	$(COMPOSE) exec web python manage.py migrate

makemigrations:
	$(COMPOSE) exec web python manage.py makemigrations

shell:
	$(COMPOSE) exec web python manage.py shell

dbshell:
	$(COMPOSE) exec web python manage.py dbshell

backup:
	$(DEPLOY_SCRIPT) backup

restore:
	@echo "Usage: make restore BACKUP_FILE=path/to/backup.sql.gz"
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: BACKUP_FILE not specified"; \
		exit 1; \
	fi
	$(DEPLOY_SCRIPT) restore $(BACKUP_FILE)

# Utilities
collectstatic:
	$(COMPOSE) exec web python manage.py collectstatic --noinput

createsuperuser:
	$(COMPOSE) exec web python manage.py createsuperuser

test:
	$(COMPOSE) exec web python manage.py test

check:
	$(COMPOSE) exec web python manage.py check

# Clean up
clean:
	$(COMPOSE) down -v
	@echo "Cleaned up containers and volumes"

clean-images:
	podman rmi tiquemax_web:latest || true
	@echo "Cleaned up images"

# Health check
health:
	@echo "Checking system health..."
	@curl -f http://localhost/health/ || echo "❌ Web service not responding"
	@curl -f http://localhost:5555 || echo "❌ Flower not responding"

# Quick deploy (for first time setup)
deploy-first-time: build start migrate collectstatic
	@echo ""
	@echo "✓ First time deployment complete!"
	@echo "  Now create a superuser with: make createsuperuser"
	@echo "  Access the system at: http://localhost"
	@echo ""

# Quick update (for updates)
deploy-update: stop build start migrate collectstatic
	@echo ""
	@echo "✓ Update deployment complete!"
	@echo ""
