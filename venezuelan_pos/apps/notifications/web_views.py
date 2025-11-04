"""
Web views for notification management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import NotificationTemplate, NotificationLog, NotificationPreference
from .forms import NotificationTemplateForm, NotificationPreferenceForm, SendNotificationForm
from .services import NotificationService


@login_required
def notification_dashboard(request):
    """Notification management dashboard."""
    tenant = request.user.tenant
    
    # Get recent notification logs
    recent_logs = NotificationLog.objects.filter(
        tenant=tenant
    ).select_related('template', 'customer').order_by('-created_at')[:10]
    
    # Get statistics
    stats = NotificationService.get_notification_stats(tenant, days=7)
    
    # Get template counts
    template_stats = NotificationTemplate.objects.filter(
        tenant=tenant
    ).values('template_type').annotate(count=Count('id'))
    
    context = {
        'recent_logs': recent_logs,
        'stats': stats,
        'template_stats': template_stats,
    }
    
    return render(request, 'notifications/dashboard.html', context)


@login_required
def template_list(request):
    """List notification templates."""
    tenant = request.user.tenant
    
    templates = NotificationTemplate.objects.filter(tenant=tenant)
    
    # Filter by type if specified
    template_type = request.GET.get('type')
    if template_type:
        templates = templates.filter(template_type=template_type)
    
    # Search
    search = request.GET.get('search')
    if search:
        templates = templates.filter(
            Q(name__icontains=search) |
            Q(subject__icontains=search) |
            Q(content__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'template_type': template_type,
        'search': search,
    }
    
    return render(request, 'notifications/template_list.html', context)


@login_required
def template_detail(request, template_id):
    """View template details."""
    template = get_object_or_404(
        NotificationTemplate,
        id=template_id,
        tenant=request.user.tenant
    )
    
    # Get recent usage
    recent_logs = NotificationLog.objects.filter(
        template=template
    ).order_by('-created_at')[:10]
    
    context = {
        'template': template,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'notifications/template_detail.html', context)


@login_required
def template_create(request):
    """Create new notification template."""
    if request.method == 'POST':
        form = NotificationTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.tenant = request.user.tenant
            template.save()
            messages.success(request, 'Template created successfully.')
            return redirect('notifications:template_detail', template_id=template.id)
    else:
        form = NotificationTemplateForm()
    
    context = {
        'form': form,
        'title': 'Create Template',
    }
    
    return render(request, 'notifications/template_form.html', context)


@login_required
def template_edit(request, template_id):
    """Edit notification template."""
    template = get_object_or_404(
        NotificationTemplate,
        id=template_id,
        tenant=request.user.tenant
    )
    
    if request.method == 'POST':
        form = NotificationTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template updated successfully.')
            return redirect('notifications:template_detail', template_id=template.id)
    else:
        form = NotificationTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'title': 'Edit Template',
    }
    
    return render(request, 'notifications/template_form.html', context)


@login_required
@require_POST
def template_test(request, template_id):
    """Test a notification template."""
    template = get_object_or_404(
        NotificationTemplate,
        id=template_id,
        tenant=request.user.tenant
    )
    
    recipient = request.POST.get('recipient')
    if not recipient:
        messages.error(request, 'Recipient is required for testing.')
        return redirect('notifications:template_detail', template_id=template.id)
    
    try:
        test_context = {
            'customer': {'name': 'Test', 'surname': 'User'},
            'event': {'name': 'Test Event'},
            'test_message': 'This is a test notification'
        }
        
        log = NotificationService.send_notification(
            tenant=request.user.tenant,
            template_name=template.name,
            recipient=recipient,
            channel=template.template_type,
            context=test_context
        )
        
        messages.success(request, f'Test notification sent successfully. Task ID: {log.task_id}')
        
    except Exception as e:
        messages.error(request, f'Failed to send test notification: {e}')
    
    return redirect('notifications:template_detail', template_id=template.id)


@login_required
def log_list(request):
    """List notification logs."""
    tenant = request.user.tenant
    
    logs = NotificationLog.objects.filter(
        tenant=tenant
    ).select_related('template', 'customer', 'transaction', 'event')
    
    # Filter by channel
    channel = request.GET.get('channel')
    if channel:
        logs = logs.filter(channel=channel)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        logs = logs.filter(status=status)
    
    # Search
    search = request.GET.get('search')
    if search:
        logs = logs.filter(
            Q(recipient__icontains=search) |
            Q(subject__icontains=search) |
            Q(content__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(logs.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'channel': channel,
        'status': status,
        'search': search,
    }
    
    return render(request, 'notifications/log_list.html', context)


@login_required
def log_detail(request, log_id):
    """View notification log details."""
    log = get_object_or_404(
        NotificationLog,
        id=log_id,
        tenant=request.user.tenant
    )
    
    context = {
        'log': log,
    }
    
    return render(request, 'notifications/log_detail.html', context)


@login_required
@require_POST
def log_retry(request, log_id):
    """Retry a failed notification."""
    log = get_object_or_404(
        NotificationLog,
        id=log_id,
        tenant=request.user.tenant
    )
    
    if log.status != 'failed':
        messages.error(request, 'Only failed notifications can be retried.')
        return redirect('notifications:log_detail', log_id=log.id)
    
    try:
        new_log = NotificationService.send_notification(
            tenant=log.tenant,
            template_name=log.template.name if log.template else 'manual',
            recipient=log.recipient,
            channel=log.channel,
            context={},
            customer=log.customer,
            transaction=log.transaction,
            event=log.event
        )
        
        messages.success(request, f'Notification retry queued successfully. New task ID: {new_log.task_id}')
        
    except Exception as e:
        messages.error(request, f'Failed to retry notification: {e}')
    
    return redirect('notifications:log_detail', log_id=log.id)


@login_required
def send_notification(request):
    """Send a manual notification."""
    if request.method == 'POST':
        form = SendNotificationForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            try:
                log = NotificationService.send_notification(
                    tenant=request.user.tenant,
                    template_name=form.cleaned_data['template'].name,
                    recipient=form.cleaned_data['recipient'],
                    channel=form.cleaned_data['template'].template_type,
                    context=form.cleaned_data.get('context', {}),
                    customer=form.cleaned_data.get('customer'),
                    transaction=form.cleaned_data.get('transaction'),
                    event=form.cleaned_data.get('event')
                )
                
                messages.success(request, f'Notification sent successfully. Task ID: {log.task_id}')
                return redirect('notifications:log_detail', log_id=log.id)
                
            except Exception as e:
                messages.error(request, f'Failed to send notification: {e}')
    else:
        form = SendNotificationForm(tenant=request.user.tenant)
    
    context = {
        'form': form,
    }
    
    return render(request, 'notifications/send_form.html', context)


@login_required
def preference_list(request):
    """List customer notification preferences."""
    tenant = request.user.tenant
    
    preferences = NotificationPreference.objects.filter(
        tenant=tenant
    ).select_related('customer')
    
    # Search by customer
    search = request.GET.get('search')
    if search:
        preferences = preferences.filter(
            Q(customer__name__icontains=search) |
            Q(customer__surname__icontains=search) |
            Q(customer__email__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(preferences, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    
    return render(request, 'notifications/preference_list.html', context)


@login_required
def preference_edit(request, preference_id):
    """Edit customer notification preferences."""
    preference = get_object_or_404(
        NotificationPreference,
        id=preference_id,
        tenant=request.user.tenant
    )
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, 'Preferences updated successfully.')
            return redirect('notifications:preference_list')
    else:
        form = NotificationPreferenceForm(instance=preference)
    
    context = {
        'form': form,
        'preference': preference,
    }
    
    return render(request, 'notifications/preference_form.html', context)


@login_required
def analytics(request):
    """Notification analytics and statistics."""
    tenant = request.user.tenant
    
    # Get date range
    days = int(request.GET.get('days', 30))
    
    # Get statistics
    stats = NotificationService.get_notification_stats(tenant, days=days)
    
    # Get daily statistics for chart
    start_date = timezone.now() - timedelta(days=days)
    daily_stats = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        day_logs = NotificationLog.objects.filter(
            tenant=tenant,
            created_at__date=date.date()
        )
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': day_logs.count(),
            'sent': day_logs.filter(status='sent').count(),
            'failed': day_logs.filter(status='failed').count(),
        })
    
    context = {
        'stats': stats,
        'daily_stats': daily_stats,
        'days': days,
    }
    
    return render(request, 'notifications/analytics.html', context)