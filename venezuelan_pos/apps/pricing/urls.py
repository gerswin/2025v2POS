"""
URL configuration for pricing app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PriceStageViewSet,
    RowPricingViewSet,
    PriceHistoryViewSet,
    PriceCalculationViewSet,
    StageTransitionViewSet
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'stages', PriceStageViewSet, basename='price-stages')
router.register(r'row-pricing', RowPricingViewSet, basename='row-pricing')
router.register(r'history', PriceHistoryViewSet, basename='price-history')
router.register(r'calculations', PriceCalculationViewSet, basename='price-calculations')
router.register(r'transitions', StageTransitionViewSet, basename='stage-transitions')

app_name = 'pricing'

urlpatterns = [
    path('api/v1/pricing/', include(router.urls)),
]