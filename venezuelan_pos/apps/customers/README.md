# Customer Management System

This module provides comprehensive customer management functionality for the Venezuelan POS system, including data capture, validation, and integration with the sales process.

## Features

### Core Models

- **Customer**: Main customer entity with Venezuelan-specific validation
- **CustomerPreferences**: Communication preferences and notification settings

### Key Capabilities

- Venezuelan cédula validation (V-12345678 or E-12345678 format)
- Phone number validation with Venezuelan regional support
- Multi-channel communication preferences (Email, SMS, WhatsApp)
- Customer search and lookup functionality
- Sales process integration

## API Endpoints

### Customer CRUD Operations

- `GET /api/v1/customers/` - List customers with filtering and search
- `POST /api/v1/customers/` - Create new customer
- `GET /api/v1/customers/{id}/` - Get customer details
- `PUT/PATCH /api/v1/customers/{id}/` - Update customer
- `DELETE /api/v1/customers/{id}/` - Soft delete customer

### Customer Preferences

- `GET /api/v1/customers/{id}/preferences/` - Get communication preferences
- `PUT/PATCH /api/v1/customers/{id}/preferences/` - Update preferences

### Search and Lookup

- `POST /api/v1/customers/search/` - Search customers by query
- `POST /api/v1/customers/lookup/` - Lookup by identification
- `GET /api/v1/customers/quick-lookup/?q={query}` - Quick lookup by any identifier

### Sales Integration

- `POST /api/v1/customers/validate/` - Validate customer data for sales
- `POST /api/v1/customers/find-or-create/` - Find or create customer from sales data
- `GET /api/v1/customers/{id}/purchase-history/` - Get purchase history
- `GET /api/v1/customers/{id}/sales-summary/` - Get sales summary

## Usage Examples

### Creating a Customer

```python
from venezuelan_pos.apps.customers.services import CustomerService

# From sales data
sales_data = {
    'customer_name': 'Juan',
    'customer_surname': 'Pérez',
    'customer_phone': '+584121234567',
    'customer_email': 'juan@example.com',
    'customer_identification': 'V-12345678'
}

customer = CustomerService.create_customer_from_sales_data(sales_data)
```

### Finding or Creating Customer

```python
# This will find existing customer or create new one
customer = CustomerService.find_or_create_customer(sales_data)
```

### Customer Lookup

```python
from venezuelan_pos.apps.customers.services import CustomerLookupService

# Quick lookup by any identifier
customer = CustomerLookupService.quick_lookup('V-12345678')
customer = CustomerLookupService.quick_lookup('juan@example.com')
customer = CustomerLookupService.quick_lookup('+584121234567')
```

### Validation

```python
from venezuelan_pos.apps.customers.services import CustomerValidationService

# Validate customer data
result = CustomerValidationService.validate_customer_data_for_sales(data)
if result['is_valid']:
    # Process customer data
    pass
else:
    # Handle validation errors
    print(result['errors'])
```

## Integration with Sales Process

### Using Mixins

For future transaction models, use the provided mixins:

```python
from venezuelan_pos.apps.customers.mixins import CustomerRelatedMixin

class Transaction(TenantAwareModel, CustomerRelatedMixin):
    # Transaction fields
    fiscal_series = models.CharField(max_length=20)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        # Validate customer before saving
        self.validate_customer_for_transaction()
        super().save(*args, **kwargs)
```

### Notification Integration

```python
# Check if customer can receive notifications
if transaction.can_notify_customer('purchase_confirmation', 'email'):
    # Send email notification
    pass

# Get customer contact info
contact_info = transaction.get_customer_contact_info()
```

## Validation Rules

### Required Fields

- `name`: Customer's first name (non-empty)
- `surname`: Customer's last name (non-empty)
- At least one of: `phone` or `email`

### Optional Fields

- `identification`: Venezuelan cédula (V-12345678 or E-12345678)
- `date_of_birth`: Customer's birth date
- `address`: Customer's address
- `notes`: Additional notes

### Validation Features

- Venezuelan cédula format validation
- Phone number format validation (international format preferred)
- Email format validation
- Duplicate prevention (unique identification and email per tenant)

## Communication Preferences

Customers can configure preferences for:

- **Channels**: Email, SMS, WhatsApp, Phone calls
- **Notification Types**: Purchase confirmations, payment reminders, event reminders, promotional messages, system updates
- **Contact Times**: Preferred time range for communications
- **Language**: Spanish (es) or English (en)

## Admin Interface

The Django admin provides:

- Customer management with search and filtering
- Bulk actions (activate/deactivate customers)
- Inline preferences editing
- Customer statistics and reporting

## Testing

Run tests with:

```bash
python manage.py test venezuelan_pos.apps.customers
```

The test suite covers:

- Model validation and business logic
- Customer services and utilities
- API endpoints functionality
- Integration scenarios

## Future Integration Points

This module is designed to integrate with:

- **Sales/Transaction System**: Customer data capture during ticket sales
- **Payment System**: Customer information for payment processing
- **Notification System**: Multi-channel customer communications
- **Reporting System**: Customer analytics and purchase history