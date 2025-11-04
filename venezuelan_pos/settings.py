"""
Django settings for venezuelan_pos project.

Production-ready configuration for Venezuelan POS System.
"""

import os
import logging
from pathlib import Path
from decouple import config
import structlog

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Configuration
SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver').split(',')

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    # REST Framework
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    
    # Development and Optimization
    "django_extensions",
    "silk",
    "debug_toolbar",
    
    # Caching and Performance
    "django_redis",
    
    # Validation and Utilities
    "phonenumber_field",
    "localflavor",
    "corsheaders",
    
    # Health Checks and Monitoring
    "health_check",
    "health_check.db",
    "health_check.cache",
]

# Add Prometheus only if explicitly enabled
ENABLE_PROMETHEUS = config("ENABLE_PROMETHEUS", default=False, cast=bool)
if ENABLE_PROMETHEUS:
    THIRD_PARTY_APPS.append("django_prometheus")

LOCAL_APPS = [
    'venezuelan_pos.core',
    'venezuelan_pos.apps.tenants',
    'venezuelan_pos.apps.authentication',
    'venezuelan_pos.apps.events',
    'venezuelan_pos.apps.zones',
    'venezuelan_pos.apps.pricing',
    'venezuelan_pos.apps.customers',
    'venezuelan_pos.apps.sales',
    'venezuelan_pos.apps.payments',
    'venezuelan_pos.apps.notifications',
    'venezuelan_pos.apps.tickets',
    'venezuelan_pos.apps.fiscal',
    'venezuelan_pos.apps.reports',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # Security
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    
    # CORS
    "corsheaders.middleware.CorsMiddleware",
    
    # Sessions and Common
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # i18n support
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    
    # Authentication
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    
    # Tenant Middleware (after authentication)
    "venezuelan_pos.apps.tenants.middleware.TenantMiddleware",
    
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # Custom Performance and Security Monitoring
    "venezuelan_pos.core.middleware.PerformanceMonitoringMiddleware",
    "venezuelan_pos.core.middleware.SecurityMonitoringMiddleware",
    "venezuelan_pos.core.middleware.CacheMonitoringMiddleware",
    
    # Development Tools (only in DEBUG)
    "silk.middleware.SilkyMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Add Prometheus middleware only if explicitly enabled
if ENABLE_PROMETHEUS:
    MIDDLEWARE.insert(0, "django_prometheus.middleware.PrometheusBeforeMiddleware")
    MIDDLEWARE.append("django_prometheus.middleware.PrometheusAfterMiddleware")

ROOT_URLCONF = "venezuelan_pos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",  # i18n support
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "venezuelan_pos.wsgi.application"


# Database Configuration with Connection Pooling and Read Replicas
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='venezuelan_pos'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
            'sslmode': config('DB_SSL_MODE', default='prefer'),
        },
        'CONN_MAX_AGE': 600,  # Connection pooling with Django's built-in pooling
        'CONN_HEALTH_CHECKS': True,  # Enable connection health checks
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_REPLICA_NAME', default=config('DB_NAME', default='venezuelan_pos')),
        'USER': config('DB_REPLICA_USER', default=config('DB_USER', default='postgres')),
        'PASSWORD': config('DB_REPLICA_PASSWORD', default=config('DB_PASSWORD', default='password')),
        'HOST': config('DB_REPLICA_HOST', default=config('DB_HOST', default='localhost')),
        'PORT': config('DB_REPLICA_PORT', default=config('DB_PORT', default='5432')),
        'OPTIONS': {
            'connect_timeout': 10,
            'sslmode': config('DB_SSL_MODE', default='prefer'),
        },
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
    }
}

# Enhanced database configuration for production with connection pooling
if not DEBUG and config('DB_POOL_ENABLED', default=False, cast=bool):
    # Use django-db-pool for production connection pooling
    DATABASES['default']['ENGINE'] = 'django_db_pool.backends.postgresql'
    DATABASES['default']['OPTIONS'].update({
        'MAX_CONNS': config('DB_MAX_CONNS', default=20, cast=int),
        'MIN_CONNS': config('DB_MIN_CONNS', default=5, cast=int),
    })
    
    DATABASES['replica']['ENGINE'] = 'django_db_pool.backends.postgresql'
    DATABASES['replica']['OPTIONS'].update({
        'MAX_CONNS': config('DB_REPLICA_MAX_CONNS', default=15, cast=int),
        'MIN_CONNS': config('DB_REPLICA_MIN_CONNS', default=3, cast=int),
    })

# Database Router for Read Replicas
DATABASE_ROUTERS = ['venezuelan_pos.core.db_router.DatabaseRouter']

# Use SQLite for development if PostgreSQL is not available
if DEBUG and not config('DB_NAME', default=None):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = 'es'  # Default to Spanish for Venezuelan POS
TIME_ZONE = config('TIME_ZONE', default='America/Caracas')
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Supported languages
LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English'),
]

# Locale paths for translation files
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'tenants.User'

# Login URLs
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Redis Configuration
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
REDIS_CACHE_URL = config('REDIS_CACHE_URL', default='redis://localhost:6379/1')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_CACHE_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'venezuelan_pos',
        'VERSION': 1,
        'TIMEOUT': 300,  # Default 5 minutes
    }
}

# Fallback to dummy cache if Redis is not available in development
if DEBUG:
    try:
        import redis
        # Test Redis connection
        r = redis.Redis.from_url(REDIS_CACHE_URL)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError, ImportError):
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        }

# Session Configuration
if DEBUG:
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/2')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/3')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# JWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Venezuelan POS System API',
    'DESCRIPTION': 'Multi-tenant POS system for event ticket sales with Venezuelan fiscal compliance',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@venezuelanpos.com')

# Notification Configuration
NOTIFICATION_SETTINGS = {
    'SMS_PROVIDER': config('SMS_PROVIDER', default='console'),  # console, twilio, aws_sns
    'WHATSAPP_PROVIDER': config('WHATSAPP_PROVIDER', default='console'),  # console, whatsapp_business
    'DEFAULT_RETRY_DELAY': 60,  # seconds
    'MAX_RETRIES': 3,
}

# Structured Logging Configuration with structlog
timestamper = structlog.processors.TimeStamper(fmt="ISO")

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if not DEBUG else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Standard Django Logging Configuration
# Determine if we're in a containerized environment
IN_CONTAINER = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')

# Logging Configuration - Use console-only logging in containers
if IN_CONTAINER:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'json': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.processors.JSONRenderer(),
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'json' if not DEBUG else 'verbose',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'venezuelan_pos': {
                'handlers': ['console'],
                'level': 'DEBUG' if DEBUG else 'INFO',
                'propagate': False,
            },
        },
    }
else:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
            'json': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.processors.JSONRenderer(),
            },
            'console': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.dev.ConsoleRenderer(colors=DEBUG),
            },
        },
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': BASE_DIR / 'logs' / 'django.log',
                'formatter': 'json' if not DEBUG else 'verbose',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'console' if DEBUG else 'json',
            },
            'performance': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': BASE_DIR / 'logs' / 'performance.log',
                'formatter': 'json',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 3,
            },
            'security': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': BASE_DIR / 'logs' / 'security.log',
                'formatter': 'json',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'loggers': {
            'django': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
            'venezuelan_pos': {
                'handlers': ['file', 'console'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'venezuelan_pos.performance': {
                'handlers': ['performance', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
            'venezuelan_pos.security': {
                'handlers': ['security', 'console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['security'],
                'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Prometheus Metrics Configuration
# Disable automatic port export in development to avoid autoreloader conflicts
# Use environment variable to control Prometheus export
PROMETHEUS_DISABLE_CREATED_SERIES = True  # Disable automatic series creation
if DEBUG:
    # In development, only use URL endpoint, not automatic port export
    os.environ['PROMETHEUS_DISABLE_CREATED_SERIES'] = 'True'
    PROMETHEUS_METRICS_EXPORT_PORT = None
    PROMETHEUS_METRICS_EXPORT_ADDRESS = None
else:
    PROMETHEUS_METRICS_EXPORT_PORT = config('PROMETHEUS_METRICS_EXPORT_PORT', default=8001, cast=int)
    PROMETHEUS_METRICS_EXPORT_ADDRESS = config('PROMETHEUS_METRICS_EXPORT_ADDRESS', default='')

# Custom Prometheus metrics configuration
PROMETHEUS_LATENCY_BUCKETS = (
    0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 25.0, 50.0, 75.0, float("inf")
)

# Enhanced Prometheus Configuration
PROMETHEUS_EXPORT_MIGRATIONS = False  # Don't export migration metrics
PROMETHEUS_MULTIPROC_DIR = config('PROMETHEUS_MULTIPROC_DIR', default='/tmp/prometheus_multiproc')

# Disable automatic metrics export in development to avoid autoreloader conflicts
if DEBUG:
    PROMETHEUS_AUTO_EXPORT = False
else:
    PROMETHEUS_AUTO_EXPORT = True

# Business-specific metrics configuration
PROMETHEUS_BUSINESS_METRICS = {
    'ticket_sales_total': 'Total number of tickets sold',
    'revenue_total': 'Total revenue generated',
    'payment_processing_duration': 'Payment processing time',
    'stage_transitions_total': 'Total number of pricing stage transitions',
    'notification_delivery_duration': 'Notification delivery time',
    'cache_hit_ratio': 'Cache hit ratio percentage',
    'database_query_duration': 'Database query execution time',
    'fiscal_series_generated_total': 'Total fiscal series numbers generated',
}

# Create prometheus multiproc directory
os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)

# Health Check Configuration
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # Fail if disk usage is over 90%
    'MEMORY_MIN': 100,     # Fail if available memory is under 100 MB
}

# Custom Health Checks
HEALTH_CHECK_BACKENDS = [
    'venezuelan_pos.core.health_checks.DatabasePerformanceHealthCheck',
    'venezuelan_pos.core.health_checks.CachePerformanceHealthCheck',
    'venezuelan_pos.core.health_checks.RedisConnectionHealthCheck',
    'venezuelan_pos.core.health_checks.CeleryHealthCheck',
    'venezuelan_pos.core.health_checks.TenantDataIntegrityHealthCheck',
    'venezuelan_pos.core.health_checks.FiscalSeriesIntegrityHealthCheck',
]

# Performance Monitoring Settings
PERFORMANCE_MONITORING = {
    'ENABLE_QUERY_PROFILING': DEBUG,
    'SLOW_QUERY_THRESHOLD': 0.5,  # Log queries slower than 500ms
    'ENABLE_REQUEST_PROFILING': DEBUG,
    'PROFILE_SAMPLE_RATE': 0.1 if not DEBUG else 1.0,
}

# Sentry Configuration for Error Tracking and Performance Monitoring
SENTRY_DSN = config('SENTRY_DSN', default='')
SENTRY_ENVIRONMENT = config('SENTRY_ENVIRONMENT', default='development')
SENTRY_TRACES_SAMPLE_RATE = config('SENTRY_TRACES_SAMPLE_RATE', default=0.1, cast=float)
SENTRY_PROFILES_SAMPLE_RATE = config('SENTRY_PROFILES_SAMPLE_RATE', default=0.1, cast=float)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.threading import ThreadingIntegration
    
    # Configure logging integration
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        integrations=[
            DjangoIntegration(
                auto_enabling=True,
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
            ThreadingIntegration(propagate_hub=True),
            sentry_logging,
        ],
        # Performance Monitoring
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        
        # Error Filtering and Custom Tags
        before_send=lambda event, hint: event if not DEBUG else None,
        before_send_transaction=lambda event, hint: event if not DEBUG else None,
        
        # Additional Options
        send_default_pii=False,  # Don't send PII for privacy
        attach_stacktrace=True,
        max_breadcrumbs=50,
        
        # Release tracking
        release=config('SENTRY_RELEASE', default=None),
        
        # Custom tags for better filtering
        tags={
            'component': 'venezuelan_pos',
            'environment': SENTRY_ENVIRONMENT,
        },
        
        # Performance thresholds
        _experiments={
            'profiles_sample_rate': SENTRY_PROFILES_SAMPLE_RATE,
        },
    )

# Development Settings
if DEBUG:
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    # Debug Toolbar Configuration
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }
    
    # Django Silk Configuration for Query Profiling
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_PYTHON_PROFILER_RESULT_PATH = BASE_DIR / 'profiles'
    SILKY_INTERCEPT_PERCENT = 100  # Profile 100% of requests in development
    SILKY_MAX_REQUEST_BODY_SIZE = 1024 * 1024  # 1MB
    SILKY_MAX_RESPONSE_BODY_SIZE = 1024 * 1024  # 1MB
    SILKY_META = True
    SILKY_ANALYZE_QUERIES = True
    
    # Create profiles directory
    os.makedirs(SILKY_PYTHON_PROFILER_RESULT_PATH, exist_ok=True)

# Currency Configuration
DEFAULT_CURRENCY = config('DEFAULT_CURRENCY', default='USD')

# Digital Tickets Configuration
TICKET_ENCRYPTION_KEY = config('TICKET_ENCRYPTION_KEY', default=None)
if not TICKET_ENCRYPTION_KEY and DEBUG:
    # Generate a key for development (should be set in production)
    try:
        from cryptography.fernet import Fernet
        TICKET_ENCRYPTION_KEY = Fernet.generate_key().decode()
    except ImportError:
        # Fallback if cryptography is not installed
        TICKET_ENCRYPTION_KEY = 'development-key-not-secure'

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/2')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/3')

# Celery Task Configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Beat Schedule for Periodic Tasks
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-cart-locks': {
        'task': 'venezuelan_pos.apps.sales.tasks.cleanup_expired_cart_locks',
        'schedule': 300.0,  # Every 5 minutes
        'options': {
            'expires': 60,  # Task expires after 1 minute if not executed
        },
    },
    'cleanup-expired-reservations': {
        'task': 'venezuelan_pos.apps.sales.tasks.cleanup_expired_reservations',
        'schedule': 600.0,  # Every 10 minutes
        'options': {
            'expires': 120,  # Task expires after 2 minutes if not executed
        },
    },
}

# Cart Lock Configuration
CART_LOCK_DURATION_MINUTES = config('CART_LOCK_DURATION_MINUTES', default=15, cast=int)
CART_LOCK_CLEANUP_INTERVAL = config('CART_LOCK_CLEANUP_INTERVAL', default=5, cast=int)
CART_LOCK_WARNING_MINUTES = config('CART_LOCK_WARNING_MINUTES', default=2, cast=int)
MAX_LOCKS_PER_SESSION = config('MAX_LOCKS_PER_SESSION', default=50, cast=int)