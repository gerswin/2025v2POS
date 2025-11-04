"""
Web views for payment processing interface.
Provides Django template-based interfaces for payment management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from venezuelan_pos.apps.tenants.middleware import TenantRequiredMixin
from venezuelan_pos.apps.sales.models import Transaction
from .models import PaymentMethod, PaymentPlan, Payment, PaymentReconciliation
from venezuelan_pos.apps.events.models import EventConfiguration
from .forms import (
    PaymentMethodForm, PaymentPlanForm, PaymentForm, 
    PaymentReconciliationForm, PaymentSearchForm
)
from .services import PaymentPlanService, PaymentProcessingService, ReservationService
from .fiscal_integration import FiscalAuditService


@login_required
def payment_dashboard(request):
    """Payment processing dashboard."""
    # Get summary statistics
    today = timezone.now().date()
    
    # Payment statistics
    payment_stats = Payment.objects.filter(
        tenant=request.user.tenant,
        created_at__date=today
    ).aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id'),
        completed_count=Count('id', filter=Q(status=Payment.Status.COMPLETED)),
        failed_count=Count('id', filter=Q(status=Payment.Status.FAILED))
    )
    
    # Payment plan statistics
    plan_stats = PaymentPlan.objects.filter(
        tenant=request.user.tenant
    ).aggregate(
        active_count=Count('id', filter=Q(status=PaymentPlan.Status.ACTIVE)),
        completed_count=Count('id', filter=Q(status=PaymentPlan.Status.COMPLETED)),
        expired_count=Count('id', filter=Q(status=PaymentPlan.Status.EXPIRED))
    )
    
    # Recent payments
    recent_payments = Payment.objects.filter(
        tenant=request.user.tenant
    ).select_related('transaction', 'payment_method').order_by('-created_at')[:10]
    
    # Active payment plans
    active_plans = PaymentPlan.objects.filter(
        tenant=request.user.tenant,
        status=PaymentPlan.Status.ACTIVE
    ).select_related('transaction', 'customer').order_by('expires_at')[:10]
    
    # Payment methods
    payment_methods = PaymentMethod.objects.filter(
        tenant=request.user.tenant,
        is_active=True
    ).order_by('sort_order', 'name')
    
    context = {
        'payment_stats': payment_stats,
        'plan_stats': plan_stats,
        'recent_payments': recent_payments,
        'active_plans': active_plans,
        'payment_methods': payment_methods,
        'today': today
    }
    
    return render(request, 'payments/dashboard.html', context)


@login_required
def payment_method_list(request):
    """List payment methods."""
    payment_methods = PaymentMethod.objects.filter(
        tenant=request.user.tenant
    ).order_by('sort_order', 'name')
    
    context = {
        'payment_methods': payment_methods
    }
    
    return render(request, 'payments/payment_method_list.html', context)


@login_required
def payment_method_create(request):
    """Create payment method."""
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.tenant = request.user.tenant
            payment_method.save()
            messages.success(request, 'Payment method created successfully.')
            return redirect('payments_web:payment_method_list')
    else:
        form = PaymentMethodForm()
    
    context = {
        'form': form,
        'title': 'Create Payment Method'
    }
    
    return render(request, 'payments/payment_method_form.html', context)


@login_required
def payment_method_edit(request, pk):
    """Edit payment method."""
    payment_method = get_object_or_404(
        PaymentMethod, 
        pk=pk, 
        tenant=request.user.tenant
    )
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=payment_method)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment method updated successfully.')
            return redirect('payments_web:payment_method_list')
    else:
        form = PaymentMethodForm(instance=payment_method)
    
    context = {
        'form': form,
        'payment_method': payment_method,
        'title': 'Edit Payment Method'
    }
    
    return render(request, 'payments/payment_method_form.html', context)


@login_required
def payment_plan_list(request):
    """List payment plans."""
    # Filter parameters
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    queryset = PaymentPlan.objects.filter(
        tenant=request.user.tenant
    ).select_related('transaction', 'customer')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if search:
        queryset = queryset.filter(
            Q(customer__name__icontains=search) |
            Q(customer__surname__icontains=search) |
            Q(customer__email__icontains=search) |
            Q(transaction__fiscal_series__icontains=search)
        )
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    payment_plans = paginator.get_page(page_number)
    
    context = {
        'payment_plans': payment_plans,
        'status_filter': status_filter,
        'search': search,
        'status_choices': PaymentPlan.Status.choices
    }
    
    return render(request, 'payments/payment_plan_list.html', context)


@login_required
def payment_plan_create(request, transaction_id):
    """Create a new payment plan for a pending transaction."""
    if request.user.is_admin_user:
        transaction_obj = get_object_or_404(
            Transaction.objects.select_related('event', 'customer'),
            pk=transaction_id
        )
    else:
        transaction_obj = get_object_or_404(
            Transaction.objects.select_related('event', 'customer'),
            pk=transaction_id,
            tenant=request.user.tenant
        )
    
    if hasattr(transaction_obj, 'payment_plan'):
        messages.error(request, 'This transaction already has a payment plan.')
        return redirect('payments_web:payment_plan_detail', pk=transaction_obj.payment_plan.pk)
    
    if transaction_obj.status != Transaction.Status.PENDING:
        messages.error(request, 'Only pending transactions can be converted into payment plans.')
        return redirect('sales_web:transaction_detail', transaction_obj.pk)
    
    event_config = EventConfiguration.objects.filter(event=transaction_obj.event).first()
    if not event_config or not event_config.partial_payments_enabled:
        messages.error(request, 'Partial payments are not enabled for this event.')
        return redirect('sales_web:transaction_detail', transaction_obj.pk)
    
    min_down_payment = Decimal('0.00')
    if event_config.min_down_payment_percentage:
        min_down_payment = (transaction_obj.total_amount * (
            Decimal(str(event_config.min_down_payment_percentage)) / Decimal('100')
        )).quantize(Decimal('0.01'))
    
    initial = {}
    if min_down_payment > 0:
        initial['initial_payment_amount'] = min_down_payment
    
    if request.method == 'POST':
        form = PaymentPlanForm(
            request.POST,
            tenant=request.user.tenant,
            transaction=transaction_obj
        )
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                if cleaned['plan_type'] == PaymentPlan.PlanType.INSTALLMENT:
                    payment_plan = PaymentPlanService.create_installment_plan(
                        transaction_obj=transaction_obj,
                        installment_count=cleaned['installment_count'],
                        expires_at=cleaned.get('expires_at'),
                        notes=cleaned.get('notes', ''),
                        initial_payment_amount=cleaned.get('initial_payment_amount'),
                        initial_payment_method=cleaned.get('payment_method')
                    )
                else:
                    payment_plan = PaymentPlanService.create_flexible_plan(
                        transaction_obj=transaction_obj,
                        expires_at=cleaned.get('expires_at'),
                        notes=cleaned.get('notes', ''),
                        initial_payment_amount=cleaned.get('initial_payment_amount'),
                        initial_payment_method=cleaned.get('payment_method')
                    )
                
                messages.success(request, 'Payment plan created successfully.')
                return redirect('payments_web:payment_plan_detail', pk=payment_plan.pk)
            except ValidationError as exc:
                form.add_error(None, exc.message)
    else:
        form = PaymentPlanForm(
            initial=initial,
            tenant=request.user.tenant,
            transaction=transaction_obj
        )
    
    context = {
        'form': form,
        'transaction': transaction_obj,
        'event_config': event_config,
        'min_down_payment': min_down_payment,
        'remaining_balance': transaction_obj.total_amount,
    }
    
    return render(request, 'payments/payment_plan_form.html', context)


@login_required
def payment_plan_detail(request, pk):
    """Payment plan detail view."""
    payment_plan = get_object_or_404(
        PaymentPlan.objects.select_related('transaction', 'customer'),
        pk=pk,
        tenant=request.user.tenant
    )
    
    # Get payments for this plan
    payments = payment_plan.payments.all().order_by('-created_at')
    
    # Get fiscal audit information
    audit_info = FiscalAuditService.get_fiscal_completion_audit(payment_plan.transaction)
    
    context = {
        'payment_plan': payment_plan,
        'payments': payments,
        'audit_info': audit_info
    }
    
    return render(request, 'payments/payment_plan_detail.html', context)


@login_required
@require_http_methods(["POST"])
def extend_payment_plan_expiry(request, pk):
    """Extend payment plan expiry date."""
    payment_plan = get_object_or_404(
        PaymentPlan,
        pk=pk,
        tenant=request.user.tenant
    )

    if payment_plan.status != PaymentPlan.Status.ACTIVE:
        return JsonResponse({
            'success': False,
            'error': 'Only active payment plans can be extended.'
        })

    try:
        # Get new expiry date from request
        new_expiry_str = request.POST.get('new_expiry')
        if not new_expiry_str:
            return JsonResponse({
                'success': False,
                'error': 'New expiry date is required.'
            })

        # Parse the datetime string
        # Expected format: YYYY-MM-DD HH:MM
        new_expiry = datetime.strptime(new_expiry_str, '%Y-%m-%d %H:%M')
        new_expiry = timezone.make_aware(new_expiry)

        # Validate that new expiry is in the future
        if new_expiry <= timezone.now():
            return JsonResponse({
                'success': False,
                'error': 'New expiry date must be in the future.'
            })

        # Update the payment plan
        payment_plan.expires_at = new_expiry
        payment_plan.save(update_fields=['expires_at'])

        # Also extend associated reservations
        reserved_tickets = payment_plan.transaction.reserved_tickets.filter(
            status='active'
        )
        reserved_tickets.update(reserved_until=new_expiry)

        messages.success(
            request,
            f'Payment plan expiry extended to {new_expiry.strftime("%Y-%m-%d %H:%M")}'
        )

        return JsonResponse({
            'success': True,
            'new_expiry': new_expiry.strftime('%Y-%m-%d %H:%M'),
            'message': 'Payment plan expiry extended successfully.'
        })

    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD HH:MM'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error extending expiry: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def cancel_payment_plan(request, pk):
    """Cancel a payment plan and release associated reservations."""
    payment_plan = get_object_or_404(
        PaymentPlan,
        pk=pk,
        tenant=request.user.tenant
    )

    if payment_plan.status != PaymentPlan.Status.ACTIVE:
        return JsonResponse({
            'success': False,
            'error': 'Only active payment plans can be cancelled.'
        })

    try:
        # Use PaymentPlanService to cancel the plan
        PaymentPlanService.cancel_payment_plan(payment_plan)

        messages.success(
            request,
            'Payment plan cancelled successfully. All reserved tickets have been released.'
        )

        return JsonResponse({
            'success': True,
            'message': 'Payment plan cancelled successfully.',
            'redirect_url': request.build_absolute_uri(
                f'/payments/plans/'
            )
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error cancelling payment plan: {str(e)}'
        })


@login_required
def payment_list(request):
    """List payments."""
    # Search form
    form = PaymentSearchForm(request.GET or None)
    
    queryset = Payment.objects.filter(
        tenant=request.user.tenant
    ).select_related('transaction', 'payment_method', 'payment_plan')
    
    if form.is_valid():
        # Apply filters
        if form.cleaned_data.get('status'):
            queryset = queryset.filter(status=form.cleaned_data['status'])
        
        if form.cleaned_data.get('payment_method'):
            queryset = queryset.filter(payment_method=form.cleaned_data['payment_method'])
        
        if form.cleaned_data.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=form.cleaned_data['start_date'])
        
        if form.cleaned_data.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=form.cleaned_data['end_date'])
        
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            queryset = queryset.filter(
                Q(reference_number__icontains=search) |
                Q(external_transaction_id__icontains=search) |
                Q(transaction__fiscal_series__icontains=search) |
                Q(transaction__customer__name__icontains=search) |
                Q(transaction__customer__surname__icontains=search)
            )
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)
    
    context = {
        'payments': payments,
        'form': form
    }
    
    return render(request, 'payments/payment_list.html', context)


@login_required
def payment_detail(request, pk):
    """Payment detail view."""
    payment = get_object_or_404(
        Payment.objects.select_related('transaction', 'payment_method', 'payment_plan'),
        pk=pk,
        tenant=request.user.tenant
    )
    
    context = {
        'payment': payment
    }
    
    return render(request, 'payments/payment_detail.html', context)


@login_required
def create_payment(request, transaction_id):
    """Create payment for a transaction."""
    transaction_obj = get_object_or_404(
        Transaction,
        pk=transaction_id,
        tenant=request.user.tenant
    )
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            try:
                payment = PaymentProcessingService.create_payment(
                    transaction_obj=transaction_obj,
                    payment_method=form.cleaned_data['payment_method'],
                    amount=form.cleaned_data['amount'],
                    currency=form.cleaned_data.get('currency', 'USD'),
                    reference_number=form.cleaned_data.get('reference_number', ''),
                    notes=form.cleaned_data.get('notes', '')
                )

                messages.success(request, f'Payment created successfully: {payment.id}')
                return redirect('payments_web:payment_detail', pk=payment.pk)
            
            except Exception as e:
                messages.error(request, f'Error creating payment: {str(e)}')
    else:
        # Pre-fill amount if no payment plan
        initial_data = {}
        if not hasattr(transaction_obj, 'payment_plan'):
            initial_data['amount'] = transaction_obj.total_amount
        
        form = PaymentForm(initial=initial_data, tenant=request.user.tenant)
    
    context = {
        'form': form,
        'transaction': transaction_obj,
        'title': 'Create Payment'
    }
    
    return render(request, 'payments/payment_form.html', context)


@login_required
@require_http_methods(["POST"])
def process_payment(request, pk):
    """Process (complete) a payment."""
    payment = get_object_or_404(
        Payment,
        pk=pk,
        tenant=request.user.tenant
    )

    if payment.status not in [Payment.Status.PENDING, Payment.Status.PROCESSING]:
        messages.error(request, 'Payment cannot be processed in current status.')
        return redirect('payments_web:payment_detail', pk=pk)

    try:
        external_id = request.POST.get('external_transaction_id', '')
        notes = request.POST.get('notes', '')

        PaymentProcessingService.process_payment(
            payment=payment,
            external_transaction_id=external_id
        )

        if notes:
            payment.notes = notes
            payment.save(update_fields=['notes'])

        messages.success(request, 'Payment processed successfully.')

    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')

    return redirect('payments_web:payment_detail', pk=pk)


@login_required
def reconciliation_list(request):
    """List payment reconciliations."""
    reconciliations = PaymentReconciliation.objects.filter(
        tenant=request.user.tenant
    ).select_related('payment_method').order_by('-reconciliation_date', '-created_at')
    
    # Pagination
    paginator = Paginator(reconciliations, 25)
    page_number = request.GET.get('page')
    reconciliations = paginator.get_page(page_number)
    
    context = {
        'reconciliations': reconciliations
    }
    
    return render(request, 'payments/reconciliation_list.html', context)


@login_required
def reconciliation_create(request):
    """Create payment reconciliation."""
    if request.method == 'POST':
        form = PaymentReconciliationForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            try:
                reconciliation = PaymentReconciliation.create_daily_reconciliation(
                    tenant=request.user.tenant,
                    payment_method=form.cleaned_data['payment_method'],
                    reconciliation_date=form.cleaned_data['reconciliation_date']
                )

                messages.success(request, 'Reconciliation created successfully.')
                return redirect('payments_web:reconciliation_detail', pk=reconciliation.pk)
            
            except Exception as e:
                messages.error(request, f'Error creating reconciliation: {str(e)}')
    else:
        form = PaymentReconciliationForm(tenant=request.user.tenant)
    
    context = {
        'form': form,
        'title': 'Create Reconciliation'
    }
    
    return render(request, 'payments/reconciliation_form.html', context)


@login_required
def reconciliation_detail(request, pk):
    """Reconciliation detail view."""
    reconciliation = get_object_or_404(
        PaymentReconciliation.objects.select_related('payment_method'),
        pk=pk,
        tenant=request.user.tenant
    )
    
    # Get payments for this reconciliation period
    payments = Payment.objects.filter(
        tenant=request.user.tenant,
        payment_method=reconciliation.payment_method,
        status=Payment.Status.COMPLETED,
        completed_at__range=[reconciliation.start_datetime, reconciliation.end_datetime]
    ).order_by('-completed_at')
    
    context = {
        'reconciliation': reconciliation,
        'payments': payments
    }
    
    return render(request, 'payments/reconciliation_detail.html', context)


@login_required
def fiscal_audit(request):
    """Fiscal audit dashboard."""
    # Get integrity validation results
    integrity_results = FiscalAuditService.validate_fiscal_integrity(
        tenant=request.user.tenant
    )
    
    # Get recent transactions with potential issues
    recent_transactions = Transaction.objects.filter(
        tenant=request.user.tenant,
        status=Transaction.Status.COMPLETED
    ).select_related('customer').order_by('-completed_at')[:20]
    
    context = {
        'integrity_results': integrity_results,
        'recent_transactions': recent_transactions
    }
    
    return render(request, 'payments/fiscal_audit.html', context)


@login_required
def ajax_calculate_fee(request):
    """AJAX endpoint to calculate processing fee."""
    if request.method == 'POST':
        payment_method_id = request.POST.get('payment_method_id')
        amount = request.POST.get('amount')
        
        try:
            payment_method = PaymentMethod.objects.get(
                pk=payment_method_id,
                tenant=request.user.tenant
            )
            
            amount = Decimal(str(amount))
            fee = payment_method.calculate_processing_fee(amount)
            net_amount = amount - fee
            
            return JsonResponse({
                'success': True,
                'processing_fee': str(fee),
                'net_amount': str(net_amount),
                'fee_percentage': str(payment_method.processing_fee_percentage * 100),
                'fee_fixed': str(payment_method.processing_fee_fixed)
            })
        
        except (PaymentMethod.DoesNotExist, ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid payment method or amount'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
@require_http_methods(["POST"])
def cleanup_expired(request):
    """Clean up expired payment plans and reservations."""
    try:
        stats = ReservationService.cleanup_expired_reservations()

        messages.success(
            request,
            f"Cleanup completed: {stats['expired_reservations']} reservations, "
            f"{stats['expired_payment_plans']} payment plans, "
            f"{stats['released_seats']} seats released."
        )

    except Exception as e:
        messages.error(request, f'Cleanup failed: {str(e)}')

    return redirect('payments_web:dashboard')
