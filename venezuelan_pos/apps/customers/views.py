from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Customer, CustomerPreferences
from .serializers import (
    CustomerSerializer,
    CustomerCreateSerializer,
    CustomerUpdateSerializer,
    CustomerPreferencesSerializer,
    CustomerSearchSerializer,
    CustomerLookupSerializer,
    CustomerSummarySerializer,
)


class CustomerListCreateView(generics.ListCreateAPIView):
    """
    List customers or create a new customer.
    
    GET: Returns paginated list of customers for the current tenant.
    POST: Creates a new customer with optional preferences.
    """
    
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'surname', 'phone', 'email', 'identification']
    ordering_fields = ['name', 'surname', 'created_at', 'updated_at']
    ordering = ['surname', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.request.method == 'POST':
            return CustomerCreateSerializer
        return CustomerSummarySerializer
    
    def perform_create(self, serializer):
        """Set tenant when creating customer."""
        # Get tenant from user or middleware
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant:
            from venezuelan_pos.apps.tenants.middleware import get_current_tenant
            tenant = get_current_tenant()
        
        serializer.save(tenant=tenant)
    
    @extend_schema(
        summary="List customers",
        description="Get paginated list of customers for the current tenant",
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search by name, surname, phone, email, or identification'
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active status'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by: name, surname, created_at, updated_at'
            ),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create customer",
        description="Create a new customer with optional communication preferences",
        request=CustomerCreateSerializer,
        responses={201: CustomerSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a customer.
    
    GET: Returns detailed customer information including preferences.
    PUT/PATCH: Updates customer information and preferences.
    DELETE: Soft deletes the customer (sets is_active=False).
    """
    
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.request.method in ['PUT', 'PATCH']:
            return CustomerUpdateSerializer
        return CustomerSerializer
    
    @extend_schema(
        summary="Get customer details",
        description="Retrieve detailed customer information including preferences"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update customer",
        description="Update customer information and communication preferences",
        request=CustomerUpdateSerializer,
        responses={200: CustomerSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update customer",
        description="Partially update customer information and communication preferences",
        request=CustomerUpdateSerializer,
        responses={200: CustomerSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete customer",
        description="Soft delete customer (sets is_active=False)"
    )
    def delete(self, request, *args, **kwargs):
        """Soft delete customer by setting is_active=False."""
        customer = self.get_object()
        customer.is_active = False
        customer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomerPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update customer communication preferences.
    
    GET: Returns customer's communication preferences.
    PUT/PATCH: Updates customer's communication preferences.
    """
    
    queryset = CustomerPreferences.objects.all()
    serializer_class = CustomerPreferencesSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'customer_id'
    lookup_url_kwarg = 'customer_id'
    
    def get_object(self):
        """Get preferences by customer ID."""
        customer_id = self.kwargs['customer_id']
        try:
            customer = Customer.objects.get(id=customer_id)
            return customer.preferences
        except Customer.DoesNotExist:
            from django.http import Http404
            raise Http404("Customer not found")
    
    @extend_schema(
        summary="Get customer preferences",
        description="Retrieve customer's communication preferences"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update customer preferences",
        description="Update customer's communication preferences",
        request=CustomerPreferencesSerializer,
        responses={200: CustomerPreferencesSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update customer preferences",
        description="Partially update customer's communication preferences",
        request=CustomerPreferencesSerializer,
        responses={200: CustomerPreferencesSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


@extend_schema(
    summary="Search customers",
    description="Search customers by name, phone, email, or identification",
    request=CustomerSearchSerializer,
    responses={200: CustomerSummarySerializer(many=True)}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def customer_search(request):
    """
    Search customers by query string.
    
    POST: Search customers by name, phone, email, or identification.
    """
    serializer = CustomerSearchSerializer(data=request.data)
    if serializer.is_valid():
        query = serializer.validated_data['query']
        customers = Customer.objects.search(query)
        
        # Paginate results
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginated_customers = paginator.paginate_queryset(customers, request)
        
        result_serializer = CustomerSummarySerializer(paginated_customers, many=True)
        return paginator.get_paginated_response(result_serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Lookup customer by identification",
    description="Find customer by Venezuelan identification number (cédula)",
    request=CustomerLookupSerializer,
    responses={
        200: CustomerSerializer,
        404: OpenApiTypes.OBJECT
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def customer_lookup(request):
    """
    Lookup customer by identification number.
    
    POST: Find customer by Venezuelan cédula.
    """
    serializer = CustomerLookupSerializer(data=request.data)
    if serializer.is_valid():
        identification = serializer.validated_data['identification']
        
        try:
            customer = Customer.objects.by_identification(identification).first()
            if customer:
                result_serializer = CustomerSerializer(customer)
                return Response(result_serializer.data)
            else:
                return Response(
                    {'detail': 'Customer not found with this identification'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'detail': 'Error looking up customer'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get customer statistics",
    description="Get statistics about customers for the current tenant",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_statistics(request):
    """
    Get customer statistics for the current tenant.
    
    GET: Returns customer counts and statistics.
    """
    from django.db.models import Count, Q
    
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
    
    # Communication preferences statistics
    preferences_stats = CustomerPreferences.objects.aggregate(
        email_enabled=Count('id', filter=Q(email_enabled=True)),
        sms_enabled=Count('id', filter=Q(sms_enabled=True)),
        whatsapp_enabled=Count('id', filter=Q(whatsapp_enabled=True)),
        promotional_enabled=Count('id', filter=Q(promotional_messages=True)),
    )
    
    stats['communication_preferences'] = preferences_stats
    
    return Response(stats)


@extend_schema(
    summary="Quick customer lookup",
    description="Quick lookup customer by phone, email, or identification",
    parameters=[
        OpenApiParameter(
            name='q',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search query (phone, email, or identification)',
            required=True
        )
    ],
    responses={
        200: CustomerSerializer,
        404: OpenApiTypes.OBJECT
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_quick_lookup(request):
    """
    Quick lookup customer by any identifier.
    
    GET: Find customer by phone, email, or identification.
    """
    from .services import CustomerLookupService
    
    query = request.GET.get('q', '').strip()
    if not query:
        return Response(
            {'detail': 'Query parameter "q" is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    customer = CustomerLookupService.quick_lookup(query)
    if customer:
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)
    else:
        return Response(
            {'detail': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Validate customer data for sales",
    description="Validate customer data provided during sales process",
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_customer_data(request):
    """
    Validate customer data for sales process.
    
    POST: Validate customer data and return validation results.
    """
    from .services import CustomerValidationService
    
    validation_result = CustomerValidationService.validate_customer_data_for_sales(request.data)
    return Response(validation_result)


@extend_schema(
    summary="Find or create customer from sales data",
    description="Find existing customer or create new one from sales transaction data",
    request=OpenApiTypes.OBJECT,
    responses={
        200: CustomerSerializer,
        201: CustomerSerializer,
        400: OpenApiTypes.OBJECT
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def find_or_create_customer(request):
    """
    Find existing customer or create new one from sales data.
    
    POST: Find or create customer based on provided data.
    """
    from .services import CustomerService, CustomerValidationService
    
    # Validate data first
    validation_result = CustomerValidationService.validate_customer_data_for_sales(request.data)
    if not validation_result['is_valid']:
        return Response(validation_result, status=status.HTTP_400_BAD_REQUEST)
    
    # Normalize data
    normalized_data = CustomerValidationService.normalize_customer_data(request.data)
    
    # Set tenant context
    tenant = getattr(request.user, 'tenant', None)
    if not tenant:
        from venezuelan_pos.apps.tenants.middleware import get_current_tenant
        tenant = get_current_tenant()
    
    try:
        customer = CustomerService.find_or_create_customer(normalized_data, tenant=tenant)
        serializer = CustomerSerializer(customer)
        
        # Return 201 if customer was created, 200 if found
        status_code = status.HTTP_201_CREATED if customer.created_at == customer.updated_at else status.HTTP_200_OK
        
        return Response(serializer.data, status=status_code)
    
    except Exception as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Get customer purchase history",
    description="Get customer's purchase history for sales interface",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_purchase_history(request, pk):
    """
    Get customer's purchase history.
    
    GET: Returns customer's transaction history.
    """
    from .services import CustomerService
    
    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return Response(
            {'detail': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    history = CustomerService.get_customer_purchase_history(customer)
    return Response({
        'customer': CustomerSummarySerializer(customer).data,
        'purchase_history': history,
        'total_purchases': len(history)
    })


@extend_schema(
    summary="Get customer summary for sales",
    description="Get customer summary information for sales interface",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_sales_summary(request, pk):
    """
    Get customer summary for sales interface.
    
    GET: Returns customer summary with sales-relevant information.
    """
    from .services import CustomerService
    
    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return Response(
            {'detail': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    summary = CustomerService.get_customer_summary_for_sales(customer)
    validation = CustomerService.validate_customer_for_purchase(customer)
    
    return Response({
        'customer': summary,
        'validation': validation
    })