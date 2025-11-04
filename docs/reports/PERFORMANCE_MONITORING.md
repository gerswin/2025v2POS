# Venezuelan POS System - Performance Monitoring Guide

This document provides comprehensive guidance on performance monitoring, testing, and optimization for the Venezuelan POS System.

## Overview

The Venezuelan POS System includes a complete performance monitoring stack with:

- **Sentry** - Error tracking and performance monitoring
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visualization dashboards
- **Structured Logging** - Comprehensive application logging
- **Health Checks** - System health monitoring
- **Load Testing** - Performance validation tools

## Quick Start

### 1. Enable Performance Monitoring

Set the following environment variables:

```bash
# Sentry Configuration (optional but recommended)
export SENTRY_DSN="your-sentry-dsn-here"
export SENTRY_ENVIRONMENT="production"
export SENTRY_TRACES_SAMPLE_RATE="0.1"

# Performance Monitoring
export PERFORMANCE_MONITORING_ENABLE_REQUEST_PROFILING="true"
export PERFORMANCE_MONITORING_SLOW_QUERY_THRESHOLD="0.5"

# Prometheus Metrics
export PROMETHEUS_METRICS_EXPORT_PORT="8001"
```

### 2. Start the Application with Monitoring

```bash
# Start Django with metrics export
python manage.py runserver 8000

# In another terminal, start metrics export
python manage.py prometheus_metrics_export --port 8001
```

### 3. Set Up External Monitoring (Optional)

```bash
# Set up Prometheus and Grafana
cd monitoring
./setup_monitoring.sh
./start_monitoring.sh
```

### 4. Run Performance Tests

```bash
# Quick performance benchmark
python manage.py benchmark_performance --iterations 100

# Load testing
cd load_testing
./run_load_tests.sh
```

## Monitoring Components

### 1. Sentry Integration

**Features:**
- Real-time error tracking
- Performance monitoring
- Release tracking
- Custom tags and context

**Configuration:**
```python
# settings.py
SENTRY_DSN = config('SENTRY_DSN', default='')
SENTRY_TRACES_SAMPLE_RATE = 0.1  # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE = 0.1  # 10% profiling
```

**Usage:**
```python
import sentry_sdk

# Add custom context
sentry_sdk.set_tag("tenant_id", tenant.id)
sentry_sdk.set_context("business", {
    "event_id": event.id,
    "ticket_count": ticket_count
})

# Capture custom metrics
sentry_sdk.capture_message("High ticket sales volume", level="info")
```

### 2. Prometheus Metrics

**Business Metrics:**
- `venezuelan_pos_ticket_sales_total` - Total tickets sold
- `venezuelan_pos_revenue_total` - Revenue generated
- `venezuelan_pos_payment_processing_duration_seconds` - Payment processing time
- `venezuelan_pos_stage_transitions_total` - Pricing stage transitions
- `venezuelan_pos_fiscal_series_generated_total` - Fiscal series generated

**System Metrics:**
- `django_http_requests_total` - HTTP requests
- `django_http_requests_latency_seconds` - Request latency
- `django_db_connections_total` - Database connections
- `venezuelan_pos_database_query_duration_seconds` - Database query time
- `venezuelan_pos_cache_operations_total` - Cache operations

**Usage:**
```python
from venezuelan_pos.core.monitoring import BusinessMetrics

# Track ticket sale
BusinessMetrics.track_ticket_sale(
    event_id=str(event.id),
    zone_id=str(zone.id),
    amount=100.50,
    payment_method="credit_card",
    tenant_id=str(tenant.id)
)

# Track payment processing
BusinessMetrics.track_payment_processing(
    payment_method="credit_card",
    amount=100.50,
    success=True,
    duration_ms=250.5
)
```

### 3. Structured Logging

**Configuration:**
```python
import structlog

logger = structlog.get_logger('venezuelan_pos.performance')

# Log with structured data
logger.info(
    "ticket_purchase_completed",
    event_id=event.id,
    customer_id=customer.id,
    amount=total_amount,
    payment_method=payment_method,
    processing_time_ms=processing_time
)
```

**Log Levels:**
- `DEBUG` - Detailed debugging information
- `INFO` - General information and business events
- `WARNING` - Warning conditions and performance issues
- `ERROR` - Error conditions and failures
- `CRITICAL` - Critical errors requiring immediate attention

### 4. Health Checks

**Available Health Checks:**
- Database performance and connectivity
- Cache performance and connectivity
- Redis connection health
- Celery worker availability
- Tenant data integrity
- Fiscal series integrity

**Usage:**
```bash
# Check system health
curl http://localhost:8000/health/

# Detailed health check
python manage.py health_check
```

**Custom Health Checks:**
```python
from health_check.backends import BaseHealthCheckBackend

class CustomHealthCheck(BaseHealthCheckBackend):
    def check_status(self):
        # Your custom health check logic
        pass
```

## Performance Testing

### 1. Benchmark Testing

**Run Performance Benchmarks:**
```bash
# Basic benchmark
python manage.py benchmark_performance

# Extended benchmark with more iterations
python manage.py benchmark_performance --iterations 500 --verbose

# Specific component benchmarks
python manage.py benchmark_performance --component database
python manage.py benchmark_performance --component cache
```

**Benchmark Results:**
- Database operations (simple queries, complex queries, writes)
- Cache operations (reads, writes, hit rates)
- API endpoint response times
- Health check performance

### 2. Load Testing with Artillery.js

**Prerequisites:**
```bash
# Install Artillery.js
npm install -g artillery
```

**Run Load Tests:**
```bash
cd load_testing

# Quick smoke test
./run_load_tests.sh
# Select option 1

# Standard load test
./run_load_tests.sh
# Select option 2

# Stress test
./run_load_tests.sh
# Select option 3
```

**Load Test Scenarios:**
- Health checks (lightweight validation)
- Authentication flows
- Event management operations
- Ticket sales workflows (most critical)
- Reporting and analytics

**Performance Targets:**
- P95 response time: < 500ms
- P99 response time: < 1000ms
- Error rate: < 5%
- Throughput: > 100 RPS

### 3. Django Load Testing

**Run Django-based Load Tests:**
```bash
# Simulate concurrent users
python manage.py load_test --concurrent-users 50 --requests-per-user 100

# Target specific URL
python manage.py load_test --target-url http://localhost:8000 --test-type api
```

## Performance Optimization

### 1. Database Optimization

**Query Optimization:**
```python
# Use select_related for foreign keys
events = Event.objects.select_related('tenant', 'venue').all()

# Use prefetch_related for many-to-many and reverse FKs
events = Event.objects.prefetch_related('zones', 'price_stages').all()

# Use database indexes
class Event(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
```

**Connection Pooling:**
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django_db_pool.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    }
}
```

### 2. Cache Optimization

**Redis Configuration:**
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}
```

**Cache Usage:**
```python
from django.core.cache import cache
from venezuelan_pos.core.monitoring import track_cache_operations

@track_cache_operations('get', 'seat_availability')
def get_seat_availability(zone_id):
    cache_key = f"seat_availability_{zone_id}"
    availability = cache.get(cache_key)
    
    if availability is None:
        availability = calculate_seat_availability(zone_id)
        cache.set(cache_key, availability, timeout=300)
    
    return availability
```

### 3. API Optimization

**Response Optimization:**
```python
# Use pagination
class EventViewSet(viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        return Event.objects.select_related('tenant').prefetch_related('zones')

# Use serializer optimization
class EventSerializer(serializers.ModelSerializer):
    zones = ZoneSerializer(many=True, read_only=True)
    
    class Meta:
        model = Event
        fields = ['id', 'name', 'start_date', 'zones']
```

**Rate Limiting:**
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour'
    }
}
```

## Monitoring Dashboards

### 1. Grafana Dashboards

**Access:** http://localhost:3000 (admin/admin123)

**Key Panels:**
- Request rate and response times
- Error rates and status codes
- Business metrics (ticket sales, revenue)
- Database and cache performance
- System resource usage

### 2. Prometheus Alerts

**Critical Alerts:**
- High response time (P95 > 1s)
- High error rate (> 10%)
- Database connection issues
- Payment processing failures

**Warning Alerts:**
- Moderate response time (P95 > 500ms)
- Moderate error rate (> 5%)
- Low cache hit rate (< 80%)
- No recent ticket sales

### 3. Custom Monitoring

**Add Custom Metrics:**
```python
from prometheus_client import Counter, Histogram

CUSTOM_COUNTER = Counter(
    'venezuelan_pos_custom_events_total',
    'Custom business events',
    ['event_type', 'tenant_id']
)

CUSTOM_HISTOGRAM = Histogram(
    'venezuelan_pos_custom_duration_seconds',
    'Custom operation duration',
    ['operation']
)

# Usage
CUSTOM_COUNTER.labels(event_type='ticket_refund', tenant_id='123').inc()
CUSTOM_HISTOGRAM.labels(operation='seat_selection').observe(0.25)
```

## Troubleshooting

### Common Performance Issues

**1. Slow Database Queries**
```bash
# Check slow queries in logs
grep "slow_query" logs/django.log

# Use Django Silk for query analysis
# Access: http://localhost:8000/silk/
```

**2. High Memory Usage**
```bash
# Monitor memory usage
python manage.py monitor_performance --interval 30

# Check for memory leaks
python manage.py shell
>>> import gc
>>> gc.collect()
```

**3. Cache Issues**
```bash
# Check cache performance
python manage.py cache_stats

# Clear cache if needed
python manage.py clear_caches
```

### Performance Debugging

**1. Enable Query Profiling**
```python
# settings.py
PERFORMANCE_MONITORING = {
    'ENABLE_QUERY_PROFILING': True,
    'SLOW_QUERY_THRESHOLD': 0.1,  # 100ms
}
```

**2. Use Django Silk**
```bash
# Access Silk profiler
http://localhost:8000/silk/

# Profile specific requests
python manage.py silk_profile
```

**3. Monitor Real-time Performance**
```bash
# Continuous monitoring
python manage.py monitor_performance --interval 60

# Performance alerts
tail -f logs/performance.log | grep WARNING
```

## Best Practices

### 1. Monitoring Strategy

- **Monitor business metrics** alongside technical metrics
- **Set up alerts** for critical performance thresholds
- **Use structured logging** for better analysis
- **Regular performance testing** in CI/CD pipeline
- **Monitor user experience** with real user monitoring

### 2. Performance Testing

- **Test early and often** during development
- **Use realistic data volumes** for testing
- **Test different user scenarios** and load patterns
- **Monitor during tests** to identify bottlenecks
- **Establish performance baselines** and track changes

### 3. Optimization Approach

- **Measure first** before optimizing
- **Focus on bottlenecks** with highest impact
- **Optimize database queries** as first priority
- **Use caching strategically** for frequently accessed data
- **Monitor the impact** of optimizations

## Integration with CI/CD

### Performance Testing in Pipeline

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run performance benchmarks
        run: |
          python manage.py benchmark_performance --iterations 50
      
      - name: Performance regression check
        run: |
          python manage.py check_performance_regression
```

### Monitoring Alerts Integration

```python
# Custom management command for CI/CD
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Run performance checks
        results = run_performance_tests()
        
        # Check against thresholds
        if results['p95_response_time'] > 500:
            self.stdout.write(self.style.ERROR('Performance regression detected'))
            sys.exit(1)
        
        self.stdout.write(self.style.SUCCESS('Performance tests passed'))
```

This comprehensive performance monitoring setup ensures that the Venezuelan POS System maintains optimal performance while providing detailed insights into system behavior and business metrics.