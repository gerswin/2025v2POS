from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from venezuelan_pos.apps.tenants.mixins import TenantViewMixin
from venezuelan_pos.apps.sales.models import Transaction
from .models import PaymentMethod, PaymentPlan, Payment, PaymentReconciliation
from .serializers import (
    PaymentMethodSerializer, PaymentPlanSerializer, PaymentPlanCreateSerializer,
    PaymentSerializer, PaymentCreateSerializer, PaymentProcessSerializer,
    PaymentReconciliationSerializer, PaymentReconciliationCompleteSerializer,
    PaymentSummarySerializer, PaymentMethodSummarySerializer
)
from .services import PaymentPlanService, PaymentProcessingService, ReservationService
from .fiscal_integration import FiscalCompletionService, FiscalPaymentValidator, FiscalAuditService


class PaymentMethodViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """ViewSet for PaymentMethod model."""
    
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['method_type', 'is_active', 'allows_partial']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']
    
    def get_queryset(self):
        """Get payment methods for current tenant."""
        return PaymentMethod.objects.filter(tenant=self.request.user.tenant)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active payment methods."""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def calculate_fee(self, request, pk=None):
        """Calculate processing fee for given amount."""
        payment_method = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response(
                {'error': 'Amount is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = Decimal(str(amount))
            fee = payment_method.calculate_processing_fee(amount)
            net_amount = amount - fee
            
            return Response({
                'amount': amount,
                'processing_fee': fee,
                'net_amount': net_amount,
                'fee_percentage': payment_method.processing_fee_percentage,
                'fee_fixed': payment_method.processing_fee_fixed
            })
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentPlanViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """ViewSet for PaymentPlan model."""
    
    serializer_class = PaymentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['plan_type', 'status', 'customer']
    search_fields = ['customer__name', 'customer__surname', 'customer__email']
    ordering_fields = ['created_at', 'expires_at', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get payment plans for current tenant."""
        return PaymentPlan.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('transaction', 'customer')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return PaymentPlanCreateSerializer
        return PaymentPlanSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new payment plan."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get transaction
        transaction = get_object_or_404(
            Transaction,
            id=serializer.validated_data['transaction_id'],
            tenant=request.user.tenant
        )
        
        # Check if transaction already has a payment plan
        if hasattr(transaction, 'payment_plan'):
            return Response(
                {'error': 'Transaction already has a payment plan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create payment plan using service
        plan_type = serializer.validated_data['plan_type']
        expires_at = serializer.validated_data.get('expires_at')
        notes = serializer.validated_data.get('notes', '')
        initial_payment_amount = serializer.validated_data.get('initial_payment_amount')
        payment_method = None

        payment_method_id = serializer.validated_data.get('payment_method_id')
        if payment_method_id:
            payment_method = get_object_or_404(
                PaymentMethod,
                id=payment_method_id,
                tenant=request.user.tenant,
                is_active=True
            )
            if not payment_method.allows_partial:
                return Response(
                    {'error': 'Selected payment method does not allow partial payments'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if initial_payment_amount is not None and initial_payment_amount <= Decimal('0.00'):
            initial_payment_amount = None
        
        try:
            if plan_type == PaymentPlan.PlanType.INSTALLMENT:
                installment_count = serializer.validated_data['installment_count']
                payment_plan = PaymentPlanService.create_installment_plan(
                    transaction_obj=transaction,
                    installment_count=installment_count,
                    expires_at=expires_at,
                    notes=notes,
                    initial_payment_amount=initial_payment_amount,
                    initial_payment_method=payment_method
                )
            else:
                payment_plan = PaymentPlanService.create_flexible_plan(
                    transaction_obj=transaction,
                    expires_at=expires_at,
                    notes=notes,
                    initial_payment_amount=initial_payment_amount,
                    initial_payment_method=payment_method
                )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Serialize and return
        response_serializer = PaymentPlanSerializer(payment_plan)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active payment plans."""
        queryset = self.get_queryset().filter(status=PaymentPlan.Status.ACTIVE)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get expired payment plans."""
        queryset = PaymentPlan.objects.expired_plans().filter(
            tenant=request.user.tenant
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        """Manually expire a payment plan."""
        payment_plan = self.get_object()
        
        if not payment_plan.is_active:
            return Response(
                {'error': 'Payment plan is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        PaymentPlanService.expire_payment_plan(payment_plan)
        serializer = self.get_serializer(payment_plan)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a payment plan."""
        payment_plan = self.get_object()
        
        if not payment_plan.is_active:
            return Response(
                {'error': 'Payment plan is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        PaymentPlanService.cancel_payment_plan(payment_plan)
        serializer = self.get_serializer(payment_plan)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def cleanup_expired(self, request):
        """Clean up expired payment plans and reservations."""
        try:
            stats = ReservationService.cleanup_expired_reservations()
            return Response({
                'message': 'Cleanup completed successfully',
                'stats': stats
            })
        except Exception as e:
            return Response(
                {'error': f'Cleanup failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def extend_expiry(self, request, pk=None):
        """Extend payment plan expiry time."""
        payment_plan = self.get_object()
        
        if not payment_plan.is_active:
            return Response(
                {'error': 'Payment plan is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_expiry = request.data.get('expires_at')
        if not new_expiry:
            return Response(
                {'error': 'expires_at is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_expiry = datetime.fromisoformat(new_expiry)
            if new_expiry <= timezone.now():
                return Response(
                    {'error': 'New expiry time must be in the future'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update payment plan expiry
            payment_plan.expires_at = new_expiry
            payment_plan.save(update_fields=['expires_at'])
            
            # Update reservation expiry times
            for reservation in payment_plan.transaction.reserved_tickets.filter(
                status='active'
            ):
                ReservationService.extend_reservation(reservation, new_expiry)
            
            serializer = self.get_serializer(payment_plan)
            return Response(serializer.data)
        
        except (ValueError, ValidationError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """ViewSet for Payment model."""
    
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'payment_method', 'currency', 'payment_plan']
    search_fields = [
        'reference_number', 'external_transaction_id',
        'transaction__fiscal_series', 'transaction__customer__name'
    ]
    ordering_fields = ['created_at', 'amount', 'completed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get payments for current tenant."""
        return Payment.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('transaction', 'payment_method', 'payment_plan')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action in ['mark_completed', 'mark_failed']:
            return PaymentProcessSerializer
        return PaymentSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new payment."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get transaction and payment method
        transaction = get_object_or_404(
            Transaction,
            id=serializer.validated_data['transaction_id'],
            tenant=request.user.tenant
        )
        
        payment_method = get_object_or_404(
            PaymentMethod,
            id=serializer.validated_data['payment_method_id'],
            tenant=request.user.tenant,
            is_active=True
        )
        
        # Create payment using service
        amount = serializer.validated_data['amount']
        
        try:
            payment = PaymentProcessingService.create_payment(
                transaction_obj=transaction,
                payment_method=payment_method,
                amount=amount,
                currency=serializer.validated_data.get('currency', 'USD'),
                exchange_rate=serializer.validated_data.get('exchange_rate', Decimal('1.0000')),
                reference_number=serializer.validated_data.get('reference_number', ''),
                notes=serializer.validated_data.get('notes', '')
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Serialize and return
        response_serializer = PaymentSerializer(payment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark payment as completed."""
        payment = self.get_object()
        
        if payment.status not in [Payment.Status.PENDING, Payment.Status.PROCESSING]:
            return Response(
                {'error': 'Payment cannot be completed in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        PaymentProcessingService.process_payment(
            payment=payment,
            external_transaction_id=serializer.validated_data.get('external_transaction_id'),
            processor_response=serializer.validated_data.get('processor_response')
        )
        
        response_serializer = PaymentSerializer(payment)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_failed(self, request, pk=None):
        """Mark payment as failed."""
        payment = self.get_object()
        
        if payment.status not in [Payment.Status.PENDING, Payment.Status.PROCESSING]:
            return Response(
                {'error': 'Payment cannot be failed in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        PaymentProcessingService.fail_payment(
            payment=payment,
            error_message=serializer.validated_data.get('notes'),
            processor_response=serializer.validated_data.get('processor_response')
        )
        
        response_serializer = PaymentSerializer(payment)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel payment."""
        payment = self.get_object()
        
        try:
            payment.cancel()
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payment summary statistics."""
        queryset = self.get_queryset()
        
        # Apply date filters if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
                queryset = queryset.filter(created_at__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
                queryset = queryset.filter(created_at__lte=end_date)
            except ValueError:
                pass
        
        # Calculate summary statistics
        completed_payments = queryset.filter(status=Payment.Status.COMPLETED)
        
        summary_data = completed_payments.aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id'),
            processing_fees=Sum('processing_fee'),
            net_amount=Sum('net_amount')
        )
        
        # Summary by payment method
        by_method = {}
        for payment_method in PaymentMethod.objects.filter(tenant=request.user.tenant):
            method_payments = completed_payments.filter(payment_method=payment_method)
            method_summary = method_payments.aggregate(
                total_amount=Sum('amount'),
                total_count=Count('id')
            )
            if method_summary['total_count']:
                by_method[payment_method.name] = method_summary
        
        # Summary by status
        by_status = {}
        for status_choice in Payment.Status.choices:
            status_code = status_choice[0]
            status_payments = queryset.filter(status=status_code)
            status_summary = status_payments.aggregate(
                total_amount=Sum('amount'),
                total_count=Count('id')
            )
            if status_summary['total_count']:
                by_status[status_choice[1]] = status_summary
        
        # Summary by currency
        by_currency = {}
        currencies = queryset.values_list('currency', flat=True).distinct()
        for currency in currencies:
            currency_payments = completed_payments.filter(currency=currency)
            currency_summary = currency_payments.aggregate(
                total_amount=Sum('amount'),
                total_count=Count('id')
            )
            if currency_summary['total_count']:
                by_currency[currency] = currency_summary
        
        # Prepare response data
        response_data = {
            'total_amount': summary_data['total_amount'] or Decimal('0.00'),
            'total_count': summary_data['total_count'] or 0,
            'processing_fees': summary_data['processing_fees'] or Decimal('0.00'),
            'net_amount': summary_data['net_amount'] or Decimal('0.00'),
            'by_method': by_method,
            'by_status': by_status,
            'by_currency': by_currency
        }
        
        serializer = PaymentSummarySerializer(response_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Process payment refund."""
        payment = self.get_object()
        
        if not payment.is_completed:
            return Response(
                {'error': 'Can only refund completed payments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund_amount = request.data.get('refund_amount')
        reason = request.data.get('reason', '')
        
        try:
            if refund_amount:
                refund_amount = Decimal(str(refund_amount))
            
            PaymentProcessingService.refund_payment(
                payment=payment,
                refund_amount=refund_amount,
                reason=reason
            )
            
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
        
        except (ValueError, ValidationError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentReconciliationViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """ViewSet for PaymentReconciliation model."""
    
    serializer_class = PaymentReconciliationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'payment_method', 'reconciliation_date']
    search_fields = ['payment_method__name', 'notes']
    ordering_fields = ['reconciliation_date', 'created_at']
    ordering = ['-reconciliation_date', '-created_at']
    
    def get_queryset(self):
        """Get reconciliations for current tenant."""
        return PaymentReconciliation.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('payment_method')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'complete':
            return PaymentReconciliationCompleteSerializer
        return PaymentReconciliationSerializer
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Recalculate system totals for reconciliation."""
        reconciliation = self.get_object()
        
        system_data = reconciliation.calculate_system_totals()
        reconciliation.save()
        
        serializer = self.get_serializer(reconciliation)
        return Response({
            'reconciliation': serializer.data,
            'system_data': system_data
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete reconciliation with external data."""
        reconciliation = self.get_object()
        
        if reconciliation.is_completed:
            return Response(
                {'error': 'Reconciliation is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reconciliation.complete_reconciliation(
            external_total=serializer.validated_data.get('external_total'),
            external_count=serializer.validated_data.get('external_transaction_count'),
            notes=serializer.validated_data.get('notes')
        )
        
        response_serializer = PaymentReconciliationSerializer(reconciliation)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_daily(self, request):
        """Create daily reconciliation for a payment method."""
        payment_method_id = request.data.get('payment_method_id')
        reconciliation_date = request.data.get('reconciliation_date')
        
        if not payment_method_id or not reconciliation_date:
            return Response(
                {'error': 'payment_method_id and reconciliation_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reconciliation_date = datetime.fromisoformat(reconciliation_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_method = get_object_or_404(
            PaymentMethod,
            id=payment_method_id,
            tenant=request.user.tenant
        )
        
        # Check if reconciliation already exists
        existing = PaymentReconciliation.objects.filter(
            tenant=request.user.tenant,
            payment_method=payment_method,
            reconciliation_date=reconciliation_date
        ).first()
        
        if existing:
            return Response(
                {'error': 'Reconciliation already exists for this date and payment method'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create reconciliation
        reconciliation = PaymentReconciliation.create_daily_reconciliation(
            tenant=request.user.tenant,
            payment_method=payment_method,
            reconciliation_date=reconciliation_date
        )
        
        serializer = self.get_serializer(reconciliation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FiscalValidationViewSet(TenantViewMixin, viewsets.ViewSet):
    """ViewSet for fiscal validation and audit operations."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def validate_transaction(self, request):
        """Validate fiscal completion for a specific transaction."""
        transaction_id = request.data.get('transaction_id')
        
        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction_obj = get_object_or_404(
                Transaction,
                id=transaction_id,
                tenant=request.user.tenant
            )
            
            is_valid, message, payment_details = FiscalPaymentValidator.validate_payment_completion(
                transaction_obj
            )
            
            can_generate_series = FiscalPaymentValidator.can_generate_fiscal_series(transaction_obj)
            
            return Response({
                'transaction_id': str(transaction_obj.id),
                'fiscal_series': transaction_obj.fiscal_series,
                'is_valid': is_valid,
                'message': message,
                'can_generate_fiscal_series': can_generate_series,
                'payment_details': payment_details,
                'status': transaction_obj.status
            })
        
        except Exception as e:
            return Response(
                {'error': f'Validation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def complete_transaction(self, request):
        """Manually complete a transaction with fiscal validation."""
        transaction_id = request.data.get('transaction_id')
        
        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction_obj = get_object_or_404(
                Transaction,
                id=transaction_id,
                tenant=request.user.tenant
            )
            
            result = FiscalCompletionService.complete_transaction_with_fiscal_validation(
                transaction_obj
            )
            
            return Response(result)
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Completion failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def audit_transaction(self, request):
        """Get fiscal audit information for a transaction."""
        transaction_id = request.query_params.get('transaction_id')
        
        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction_obj = get_object_or_404(
                Transaction,
                id=transaction_id,
                tenant=request.user.tenant
            )
            
            audit_info = FiscalAuditService.get_fiscal_completion_audit(transaction_obj)
            return Response(audit_info)
        
        except Exception as e:
            return Response(
                {'error': f'Audit failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def validate_integrity(self, request):
        """Validate fiscal integrity across all transactions."""
        try:
            integrity_results = FiscalAuditService.validate_fiscal_integrity(
                tenant=request.user.tenant
            )
            return Response(integrity_results)
        
        except Exception as e:
            return Response(
                {'error': f'Integrity validation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
