"""
API Views for Fiscal Compliance System.
Provides REST endpoints for Venezuelan fiscal compliance operations.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from venezuelan_pos.apps.tenants.mixins import TenantViewMixin
from .models import (
    FiscalSeries, FiscalDay, FiscalReport, AuditLog,
    TaxConfiguration, TaxCalculationHistory
)
from .serializers import (
    FiscalSeriesSerializer, FiscalDaySerializer, FiscalReportSerializer,
    FiscalReportCreateSerializer, AuditLogSerializer, TaxConfigurationSerializer,
    TaxCalculationHistorySerializer, TaxCalculationRequestSerializer,
    TaxCalculationResponseSerializer, FiscalStatusSerializer,
    VoidFiscalSeriesSerializer, CloseFiscalDaySerializer
)
from .services import (
    FiscalSeriesService, FiscalDayService, FiscalReportService,
    TaxCalculationService, FiscalComplianceService
)


class FiscalSeriesViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Fiscal Series management.
    Provides read-only access to fiscal series with void functionality.
    """
    serializer_class = FiscalSeriesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_voided', 'issued_by', 'issued_at']
    search_fields = ['series_number', 'transaction__id']
    ordering = ['-issued_at']
    
    def get_queryset(self):
        return FiscalSeries.objects.filter(
            tenant=self.request.tenant
        ).select_related('transaction', 'issued_by', 'voided_by')
    
    @extend_schema(
        request=VoidFiscalSeriesSerializer,
        responses={200: FiscalSeriesSerializer}
    )
    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Void a fiscal series with audit trail"""
        fiscal_series = self.get_object()
        serializer = VoidFiscalSeriesSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                voided_series = FiscalSeriesService.void_fiscal_series(
                    fiscal_series_id=fiscal_series.id,
                    user=request.user,
                    reason=serializer.validated_data['reason']
                )
                
                response_serializer = FiscalSeriesSerializer(voided_series)
                return Response(response_serializer.data)
                
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FiscalDayViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Fiscal Day management.
    Provides fiscal day operations and closure functionality.
    """
    serializer_class = FiscalDaySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_closed', 'user', 'fiscal_date']
    ordering = ['-fiscal_date']
    
    def get_queryset(self):
        return FiscalDay.objects.filter(
            tenant=self.request.tenant
        ).select_related('user', 'z_report')
    
    @extend_schema(
        responses={200: FiscalDaySerializer}
    )
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current fiscal day for authenticated user"""
        fiscal_day = FiscalDayService.get_current_fiscal_day(
            tenant=self.request.tenant,
            user=request.user
        )
        serializer = FiscalDaySerializer(fiscal_day)
        return Response(serializer.data)
    
    @extend_schema(
        request=CloseFiscalDaySerializer,
        responses={200: FiscalDaySerializer}
    )
    @action(detail=False, methods=['post'])
    def close(self, request):
        """Close current fiscal day and generate Z-Report"""
        serializer = CloseFiscalDaySerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                fiscal_day, z_report = FiscalDayService.close_fiscal_day(
                    tenant=self.request.tenant,
                    user=request.user
                )
                
                response_serializer = FiscalDaySerializer(fiscal_day)
                return Response(response_serializer.data)
                
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FiscalReportViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Fiscal Reports (X and Z Reports).
    Provides report generation and viewing functionality.
    """
    serializer_class = FiscalReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'user', 'fiscal_date']
    search_fields = ['report_number']
    ordering = ['-generated_at']
    
    def get_queryset(self):
        return FiscalReport.objects.filter(
            tenant=self.request.tenant
        ).select_related('user')
    
    @extend_schema(
        request=FiscalReportCreateSerializer,
        responses={201: FiscalReportSerializer}
    )
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate X or Z Report"""
        serializer = FiscalReportCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                report_type = serializer.validated_data['report_type']
                fiscal_date = serializer.validated_data.get('fiscal_date')
                
                if report_type == 'X':
                    report = FiscalReportService.generate_x_report(
                        tenant=self.request.tenant,
                        user=request.user,
                        fiscal_date=fiscal_date
                    )
                else:  # Z Report
                    report = FiscalReportService.generate_z_report(
                        tenant=self.request.tenant,
                        user=request.user,
                        fiscal_date=fiscal_date
                    )
                
                response_serializer = FiscalReportSerializer(report)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuditLogViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Audit Logs.
    Provides read-only access to immutable audit trail.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action_type', 'object_type', 'user']
    search_fields = ['object_id', 'description']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        return AuditLog.objects.filter(
            tenant=self.request.tenant
        ).select_related('user', 'fiscal_series')


class TaxConfigurationViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """
    ViewSet for Tax Configuration management.
    Provides CRUD operations for tax configurations.
    """
    serializer_class = TaxConfigurationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tax_type', 'scope', 'is_active', 'event']
    search_fields = ['name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return TaxConfiguration.objects.filter(
            tenant=self.request.tenant
        ).select_related('event', 'created_by')
    
    def perform_create(self, serializer):
        """Set tenant and created_by when creating tax configuration"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )
    
    @extend_schema(
        request=TaxCalculationRequestSerializer,
        responses={200: TaxCalculationResponseSerializer}
    )
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate taxes for given base amount"""
        serializer = TaxCalculationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                base_amount = serializer.validated_data['base_amount']
                event_id = serializer.validated_data.get('event_id')
                
                event = None
                if event_id:
                    from venezuelan_pos.apps.events.models import Event
                    event = get_object_or_404(Event, id=event_id, tenant=self.request.tenant)
                
                tax_amount, tax_details, _ = TaxCalculationService.calculate_taxes(
                    base_amount=base_amount,
                    tenant=self.request.tenant,
                    event=event,
                    user=request.user
                )
                
                response_data = {
                    'base_amount': base_amount,
                    'tax_amount': tax_amount,
                    'total_amount': base_amount + tax_amount,
                    'tax_details': tax_details
                }
                
                response_serializer = TaxCalculationResponseSerializer(response_data)
                return Response(response_serializer.data)
                
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaxCalculationHistoryViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Tax Calculation History.
    Provides read-only access to tax calculation audit trail.
    """
    serializer_class = TaxCalculationHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tax_configuration', 'transaction', 'calculated_by']
    ordering = ['-calculated_at']
    
    def get_queryset(self):
        return TaxCalculationHistory.objects.filter(
            tenant=self.request.tenant
        ).select_related('transaction', 'tax_configuration', 'calculated_by')


class FiscalComplianceViewSet(TenantViewMixin, viewsets.ViewSet):
    """
    ViewSet for general fiscal compliance operations.
    Provides status checks and validation endpoints.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: FiscalStatusSerializer}
    )
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current fiscal compliance status"""
        try:
            fiscal_status = FiscalComplianceService.get_fiscal_status(
                tenant=self.request.tenant,
                user=request.user
            )
            
            serializer = FiscalStatusSerializer(fiscal_status)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        responses={200: {'type': 'object', 'properties': {'valid': {'type': 'boolean'}}}}
    )
    @action(detail=False, methods=['get'])
    def validate_operations(self, request):
        """Validate that fiscal operations can be performed"""
        try:
            is_valid = FiscalComplianceService.validate_fiscal_day_operations(
                tenant=self.request.tenant,
                user=request.user
            )
            
            return Response({'valid': is_valid})
            
        except ValidationError as e:
            return Response(
                {'valid': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'valid': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )