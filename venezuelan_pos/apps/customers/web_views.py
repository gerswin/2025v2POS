from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _

from .models import Customer, CustomerPreferences
from .forms import (
    CustomerForm, CustomerPreferencesForm, CustomerSearchForm,
    CustomerQuickAddForm, CustomerLookupForm
)
from .services import CustomerService, CustomerLookupService


@login_required
def customer_list(request):
    """List all customers with search and filtering."""
    search_form = CustomerSearchForm(request.GET or None)
    customers = Customer.objects.all()
    
    # Apply search filter
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        is_active = search_form.cleaned_data.get('is_active')
        
        if query:
            customers = Customer.objects.search(query)
        
        if is_active == 'true':
            customers = customers.filter(is_active=True)
        elif is_active == 'false':
            customers = customers.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'customers/customer_list.html', context)


@login_required
def customer_detail(request, pk):
    """Display customer details."""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Get purchase history (will be implemented when sales system is ready)
    purchase_history = CustomerService.get_customer_purchase_history(customer)
    
    # Get customer summary for sales
    sales_summary = CustomerService.get_customer_summary_for_sales(customer)
    validation = CustomerService.validate_customer_for_purchase(customer)
    
    context = {
        'customer': customer,
        'purchase_history': purchase_history,
        'sales_summary': sales_summary,
        'validation': validation,
    }
    
    return render(request, 'customers/customer_detail.html', context)


@login_required
def customer_create(request):
    """Create a new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, _('Customer created successfully.'))
            return redirect('customers_web:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'title': _('Create Customer'),
        'submit_text': _('Create Customer')
    }
    
    return render(request, 'customers/customer_form.html', context)


@login_required
def customer_edit(request, pk):
    """Edit an existing customer."""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, _('Customer updated successfully.'))
            return redirect('customers_web:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'title': _('Edit Customer'),
        'submit_text': _('Update Customer')
    }
    
    return render(request, 'customers/customer_form.html', context)


@login_required
def customer_preferences(request, pk):
    """Edit customer communication preferences."""
    customer = get_object_or_404(Customer, pk=pk)
    
    try:
        preferences = customer.preferences
    except CustomerPreferences.DoesNotExist:
        preferences = CustomerPreferences.create_default_preferences(customer)
    
    if request.method == 'POST':
        form = CustomerPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, _('Customer preferences updated successfully.'))
            return redirect('customers_web:customer_detail', pk=customer.pk)
    else:
        form = CustomerPreferencesForm(instance=preferences)
    
    context = {
        'form': form,
        'customer': customer,
        'preferences': preferences,
    }
    
    return render(request, 'customers/customer_preferences.html', context)


@login_required
def customer_search(request):
    """Search customers with AJAX support."""
    if request.method == 'POST':
        form = CustomerSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            customers = CustomerService.search_customers_for_sales(query, limit=20)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # AJAX request - return JSON
                results = []
                for customer in customers:
                    results.append({
                        'id': str(customer.id),
                        'name': customer.full_name,
                        'email': customer.email or '',
                        'phone': str(customer.phone) if customer.phone else '',
                        'identification': customer.display_identification,
                        'primary_contact': customer.primary_contact,
                    })
                
                return JsonResponse({
                    'success': True,
                    'results': results,
                    'count': len(results)
                })
            else:
                # Regular form submission
                context = {
                    'form': form,
                    'customers': customers,
                    'query': query,
                }
                return render(request, 'customers/customer_search.html', context)
    else:
        form = CustomerSearchForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'customers/customer_search.html', context)


@login_required
def customer_lookup(request):
    """Lookup customer by identification."""
    customer = None
    
    if request.method == 'POST':
        form = CustomerLookupForm(request.POST)
        if form.is_valid():
            identification = form.cleaned_data['identification']
            customer = CustomerLookupService.lookup_by_identification(identification)
            
            if customer:
                messages.success(request, _('Customer found.'))
            else:
                messages.warning(request, _('Customer not found with this identification.'))
    else:
        form = CustomerLookupForm()
    
    context = {
        'form': form,
        'customer': customer,
    }
    
    return render(request, 'customers/customer_lookup.html', context)


@login_required
@require_http_methods(["POST"])
def customer_quick_add(request):
    """Quick add customer (AJAX endpoint for sales interface)."""
    form = CustomerQuickAddForm(request.POST)
    
    if form.is_valid():
        try:
            customer = form.save()
            return JsonResponse({
                'success': True,
                'customer': {
                    'id': str(customer.id),
                    'name': customer.full_name,
                    'email': customer.email or '',
                    'phone': str(customer.phone) if customer.phone else '',
                    'identification': customer.display_identification,
                    'primary_contact': customer.primary_contact,
                }
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


@login_required
def customer_quick_lookup(request):
    """Quick lookup customer (AJAX endpoint)."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({
            'success': False,
            'error': 'Query parameter required'
        })
    
    customer = CustomerLookupService.quick_lookup(query)
    
    if customer:
        return JsonResponse({
            'success': True,
            'customer': {
                'id': str(customer.id),
                'name': customer.full_name,
                'email': customer.email or '',
                'phone': str(customer.phone) if customer.phone else '',
                'identification': customer.display_identification,
                'primary_contact': customer.primary_contact,
                'is_active': customer.is_active,
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Customer not found'
        })


@login_required
def customer_toggle_active(request, pk):
    """Toggle customer active status."""
    customer = get_object_or_404(Customer, pk=pk)
    
    customer.is_active = not customer.is_active
    customer.save()
    
    status = _('activated') if customer.is_active else _('deactivated')
    messages.success(request, _('Customer {} successfully.').format(status))
    
    return redirect('customers_web:customer_detail', pk=customer.pk)


@login_required
def customer_dashboard(request):
    """Customer management dashboard."""
    from django.db.models import Count, Q
    
    # Customer statistics
    stats = {
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(is_active=True).count(),
        'inactive_customers': Customer.objects.filter(is_active=False).count(),
        'customers_with_phone': Customer.objects.filter(phone__isnull=False).count(),
        'customers_with_email': Customer.objects.filter(email__isnull=False).count(),
        'customers_with_identification': Customer.objects.filter(
            identification__isnull=False
        ).exclude(identification='').count(),
    }
    
    # Recent customers
    recent_customers = Customer.objects.order_by('-created_at')[:10]
    
    # Communication preferences statistics
    preferences_stats = CustomerPreferences.objects.aggregate(
        email_enabled=Count('id', filter=Q(email_enabled=True)),
        sms_enabled=Count('id', filter=Q(sms_enabled=True)),
        whatsapp_enabled=Count('id', filter=Q(whatsapp_enabled=True)),
        promotional_enabled=Count('id', filter=Q(promotional_messages=True)),
    )
    
    context = {
        'stats': stats,
        'recent_customers': recent_customers,
        'preferences_stats': preferences_stats,
    }
    
    return render(request, 'customers/customer_dashboard.html', context)