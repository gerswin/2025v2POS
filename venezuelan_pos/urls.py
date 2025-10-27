"""
URL configuration for venezuelan_pos project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Admin site configuration
admin.site.site_header = "Venezuelan POS System"
admin.site.site_title = "Venezuelan POS Admin"
admin.site.index_title = "Welcome to Venezuelan POS Administration"

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health Checks
    path('health/', include('health_check.urls')),
    
    # Monitoring
    path('metrics/', include('django_prometheus.urls')),
    
    # API v1
    path('api/v1/auth/', include('venezuelan_pos.apps.authentication.urls')),
    path('api/v1/events/', include('venezuelan_pos.apps.events.urls')),
    path('api/v1/', include(('venezuelan_pos.apps.zones.urls', 'zones'), namespace='zones_api')),
    path('api/v1/customers/', include('venezuelan_pos.apps.customers.urls')),
    path('api/v1/sales/', include('venezuelan_pos.apps.sales.urls')),
    path('', include('venezuelan_pos.apps.pricing.urls')),
    
    # Internationalization
    path('i18n/', include('django.conf.urls.i18n')),
    
    # Web authentication
    path('auth/', include('venezuelan_pos.apps.authentication.web_urls')),
    
    # Web interfaces
    path('', include('venezuelan_pos.apps.events.web_urls')),
    path('zones/', include(('venezuelan_pos.apps.zones.urls', 'zones'), namespace='zones_web')),
    path('pricing/', include(('venezuelan_pos.apps.pricing.web_urls', 'pricing'), namespace='pricing_web')),
    path('customers/', include(('venezuelan_pos.apps.customers.web_urls', 'customers'), namespace='customers_web')),
    path('sales/', include(('venezuelan_pos.apps.sales.web_urls', 'sales'), namespace='sales_web')),
]

# Development URLs
if settings.DEBUG:
    import debug_toolbar
    
    urlpatterns += [
        # Debug Toolbar
        path('__debug__/', include(debug_toolbar.urls)),
        
        # Silk Profiling
        path('silk/', include('silk.urls', namespace='silk')),
    ]
    
    # Static and Media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
