from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalesReportViewSet, OccupancyAnalysisViewSet, ReportScheduleViewSet

# Create router for API endpoints
router = DefaultRouter()
router.register(r'sales-reports', SalesReportViewSet, basename='salesreport')
router.register(r'occupancy-analysis', OccupancyAnalysisViewSet, basename='occupancyanalysis')
router.register(r'schedules', ReportScheduleViewSet, basename='reportschedule')

app_name = 'reports'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]