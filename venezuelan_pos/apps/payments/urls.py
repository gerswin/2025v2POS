from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentMethodViewSet, PaymentPlanViewSet, 
    PaymentViewSet, PaymentReconciliationViewSet, FiscalValidationViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'methods', PaymentMethodViewSet, basename='paymentmethod')
router.register(r'plans', PaymentPlanViewSet, basename='paymentplan')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'reconciliations', PaymentReconciliationViewSet, basename='paymentreconciliation')
router.register(r'fiscal', FiscalValidationViewSet, basename='fiscalvalidation')

app_name = 'payments'

urlpatterns = [
    path('api/v1/payments/', include(router.urls)),
]