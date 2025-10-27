"""
Customer management services for integration with sales process.
"""

from typing import Optional, Dict, Any, List
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Customer, CustomerPreferences
from .serializers import CustomerCreateSerializer, CustomerUpdateSerializer


class CustomerService:
    """Service class for customer management operations."""
    
    @staticmethod
    def create_customer_from_sales_data(sales_data: Dict[str, Any], tenant=None) -> Customer:
        """
        Create a customer from sales transaction data.
        
        Args:
            sales_data: Dictionary containing customer information from sales process
                Expected keys: name, surname, phone, email, identification
            tenant: Tenant instance for multi-tenant support
        
        Returns:
            Customer: Created customer instance
        
        Raises:
            ValidationError: If customer data is invalid
        """
        # Extract customer data from sales data
        customer_data = {
            'name': sales_data.get('customer_name', '').strip(),
            'surname': sales_data.get('customer_surname', '').strip(),
            'phone': sales_data.get('customer_phone', ''),
            'email': sales_data.get('customer_email', ''),
            'identification': sales_data.get('customer_identification', ''),
        }
        
        # Remove empty values
        customer_data = {k: v for k, v in customer_data.items() if v}
        
        # Validate required fields
        if not customer_data.get('name') or not customer_data.get('surname'):
            raise ValidationError("Customer name and surname are required")
        
        if not customer_data.get('phone') and not customer_data.get('email'):
            raise ValidationError("Customer must have at least phone or email")
        
        # Create customer using serializer for validation
        serializer = CustomerCreateSerializer(data=customer_data)
        if serializer.is_valid():
            # Use provided tenant or get current tenant
            if not tenant:
                from venezuelan_pos.apps.tenants.middleware import get_current_tenant
                tenant = get_current_tenant()
            
            if tenant:
                return serializer.save(tenant=tenant)
            else:
                return serializer.save()
        else:
            raise ValidationError(serializer.errors)
    
    @staticmethod
    def find_or_create_customer(customer_data: Dict[str, Any], tenant=None) -> Customer:
        """
        Find existing customer or create new one based on identification or contact info.
        
        Args:
            customer_data: Dictionary containing customer information
            tenant: Tenant instance for multi-tenant filtering
        
        Returns:
            Customer: Found or created customer instance
        """
        identification = customer_data.get('customer_identification', '').strip()
        email = customer_data.get('customer_email', '').strip()
        phone = customer_data.get('customer_phone', '').strip()
        
        # Try to find existing customer by identification first
        if identification:
            existing_customer = Customer.objects.by_identification(identification).first()
            if existing_customer:
                # Update customer data if provided
                CustomerService.update_customer_from_sales_data(existing_customer, customer_data)
                return existing_customer
        
        # Try to find by email
        if email:
            try:
                existing_customer = Customer.objects.filter(email=email).first()
                if existing_customer:
                    CustomerService.update_customer_from_sales_data(existing_customer, customer_data)
                    return existing_customer
            except Customer.DoesNotExist:
                pass
        
        # Try to find by phone
        if phone:
            try:
                existing_customer = Customer.objects.filter(phone=phone).first()
                if existing_customer:
                    CustomerService.update_customer_from_sales_data(existing_customer, customer_data)
                    return existing_customer
            except Customer.DoesNotExist:
                pass
        
        # Create new customer if not found
        return CustomerService.create_customer_from_sales_data(customer_data, tenant=tenant)
    
    @staticmethod
    def update_customer_from_sales_data(customer: Customer, sales_data: Dict[str, Any]) -> Customer:
        """
        Update customer information from sales data.
        
        Args:
            customer: Existing customer instance
            sales_data: Dictionary containing updated customer information
        
        Returns:
            Customer: Updated customer instance
        """
        update_data = {}
        
        # Map sales data fields to customer fields
        field_mapping = {
            'customer_name': 'name',
            'customer_surname': 'surname',
            'customer_phone': 'phone',
            'customer_email': 'email',
            'customer_identification': 'identification',
        }
        
        for sales_field, customer_field in field_mapping.items():
            if sales_field in sales_data and sales_data[sales_field]:
                update_data[customer_field] = sales_data[sales_field]
        
        if update_data:
            serializer = CustomerUpdateSerializer(customer, data=update_data, partial=True)
            if serializer.is_valid():
                return serializer.save()
            else:
                raise ValidationError(serializer.errors)
        
        return customer
    
    @staticmethod
    def get_customer_purchase_history(customer: Customer) -> List[Dict[str, Any]]:
        """
        Get customer's purchase history.
        
        Args:
            customer: Customer instance
        
        Returns:
            List of purchase history records
        
        Note:
            This method will be implemented when the sales/transaction models are created.
            For now, it returns an empty list.
        """
        # TODO: Implement when Transaction model is available
        # This will query Transaction.objects.filter(customer=customer)
        return []
    
    @staticmethod
    def validate_customer_for_purchase(customer: Customer) -> Dict[str, Any]:
        """
        Validate customer data for ticket purchase.
        
        Args:
            customer: Customer instance to validate
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check if customer has contact information
        if not customer.phone and not customer.email:
            validation_result['errors'].append(
                "Customer must have at least phone or email for notifications"
            )
            validation_result['is_valid'] = False
        
        # Check if customer is active
        if not customer.is_active:
            validation_result['errors'].append("Customer account is inactive")
            validation_result['is_valid'] = False
        
        # Warnings for missing optional information
        if not customer.identification:
            validation_result['warnings'].append(
                "Customer identification (cédula) not provided"
            )
        
        if customer.phone and not customer.email:
            validation_result['warnings'].append(
                "Customer email not provided - notifications will be sent via SMS only"
            )
        elif customer.email and not customer.phone:
            validation_result['warnings'].append(
                "Customer phone not provided - notifications will be sent via email only"
            )
        
        return validation_result
    
    @staticmethod
    def get_customer_notification_preferences(customer: Customer) -> Dict[str, Any]:
        """
        Get customer's notification preferences for sales process.
        
        Args:
            customer: Customer instance
        
        Returns:
            Dictionary with notification preferences
        """
        try:
            prefs = customer.preferences
            return {
                'email_enabled': prefs.email_enabled and bool(customer.email),
                'sms_enabled': prefs.sms_enabled and bool(customer.phone),
                'whatsapp_enabled': prefs.whatsapp_enabled and bool(customer.phone),
                'purchase_confirmations': prefs.purchase_confirmations,
                'payment_reminders': prefs.payment_reminders,
                'preferred_language': prefs.preferred_language,
                'contact_methods': {
                    'email': customer.email if prefs.email_enabled else None,
                    'phone': str(customer.phone) if prefs.sms_enabled and customer.phone else None,
                    'whatsapp': str(customer.phone) if prefs.whatsapp_enabled and customer.phone else None,
                }
            }
        except CustomerPreferences.DoesNotExist:
            # Create default preferences if they don't exist
            CustomerPreferences.create_default_preferences(customer)
            return CustomerService.get_customer_notification_preferences(customer)
    
    @staticmethod
    def search_customers_for_sales(query: str, limit: int = 10) -> List[Customer]:
        """
        Search customers for sales interface.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
        
        Returns:
            List of matching customers
        """
        if not query or len(query.strip()) < 2:
            return []
        
        return list(Customer.objects.search(query.strip())[:limit])
    
    @staticmethod
    def get_customer_summary_for_sales(customer: Customer) -> Dict[str, Any]:
        """
        Get customer summary information for sales interface.
        
        Args:
            customer: Customer instance
        
        Returns:
            Dictionary with customer summary
        """
        return {
            'id': str(customer.id),
            'full_name': customer.full_name,
            'primary_contact': customer.primary_contact,
            'identification': customer.display_identification,
            'email': customer.email or '',
            'phone': str(customer.phone) if customer.phone else '',
            'is_active': customer.is_active,
            'purchase_count': len(CustomerService.get_customer_purchase_history(customer)),
            'notification_preferences': CustomerService.get_customer_notification_preferences(customer)
        }


class CustomerLookupService:
    """Service for customer lookup operations during sales."""
    
    @staticmethod
    def lookup_by_identification(identification: str) -> Optional[Customer]:
        """
        Lookup customer by identification number.
        
        Args:
            identification: Customer identification (cédula)
        
        Returns:
            Customer instance if found, None otherwise
        """
        if not identification:
            return None
        
        # Normalize identification
        normalized = identification.replace(' ', '').upper()
        return Customer.objects.by_identification(normalized).first()
    
    @staticmethod
    def lookup_by_phone(phone: str) -> Optional[Customer]:
        """
        Lookup customer by phone number.
        
        Args:
            phone: Customer phone number
        
        Returns:
            Customer instance if found, None otherwise
        """
        if not phone:
            return None
        
        try:
            return Customer.objects.filter(phone=phone).first()
        except:
            return None
    
    @staticmethod
    def lookup_by_email(email: str) -> Optional[Customer]:
        """
        Lookup customer by email address.
        
        Args:
            email: Customer email address
        
        Returns:
            Customer instance if found, None otherwise
        """
        if not email:
            return None
        
        try:
            return Customer.objects.filter(email__iexact=email).first()
        except:
            return None
    
    @staticmethod
    def quick_lookup(query: str) -> Optional[Customer]:
        """
        Quick lookup customer by any identifier (phone, email, identification).
        
        Args:
            query: Search query (phone, email, or identification)
        
        Returns:
            Customer instance if found, None otherwise
        """
        if not query:
            return None
        
        query = query.strip()
        
        # Try identification first
        customer = CustomerLookupService.lookup_by_identification(query)
        if customer:
            return customer
        
        # Try email
        if '@' in query:
            customer = CustomerLookupService.lookup_by_email(query)
            if customer:
                return customer
        
        # Try phone
        if query.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            customer = CustomerLookupService.lookup_by_phone(query)
            if customer:
                return customer
        
        return None


class CustomerValidationService:
    """Service for customer data validation during sales."""
    
    @staticmethod
    def validate_customer_data_for_sales(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate customer data provided during sales process.
        
        Args:
            data: Customer data dictionary
        
        Returns:
            Validation result dictionary
        """
        result = {
            'is_valid': True,
            'errors': {},
            'warnings': []
        }
        
        # Required fields
        required_fields = ['customer_name', 'customer_surname']
        for field in required_fields:
            if not data.get(field, '').strip():
                result['errors'][field] = f"{field.replace('customer_', '').title()} is required"
                result['is_valid'] = False
        
        # At least one contact method required
        phone = data.get('customer_phone', '').strip()
        email = data.get('customer_email', '').strip()
        
        if not phone and not email:
            result['errors']['contact'] = "At least phone or email is required"
            result['is_valid'] = False
        
        # Validate identification format if provided
        identification = data.get('customer_identification', '').strip()
        if identification:
            try:
                from .models import validate_venezuelan_cedula
                validate_venezuelan_cedula(identification)
            except ValidationError as e:
                result['errors']['customer_identification'] = str(e)
                result['is_valid'] = False
        
        # Validate email format if provided
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                result['errors']['customer_email'] = "Invalid email format"
                result['is_valid'] = False
        
        # Validate phone format if provided
        if phone:
            # Basic phone validation - should start with + and contain only digits, spaces, and dashes
            phone_clean = phone.replace('+', '').replace('-', '').replace(' ', '')
            if not phone_clean.isdigit() or len(phone_clean) < 10:
                result['errors']['customer_phone'] = "Invalid phone format"
                result['is_valid'] = False
        
        return result
    
    @staticmethod
    def normalize_customer_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize customer data for consistent storage.
        
        Args:
            data: Raw customer data
        
        Returns:
            Normalized customer data
        """
        normalized = {}
        
        # Normalize text fields
        text_fields = ['customer_name', 'customer_surname', 'customer_email']
        for field in text_fields:
            if field in data and data[field]:
                normalized[field] = data[field].strip()
        
        # Normalize identification
        if 'customer_identification' in data and data['customer_identification']:
            normalized['customer_identification'] = data['customer_identification'].replace(' ', '').upper()
        
        # Normalize phone (keep as provided for phonenumber_field to handle)
        if 'customer_phone' in data and data['customer_phone']:
            normalized['customer_phone'] = data['customer_phone'].strip()
        
        return normalized