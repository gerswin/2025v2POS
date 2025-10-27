# 🧪 Test Users Guide - Venezuelan POS System

This document provides a comprehensive list of test users, tenants, venues, and events for testing the Venezuelan POS System.

## 🚀 Quick Setup

Run the test data creation script:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the test data script
python create_test_users.py
```

## 👥 Test Users

### 🔧 System Administrator

| Username | Password | Role | Email | Description |
|----------|----------|------|-------|-------------|
| `admin` | `admin123` | Admin User | admin@venezuelanpos.com | System-wide administrator with full access |

### 🏢 Tenant: Eventos Caracas

**Company Details:**
- **Name:** Eventos Caracas
- **Slug:** eventos-caracas
- **Email:** admin@eventoscaracas.com
- **Phone:** +58-212-555-0001
- **Location:** Caracas, Distrito Capital

**Users:**

| Username | Password | Role | Name | Email | Phone | Description |
|----------|----------|------|------|-------|-------|-------------|
| `carlos.admin` | `carlos123` | Tenant Admin | Carlos Rodríguez | carlos@eventoscaracas.com | +58-414-555-1001 | Tenant administrator for Eventos Caracas |
| `maria.operator` | `maria123` | Event Operator | María González | maria@eventoscaracas.com | +58-424-555-1002 | Event operator for daily operations |
| `jose.operator` | `jose123` | Event Operator | José Pérez | jose@eventoscaracas.com | +58-414-555-1003 | Event operator for ticket sales |

**Venues:**
- **Teatro Teresa Carreño** (2,400 capacity) - Premium theater venue
- **Poliedro de Caracas** (15,000 capacity) - Large concert venue
- **Centro de Arte Los Galpones** (800 capacity) - Intimate art space

**Sample Events:**
- **Concierto Sinfónico de Año Nuevo** - New Year's symphonic concert (Numbered seats)
- **Festival Rock Venezolano 2025** - Rock festival (General assignment)
- **Exposición de Arte Contemporáneo** - Contemporary art exhibition (General assignment)

### 🏢 Tenant: Valencia Entertainment

**Company Details:**
- **Name:** Valencia Entertainment
- **Slug:** valencia-entertainment
- **Email:** info@valenciaent.com
- **Phone:** +58-241-555-0002
- **Location:** Valencia, Carabobo

**Users:**

| Username | Password | Role | Name | Email | Phone | Description |
|----------|----------|------|------|-------|-------|-------------|
| `ana.admin` | `ana123` | Tenant Admin | Ana Martínez | ana@valenciaent.com | +58-414-555-2001 | Tenant administrator for Valencia Entertainment |
| `luis.operator` | `luis123` | Event Operator | Luis Hernández | luis@valenciaent.com | +58-424-555-2002 | Event operator for Valencia region |

**Venues:**
- **Teatro Municipal de Valencia** (1,200 capacity) - Municipal theater
- **Forum de Valencia** (8,000 capacity) - Large entertainment venue

**Sample Events:**
- **Obra Teatral: Romeo y Julieta** - Shakespeare adaptation (Numbered seats)
- **Concierto de Salsa Internacional** - International salsa concert (Mixed seating)

### 🏢 Tenant: Maracaibo Shows

**Company Details:**
- **Name:** Maracaibo Shows
- **Slug:** maracaibo-shows
- **Email:** contact@maracaiboshows.com
- **Phone:** +58-261-555-0003
- **Location:** Maracaibo, Zulia

**Users:**

| Username | Password | Role | Name | Email | Phone | Description |
|----------|----------|------|------|-------|-------|-------------|
| `sofia.admin` | `sofia123` | Tenant Admin | Sofía López | sofia@maracaiboshows.com | +58-414-555-3001 | Tenant administrator for Maracaibo Shows |
| `pedro.operator` | `pedro123` | Event Operator | Pedro Ramírez | pedro@maracaiboshows.com | +58-424-555-3002 | Event operator for Zulia region |

**Venues:**
- **Teatro Baralt** (1,500 capacity) - Historic theater
- **Centro de Convenciones Lago Mar** (5,000 capacity) - Convention center

**Sample Events:**
- **Recital de Piano Clásico** - Classical piano recital (Numbered seats)
- **Feria Gastronómica del Zulia** - Zulia gastronomic fair (General assignment)

## 🧪 Testing Scenarios

### 1. Authentication Testing

```bash
# Test login for different user types
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "carlos.admin", "password": "carlos123"}'
```

### 2. Multi-Tenant Data Isolation

- Login as `carlos.admin` (Eventos Caracas) - should only see Caracas venues/events
- Login as `ana.admin` (Valencia Entertainment) - should only see Valencia venues/events
- Login as `admin` (System Admin) - should see all data

### 3. Role-Based Access Control

**Tenant Admin (`carlos.admin`):**
- ✅ Can create/edit venues and events
- ✅ Can manage event configurations
- ✅ Can activate/deactivate events
- ✅ Can view all tenant data

**Event Operator (`maria.operator`):**
- ✅ Can view venues and events
- ✅ Can create events (limited)
- ❌ Cannot delete venues
- ❌ Cannot access other tenants' data

**System Admin (`admin`):**
- ✅ Full access to all tenants
- ✅ Can create new tenants
- ✅ Can manage system-wide settings

### 4. Event Status Testing

**Active Events (Sales Open):**
- Concierto Sinfónico de Año Nuevo
- Festival Rock Venezolano 2025
- Exposición de Arte Contemporáneo
- Obra Teatral: Romeo y Julieta
- Recital de Piano Clásico

**Draft Events (Not Yet Active):**
- Concierto de Salsa Internacional
- Feria Gastronómica del Zulia

### 5. Event Type Testing

**Numbered Seat Events:**
- Concierto Sinfónico de Año Nuevo
- Obra Teatral: Romeo y Julieta
- Recital de Piano Clásico

**General Assignment Events:**
- Festival Rock Venezolano 2025
- Exposición de Arte Contemporáneo
- Feria Gastronómica del Zulia

**Mixed Events:**
- Concierto de Salsa Internacional

## 📱 API Testing Examples

### Get User Profile
```bash
curl -X GET http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### List Venues (Tenant-Filtered)
```bash
curl -X GET http://localhost:8000/api/v1/venues/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### List Events (Tenant-Filtered)
```bash
curl -X GET http://localhost:8000/api/v1/events/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create New Event
```bash
curl -X POST http://localhost:8000/api/v1/events/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Event",
    "description": "A test event",
    "event_type": "general_assignment",
    "venue": "VENUE_UUID",
    "start_date": "2025-12-31T20:00:00-04:00",
    "end_date": "2025-12-31T23:00:00-04:00"
  }'
```

### Activate Event
```bash
curl -X POST http://localhost:8000/api/v1/events/EVENT_UUID/activate/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔍 Testing Checklist

### ✅ Authentication & Authorization
- [ ] System admin can access all tenants
- [ ] Tenant admins can only access their tenant data
- [ ] Event operators have limited permissions
- [ ] Unauthorized users cannot access protected endpoints

### ✅ Multi-Tenancy
- [ ] Data isolation between tenants
- [ ] Tenant-specific venue listings
- [ ] Tenant-specific event listings
- [ ] Cross-tenant data access prevention

### ✅ Event Management
- [ ] Create events with different types
- [ ] Event status transitions (Draft → Active → Closed)
- [ ] Event date validation
- [ ] Sales period validation
- [ ] Event configuration management

### ✅ Venue Management
- [ ] Create venues with different capacities
- [ ] Venue type handling (physical, virtual, hybrid)
- [ ] Venue contact information management
- [ ] Venue activation/deactivation

### ✅ API Functionality
- [ ] CRUD operations for all models
- [ ] Filtering and searching
- [ ] Pagination
- [ ] Error handling
- [ ] Validation responses

## 🚨 Important Notes

1. **Password Security:** These are test passwords only. Never use simple passwords in production.

2. **Data Reset:** To reset test data, delete the database and run migrations again:
   ```bash
   rm db.sqlite3
   python manage.py migrate
   python create_test_users.py
   ```

3. **Currency Rates:** All events use USD as base currency with a conversion rate of 36.50 VES/USD (example rate).

4. **Time Zones:** All dates are in America/Caracas timezone (VET).

5. **Event Dates:** Events are scheduled at various future dates to test different scenarios (upcoming, ongoing, past).

## 🔧 Troubleshooting

If you encounter issues:

1. **Database Errors:** Ensure migrations are up to date
2. **Authentication Errors:** Check JWT token expiration
3. **Permission Errors:** Verify user roles and tenant assignments
4. **Data Not Showing:** Confirm tenant context is properly set

For additional help, check the API documentation at `/api/docs/` when the server is running.