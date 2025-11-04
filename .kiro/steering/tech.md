# Technology Stack & Development

## Core Technologies

- **Backend**: Django 5.0 with Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Cache**: Redis with django-redis
- **Task Queue**: Celery with Redis broker
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (no framework)
- **Containerization**: Docker & Docker Compose

## Key Libraries & Frameworks

- **API**: djangorestframework, drf-spectacular (OpenAPI docs)
- **Authentication**: djangorestframework-simplejwt
- **Monitoring**: django-silk, django-debug-toolbar, sentry-sdk, django-prometheus
- **Performance**: django-redis, django-db-pool (connection pooling)
- **Validation**: django-phonenumber-field, django-localflavor
- **Notifications**: celery (async processing)
- **Digital Tickets**: cryptography, qrcode, reportlab (PDF generation)
- **Health Checks**: django-health-check
- **Logging**: structlog (structured logging)

## Development Commands

### Setup & Installation
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Compile translations
python manage.py compilemessages

# Run development server
python manage.py runserver
```

### Docker Development
```bash
# Start all services
docker-compose up --build

# Run specific service
docker-compose up web
docker-compose up celery
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test venezuelan_pos.apps.sales

# Run with pytest
pytest

# Run with coverage
pytest --cov=venezuelan_pos
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Database shell
python manage.py dbshell

# Django shell
python manage.py shell
```

### Cache Management
```bash
# Clear all caches
python manage.py clear_caches

# Cache statistics
python manage.py cache_stats
```

### Internationalization
```bash
# Extract translatable strings
python manage.py makemessages -l es
python manage.py makemessages -l en

# Compile translations
python manage.py compilemessages
```

### Production Utilities
```bash
# Collect static files
python manage.py collectstatic

# Create admin user for tenant
python manage.py create_admin_user

# Performance monitoring
python manage.py monitor_performance

# Database optimization
python manage.py optimize_database
```

## Environment Configuration

- **Development**: Uses SQLite, console email backend, debug toolbar enabled
- **Production**: PostgreSQL with connection pooling, Redis caching, Sentry monitoring
- **Docker**: Separate services for web, database, Redis, Celery worker, and Celery beat

## Performance & Monitoring

- **Profiling**: Django Silk for query analysis in development
- **Metrics**: Prometheus metrics with custom business metrics
- **Logging**: Structured logging with JSON format in production
- **Health Checks**: Custom health checks for database, cache, and Celery
- **Error Tracking**: Sentry integration for error monitoring and performance tracking