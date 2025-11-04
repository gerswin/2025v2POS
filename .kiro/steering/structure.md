# Project Structure & Architecture

## Django Project Layout

```
venezuelan_pos/                 # Main Django project
├── apps/                      # Django applications
│   ├── tenants/              # Multi-tenant core (users, tenant management)
│   ├── authentication/       # Auth views and web interface
│   ├── events/              # Events and venues management
│   ├── zones/               # Zones and seat mapping
│   ├── pricing/             # Dynamic pricing system
│   ├── customers/           # Customer management
│   ├── sales/               # Sales transactions and cart
│   ├── payments/            # Payment processing
│   ├── notifications/       # Email/SMS/WhatsApp notifications
│   ├── tickets/             # Digital ticket generation
│   ├── fiscal/              # Venezuelan fiscal compliance
│   └── reports/             # Analytics and reporting
├── core/                    # Core utilities and middleware
├── management/              # Custom Django commands
├── settings.py              # Django configuration
└── urls.py                  # Main URL routing
```

## App Architecture Patterns

### Model Structure
- **TenantAwareModel**: Base abstract model for tenant isolation
- **TenantAwareManager**: Custom manager for automatic tenant filtering
- **Optimized Managers**: Performance-optimized querysets in `optimizations.py`

### View Patterns
- **API Views**: DRF ViewSets in `views.py` and `serializers.py`
- **Web Views**: Django template views in `web_views.py`
- **Forms**: Django forms in `forms.py`
- **Templates**: App-specific templates in `templates/{app_name}/`

### File Naming Conventions
- `models.py` - Django models
- `views.py` - DRF API views and serializers
- `web_views.py` - Django template-based views
- `web_urls.py` - URL patterns for web views
- `serializers.py` - DRF serializers (if separate from views.py)
- `forms.py` - Django forms
- `admin.py` - Django admin configuration
- `services.py` - Business logic services
- `tasks.py` - Celery async tasks
- `tests.py` - Unit and integration tests
- `optimizations.py` - Performance-optimized managers and querysets

## Key Architectural Patterns

### Multi-Tenancy
- **Tenant Isolation**: All models inherit from `TenantAwareModel`
- **Middleware**: `TenantMiddleware` sets current tenant context
- **URL Routing**: Subdomain-based tenant routing
- **Data Access**: Automatic tenant filtering via custom managers

### Performance Optimization
- **Database**: Read replicas, connection pooling, query optimization
- **Caching**: Redis-based caching with tenant-aware keys
- **Monitoring**: Custom middleware for performance tracking
- **Async Processing**: Celery for notifications and heavy operations

### Security & Compliance
- **Fiscal Series**: Consecutive numbering with `FiscalSeriesCounter`
- **Offline Support**: Pre-assigned series blocks for offline terminals
- **Audit Logging**: Structured logging for all transactions
- **Data Validation**: Comprehensive model validation and clean methods

## Static Assets Structure

```
static/
├── css/
│   ├── components.css        # Reusable UI components
│   ├── design-system.css     # Design system variables
│   ├── pricing.css          # Pricing-specific styles
│   ├── responsive-improvements.css  # Mobile responsiveness
│   └── zone_form.css        # Zone management styles
└── js/
    ├── components.js         # Reusable JavaScript components
    ├── general_admission.js  # General admission functionality
    ├── reports_charts.js     # Chart and analytics
    ├── responsive-handler.js # Responsive behavior
    ├── stage_monitoring.js   # Pricing stage monitoring
    └── zone_form.js         # Zone management interface
```

## Configuration & Environment

### Settings Organization
- **Single settings.py**: All configuration in one file with environment-based conditionals
- **Environment Variables**: `.env` file for local development
- **Feature Flags**: Environment-based feature toggles (DEBUG, caching, etc.)

### Database Configuration
- **Development**: SQLite with fallback
- **Production**: PostgreSQL with read replicas
- **Connection Pooling**: django-db-pool for production
- **Database Router**: Custom router for read/write splitting

### Monitoring & Logging
- **Structured Logging**: JSON format in production, console in development
- **Performance Monitoring**: Custom middleware with Prometheus metrics
- **Health Checks**: Custom health check backends
- **Error Tracking**: Sentry integration with performance monitoring

## Testing Structure

### Test Organization
- **Unit Tests**: `tests.py` in each app
- **Integration Tests**: `test_*_integration.py` files
- **Performance Tests**: `test_*_performance.py` files
- **Test Markers**: pytest markers for slow, integration, and unit tests

### Test Data Management
- **Setup Scripts**: `setup_test_data.py` for test data creation
- **Cleanup Scripts**: `cleanup_test_data.py` for test data removal
- **Factory Pattern**: factory-boy for model factories

## Development Workflow

### Code Organization
- **Business Logic**: Centralized in `services.py` files
- **API Layer**: Clean separation between web and API views
- **Template Structure**: Consistent template inheritance with `base.html`
- **Form Handling**: Dedicated forms with proper validation

### Performance Considerations
- **Query Optimization**: Use `select_related` and `prefetch_related`
- **Caching Strategy**: Multi-level caching (database, Redis, template)
- **Async Processing**: Celery for notifications and heavy operations
- **Database Indexing**: Comprehensive indexing strategy for tenant-aware queries