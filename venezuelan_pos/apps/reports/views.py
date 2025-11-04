from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from .models import SalesReport, OccupancyAnalysis, ReportSchedule
from .serializers import (
    SalesReportSerializer,
    SalesReportCreateSerializer,
    OccupancyAnalysisSerializer,
    OccupancyAnalysisCreateSerializer,
    ReportScheduleSerializer,
    ReportExportSerializer,
    HeatMapDataSerializer
)
from venezuelan_pos.apps.tenants.mixins import TenantViewMixin
import json
import csv
import io


class SalesReportViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """
    ViewSet for sales reports with flexible filtering.
    Provides CRUD operations and export functionality.
    """
    
    queryset = SalesReport.objects.all()
    serializer_class = SalesReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return SalesReportCreateSerializer
        elif self.action == 'export':
            return ReportExportSerializer
        return SalesReportSerializer
    
    def get_queryset(self):
        """Filter queryset by tenant and apply search/filter parameters."""
        queryset = super().get_queryset()
        
        # Apply filters from query parameters
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date range filters
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(period_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(period_end__lte=end_date)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(generated_by__username__icontains=search)
            )
        
        return queryset.select_related('generated_by').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant when creating report."""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """Export report in specified format."""
        report = self.get_object()
        serializer = ReportExportSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        export_format = serializer.validated_data['format']
        include_details = serializer.validated_data['include_details']
        
        try:
            if export_format == 'json':
                return self._export_json(report, include_details)
            elif export_format == 'csv':
                return self._export_csv(report, include_details)
            elif export_format == 'pdf':
                return self._export_pdf(report, include_details)
        except Exception as e:
            return Response(
                {'error': f'Export failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _export_json(self, report, include_details):
        """Export report as JSON."""
        data = {
            'report_id': str(report.id),
            'name': report.name,
            'report_type': report.report_type,
            'period_start': report.period_start.isoformat() if report.period_start else None,
            'period_end': report.period_end.isoformat() if report.period_end else None,
            'total_transactions': report.total_transactions,
            'total_revenue': float(report.total_revenue),
            'total_tickets': report.total_tickets,
            'average_ticket_price': float(report.average_ticket_price),
            'generated_at': report.created_at.isoformat(),
            'generated_by': report.generated_by.get_full_name() if report.generated_by else None
        }
        
        if include_details:
            data['filters'] = report.filters
            data['detailed_data'] = report.detailed_data
        
        response = HttpResponse(
            json.dumps(data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}.json"'
        return response
    
    def _export_csv(self, report, include_details):
        """Export report as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Report ID',
            'Name',
            'Type',
            'Period Start',
            'Period End',
            'Total Transactions',
            'Total Revenue',
            'Total Tickets',
            'Average Ticket Price',
            'Generated At',
            'Generated By'
        ])
        
        # Write data
        writer.writerow([
            str(report.id),
            report.name,
            report.get_report_type_display(),
            report.period_start.strftime('%Y-%m-%d %H:%M:%S') if report.period_start else '',
            report.period_end.strftime('%Y-%m-%d %H:%M:%S') if report.period_end else '',
            report.total_transactions,
            float(report.total_revenue),
            report.total_tickets,
            float(report.average_ticket_price),
            report.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            report.generated_by.get_full_name() if report.generated_by else ''
        ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}.csv"'
        return response
    
    def _export_pdf(self, report, include_details):
        """Export report as PDF."""
        # For now, return a simple text response
        # In a real implementation, you would use a library like ReportLab
        content = f"""
Sales Report: {report.name}
Type: {report.get_report_type_display()}
Period: {report.period_start} to {report.period_end}

Summary:
- Total Transactions: {report.total_transactions}
- Total Revenue: ${report.total_revenue}
- Total Tickets: {report.total_tickets}
- Average Ticket Price: ${report.average_ticket_price}

Generated: {report.created_at}
Generated By: {report.generated_by.get_full_name() if report.generated_by else 'System'}
        """
        
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}.txt"'
        return response
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for reports."""
        queryset = self.get_queryset()
        
        total_reports = queryset.count()
        completed_reports = queryset.filter(status='completed').count()
        failed_reports = queryset.filter(status='failed').count()
        
        # Recent reports (last 30 days)
        recent_date = timezone.now() - timezone.timedelta(days=30)
        recent_reports = queryset.filter(created_at__gte=recent_date).count()
        
        return Response({
            'total_reports': total_reports,
            'completed_reports': completed_reports,
            'failed_reports': failed_reports,
            'pending_reports': total_reports - completed_reports - failed_reports,
            'recent_reports': recent_reports
        })


class OccupancyAnalysisViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """
    ViewSet for occupancy analysis and heat maps.
    Provides zone performance tracking and visualization data.
    """
    
    queryset = OccupancyAnalysis.objects.all()
    serializer_class = OccupancyAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return OccupancyAnalysisCreateSerializer
        elif self.action == 'heat_map':
            return HeatMapDataSerializer
        return OccupancyAnalysisSerializer
    
    def get_queryset(self):
        """Filter queryset by tenant and apply search/filter parameters."""
        queryset = super().get_queryset()
        
        # Apply filters from query parameters
        analysis_type = self.request.query_params.get('analysis_type')
        if analysis_type:
            queryset = queryset.filter(analysis_type=analysis_type)
        
        event_id = self.request.query_params.get('event_id')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        zone_id = self.request.query_params.get('zone_id')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(event__name__icontains=search) |
                Q(zone__name__icontains=search)
            )
        
        return queryset.select_related('event', 'zone', 'generated_by').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant when creating analysis."""
        serializer.save()
    
    @action(detail=False, methods=['post'])
    def heat_map(self, request):
        """Generate heat map data for a zone."""
        serializer = HeatMapDataSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        zone_id = serializer.validated_data['zone_id']
        event_id = serializer.validated_data.get('event_id')
        
        try:
            heat_map_data = self._generate_heat_map_data(zone_id, event_id)
            return Response(heat_map_data)
        except Exception as e:
            return Response(
                {'error': f'Heat map generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_heat_map_data(self, zone_id, event_id=None):
        """Generate heat map data for visualization."""
        from venezuelan_pos.apps.zones.models import Zone
        from venezuelan_pos.apps.events.models import Event
        from .services import ReportService
        
        # Get zone
        try:
            zone = Zone.objects.get(id=zone_id, tenant=self.request.user.tenant)
        except Zone.DoesNotExist:
            return {
                'error': 'Zone not found'
            }
        
        # Get event if specified
        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id, tenant=self.request.user.tenant)
            except Event.DoesNotExist:
                return {
                    'error': 'Event not found'
                }
        
        # Use the enhanced service method
        heat_map_data = ReportService.generate_occupancy_heat_map(zone, event)
        
        return heat_map_data
    
    @action(detail=False, methods=['get'])
    def performance_ranking(self, request):
        """Get performance ranking of zones."""
        event_id = request.query_params.get('event_id')
        limit = request.query_params.get('limit', 10)
        
        try:
            limit = int(limit) if limit else 10
        except ValueError:
            limit = 10
        
        # Use the enhanced service method
        from .services import ReportService
        from venezuelan_pos.apps.events.models import Event
        
        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id, tenant=request.user.tenant)
            except Event.DoesNotExist:
                return Response(
                    {'error': 'Event not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        ranking_data = ReportService.generate_zone_popularity_ranking(
            event=event,
            tenant=request.user.tenant,
            limit=limit
        )
        
        return Response(ranking_data)
    
    @action(detail=False, methods=['post'])
    def zone_metrics(self, request):
        """Get detailed performance metrics for a specific zone."""
        zone_id = request.data.get('zone_id')
        event_id = request.data.get('event_id')
        period_days = request.data.get('period_days', 30)
        
        if not zone_id:
            return Response(
                {'error': 'zone_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            period_days = int(period_days)
        except (ValueError, TypeError):
            period_days = 30
        
        from venezuelan_pos.apps.zones.models import Zone
        from venezuelan_pos.apps.events.models import Event
        from .services import ReportService
        
        try:
            zone = Zone.objects.get(id=zone_id, tenant=request.user.tenant)
        except Zone.DoesNotExist:
            return Response(
                {'error': 'Zone not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id, tenant=request.user.tenant)
            except Event.DoesNotExist:
                return Response(
                    {'error': 'Event not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        metrics = ReportService.calculate_zone_performance_metrics(
            zone=zone,
            event=event,
            period_days=period_days
        )
        
        return Response(metrics)
    
    @action(detail=False, methods=['post'])
    def occupancy_trends(self, request):
        """Get occupancy trends for a zone over time."""
        zone_id = request.data.get('zone_id')
        days = request.data.get('days', 30)
        
        if not zone_id:
            return Response(
                {'error': 'zone_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            days = int(days)
            if days <= 0 or days > 365:
                days = 30
        except (ValueError, TypeError):
            days = 30
        
        from venezuelan_pos.apps.zones.models import Zone
        from .services import ReportService
        
        try:
            zone = Zone.objects.get(id=zone_id, tenant=request.user.tenant)
        except Zone.DoesNotExist:
            return Response(
                {'error': 'Zone not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        trends = ReportService.generate_occupancy_trends(zone=zone, days=days)
        
        return Response(trends)
    
    @action(detail=False, methods=['post'])
    def comparative_analysis(self, request):
        """Generate comparative analysis across multiple zones."""
        zone_ids = request.data.get('zone_ids', [])
        event_id = request.data.get('event_id')
        
        if not zone_ids or not isinstance(zone_ids, list):
            return Response(
                {'error': 'zone_ids must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from venezuelan_pos.apps.zones.models import Zone
        from venezuelan_pos.apps.events.models import Event
        from .services import ReportService
        
        # Get zones
        zones = Zone.objects.filter(
            id__in=zone_ids,
            tenant=request.user.tenant
        )
        
        if not zones.exists():
            return Response(
                {'error': 'No valid zones found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id, tenant=request.user.tenant)
            except Event.DoesNotExist:
                return Response(
                    {'error': 'Event not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        analysis = ReportService.generate_comparative_analysis(zones, event)
        
        return Response(analysis)


class ReportScheduleViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """
    ViewSet for report schedules.
    Provides automated report generation scheduling.
    """
    
    queryset = ReportSchedule.objects.all()
    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset by tenant and apply search/filter parameters."""
        queryset = super().get_queryset()
        
        # Apply filters from query parameters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        frequency = self.request.query_params.get('frequency')
        if frequency:
            queryset = queryset.filter(frequency=frequency)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('created_by').order_by('next_run')
    
    def perform_create(self, serializer):
        """Set tenant and created_by when creating schedule."""
        serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a schedule immediately."""
        schedule = self.get_object()
        
        if not schedule.is_active:
            return Response(
                {'error': 'Schedule is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            report = schedule.execute()
            if report:
                return Response({
                    'message': 'Schedule executed successfully',
                    'report_id': str(report.id)
                })
            else:
                return Response(
                    {'error': 'Schedule execution failed'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'Execution failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a schedule."""
        schedule = self.get_object()
        schedule.status = ReportSchedule.Status.PAUSED
        schedule.save(update_fields=['status'])
        
        return Response({'message': 'Schedule paused'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused schedule."""
        schedule = self.get_object()
        schedule.status = ReportSchedule.Status.ACTIVE
        schedule.save(update_fields=['status'])
        
        return Response({'message': 'Schedule resumed'})
    
    @action(detail=False, methods=['get'])
    def due_schedules(self, request):
        """Get schedules that are due for execution."""
        due_schedules = self.get_queryset().filter(
            status='active',
            next_run__lte=timezone.now()
        )
        
        serializer = self.get_serializer(due_schedules, many=True)
        return Response({
            'count': due_schedules.count(),
            'schedules': serializer.data
        })