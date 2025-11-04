"""
URL configuration for Fiscal Compliance API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FiscalSeriesViewSet, FiscalDayViewSet, FiscalReportViewSet,
    AuditLogViewSet, TaxConfigurationViewSet, TaxCalculationHistoryViewSet,
    FiscalComplianceViewSet
)

app_name = 'fiscal'

# API Router
router = DefaultRouter()
router.register(r'series', FiscalSeriesViewSet, basename='fiscalseries')
router.register(r'days', FiscalDayViewSet, basename='fiscalday')
router.register(r'reports', FiscalReportViewSet, basename='fiscalreport')
router.register(r'audit', AuditLogViewSet, basename='auditlog')
router.register(r'tax-configurations', TaxConfigurationViewSet, basename='taxconfiguration')
router.register(r'tax-history', TaxCalculationHistoryViewSet, basename='taxhistory')
router.register(r'compliance', FiscalComplianceViewSet, basename='compliance')

urlpatterns = [
    path('api/', include(router.urls)),
]