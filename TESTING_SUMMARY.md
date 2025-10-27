# 🧪 Venezuelan POS System - Testing Summary

## 📋 Quick Reference - Test Users

### 🔧 System Administrator
```
Username: admin
Password: admin123
Role: System Admin
Access: All tenants and system-wide settings
```

### 🏢 Eventos Caracas (Caracas, Venezuela)
```
Tenant Admin:
  Username: carlos.admin
  Password: carlos123
  Name: Carlos Rodríguez
  
Event Operators:
  Username: maria.operator
  Password: maria123
  Name: María González
  
  Username: jose.operator
  Password: jose123
  Name: José Pérez
```

### 🏢 Valencia Entertainment (Valencia, Venezuela)
```
Tenant Admin:
  Username: ana.admin
  Password: ana123
  Name: Ana Martínez
  
Event Operator:
  Username: luis.operator
  Password: luis123
  Name: Luis Hernández
```

### 🏢 Maracaibo Shows (Maracaibo, Venezuela)
```
Tenant Admin:
  Username: sofia.admin
  Password: sofia123
  Name: Sofía López
  
Event Operator:
  Username: pedro.operator
  Password: pedro123
  Name: Pedro Ramírez
```

## 🚀 Quick Start Testing

### 1. Setup Test Data
```bash
# Activate virtual environment
source .venv/bin/activate

# Create all test users, venues, and events
python create_test_users.py

# Start the development server
python manage.py runserver
```

### 2. Test API Endpoints
```bash
# Run automated API tests
python test_api_endpoints.py
```

### 3. Manual Testing with cURL

**Login:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "carlos.admin", "password": "carlos123"}'
```

**Get Venues (tenant-filtered):**
```bash
curl -X GET http://127.0.0.1:8000/api/v1/venues/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Get Events (tenant-filtered):**
```bash
curl -X GET http://127.0.0.1:8000/api/v1/events/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🏢 Test Venues by Tenant

### Eventos Caracas (3 venues)
- **Teatro Teresa Carreño** - 2,400 capacity (Premium theater)
- **Poliedro de Caracas** - 15,000 capacity (Large concert venue)
- **Centro de Arte Los Galpones** - 800 capacity (Intimate art space)

### Valencia Entertainment (2 venues)
- **Teatro Municipal de Valencia** - 1,200 capacity (Municipal theater)
- **Forum de Valencia** - 8,000 capacity (Entertainment venue)

### Maracaibo Shows (2 venues)
- **Teatro Baralt** - 1,500 capacity (Historic theater)
- **Centro de Convenciones Lago Mar** - 5,000 capacity (Convention center)

## 🎭 Test Events by Status

### ✅ Active Events (Sales Open)
- **Concierto Sinfónico de Año Nuevo** (Eventos Caracas) - Numbered seats
- **Festival Rock Venezolano 2025** (Eventos Caracas) - General assignment
- **Exposición de Arte Contemporáneo** (Eventos Caracas) - General assignment
- **Obra Teatral: Romeo y Julieta** (Valencia Entertainment) - Numbered seats
- **Recital de Piano Clásico** (Maracaibo Shows) - Numbered seats

### 📝 Draft Events (Not Active)
- **Concierto de Salsa Internacional** (Valencia Entertainment) - Mixed seating
- **Feria Gastronómica del Zulia** (Maracaibo Shows) - General assignment

## 🧪 Key Testing Scenarios

### 1. Multi-Tenancy Verification
- Login as `carlos.admin` → Should see only Eventos Caracas data
- Login as `ana.admin` → Should see only Valencia Entertainment data
- Login as `admin` → Should see all data across tenants

### 2. Role-Based Access Control
- **Tenant Admins** can create/edit venues and events
- **Event Operators** can view and create events (limited permissions)
- **System Admin** has full access to everything

### 3. Event Management
- Create events with different types (general assignment, numbered seats, mixed)
- Test event status transitions (draft → active → closed)
- Validate date constraints (sales dates, event dates)
- Test event activation/deactivation

### 4. Data Validation
- Event dates must be logical (start < end)
- Sales dates must end before event starts
- Currency conversion rates must be positive
- Venue capacity must be positive

## 📱 Postman Collection

Import the generated Postman collection for comprehensive API testing:
```
File: postman/Venezuelan_POS_System_Complete.postman_collection.json
```

The collection includes:
- Pre-configured requests for all endpoints
- Automatic token management
- Test scripts for validation
- Multiple user login scenarios

## 🔍 Testing Checklist

### ✅ Authentication & Authorization
- [ ] System admin login works
- [ ] Tenant admin login works
- [ ] Event operator login works
- [ ] Invalid credentials are rejected
- [ ] JWT tokens are properly generated
- [ ] Token expiration is handled

### ✅ Multi-Tenancy
- [ ] Users only see their tenant's data
- [ ] Cross-tenant data access is prevented
- [ ] System admin sees all tenant data
- [ ] Tenant isolation is maintained

### ✅ Venue Management
- [ ] List venues (tenant-filtered)
- [ ] Create new venues
- [ ] Update venue information
- [ ] Search and filter venues
- [ ] Venue validation works

### ✅ Event Management
- [ ] List events (tenant-filtered)
- [ ] Create events with configurations
- [ ] Update event details
- [ ] Event status management (activate/deactivate)
- [ ] Event type handling (general/numbered/mixed)
- [ ] Date validation works

### ✅ API Functionality
- [ ] All CRUD operations work
- [ ] Filtering and searching work
- [ ] Pagination is implemented
- [ ] Error responses are proper
- [ ] Validation messages are clear

## 🚨 Important Notes

1. **Test Environment Only**: These credentials are for testing only
2. **Data Reset**: Run `python create_test_users.py` to reset test data
3. **Server Required**: Development server must be running on port 8000
4. **Database**: Uses SQLite for development (db.sqlite3)

## 📞 Support

If you encounter issues:
1. Check server is running: `python manage.py runserver`
2. Verify database migrations: `python manage.py migrate`
3. Reset test data: `python create_test_users.py`
4. Check API documentation: `http://127.0.0.1:8000/api/docs/`

---

**Happy Testing! 🎉**