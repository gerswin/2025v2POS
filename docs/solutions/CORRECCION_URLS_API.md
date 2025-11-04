# Corrección de URLs de API

## 🐛 Problema Identificado

El endpoint `/api/auth/login/` no existe. Las rutas de API están versionadas bajo `/api/v1/`.

## ✅ URLs Correctas de la API

### Autenticación
- **Login**: `POST /api/v1/auth/login/`
- **Refresh Token**: `POST /api/v1/auth/refresh/`
- **Logout**: `POST /api/v1/auth/logout/`
- **Registro**: `POST /api/v1/auth/register/`
- **Perfil**: `GET /api/v1/auth/profile/`
- **Cambiar Password**: `POST /api/v1/auth/change-password/`
- **Permisos**: `GET /api/v1/auth/permissions/`
- **Tenants**: `GET /api/v1/auth/tenants/`

### Otros Endpoints Principales
- **Eventos**: `/api/v1/events/`
- **Zonas**: `/api/v1/zones/`
- **Clientes**: `/api/v1/customers/`
- **Ventas**: `/api/v1/sales/`
- **Notificaciones**: `/api/v1/notifications/`
- **Tickets**: `/api/v1/tickets/`
- **Fiscal**: `/api/v1/fiscal/`
- **Reportes**: `/api/v1/reports/`

## 🧪 Comandos Curl Corregidos

### 1. Login de Usuario
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "gerswin",
    "password": "MiPasswordSeguro123"
  }'
```

**Respuesta esperada:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid-here",
    "username": "gerswin",
    "email": "g3rswin@gmail.com",
    "role": "admin_user",
    "tenant": null
  }
}
```

### 2. Login de Tenant Admin
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tenant_admin",
    "password": "tenant123"
  }'
```

### 3. Obtener Perfil de Usuario
```bash
curl -X GET http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Listar Tenants
```bash
curl -X GET http://localhost:8000/api/v1/auth/tenants/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. Refresh Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

## 📋 Endpoints de Gestión

### Eventos
```bash
# Listar eventos
curl -X GET http://localhost:8000/api/v1/events/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Crear evento
curl -X POST http://localhost:8000/api/v1/events/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Concierto de Prueba",
    "venue_id": "venue-uuid",
    "start_date": "2025-02-15T20:00:00Z",
    "end_date": "2025-02-15T23:00:00Z"
  }'
```

### Clientes
```bash
# Crear cliente
curl -X POST http://localhost:8000/api/v1/customers/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "María",
    "surname": "González",
    "phone": "+58-414-1234567",
    "email": "maria@example.com",
    "identification": "V-12345678"
  }'

# Buscar cliente
curl -X GET "http://localhost:8000/api/v1/customers/search/?phone=+58-414-1234567" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Ventas
```bash
# Ver carrito
curl -X GET http://localhost:8000/api/v1/sales/cart/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Crear transacción
curl -X POST http://localhost:8000/api/v1/sales/transactions/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "event-uuid",
    "customer_id": "customer-uuid",
    "items": [
      {
        "zone_id": "zone-uuid",
        "seat_id": "seat-uuid",
        "quantity": 1
      }
    ]
  }'
```

## 🌐 Interfaces Web Disponibles

### Dashboards Principales
- **Admin Django**: `http://localhost:8000/admin/`
- **Dashboard Principal**: `http://localhost:8000/`
- **Eventos**: `http://localhost:8000/events/`
- **Pricing**: `http://localhost:8000/pricing/`
- **Ventas**: `http://localhost:8000/sales/`
- **Clientes**: `http://localhost:8000/customers/`
- **Reportes**: `http://localhost:8000/reports/`

### Autenticación Web
- **Login Web**: `http://localhost:8000/auth/login/`
- **Dashboard**: `http://localhost:8000/auth/dashboard/`

### Documentación
- **API Docs (Swagger)**: `http://localhost:8000/api/docs/`
- **API Docs (ReDoc)**: `http://localhost:8000/api/redoc/`
- **API Schema**: `http://localhost:8000/api/schema/`

### Monitoreo
- **Health Check**: `http://localhost:8000/health/`
- **Métricas**: `http://localhost:8000/metrics/` (solo en producción)
- **Silk Profiling**: `http://localhost:8000/silk/` (solo en desarrollo)

## 🔧 Flujo de Autenticación Completo

### 1. Login y Obtener Tokens
```bash
# Login
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "gerswin",
    "password": "MiPasswordSeguro123"
  }')

# Extraer token de acceso
ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access')
echo "Access Token: $ACCESS_TOKEN"
```

### 2. Usar Token en Requests
```bash
# Usar el token en requests subsecuentes
curl -X GET http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 3. Refresh Token Cuando Expire
```bash
# Extraer refresh token
REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh')

# Obtener nuevo access token
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}"
```

## 📝 Guía de Pruebas Actualizada

Ahora puedes usar las URLs correctas en la **Guía de Pruebas Completa**. Todos los endpoints de API deben usar el prefijo `/api/v1/` en lugar de `/api/`.

### Ejemplo de Flujo Completo:
1. **Login**: `/api/v1/auth/login/`
2. **Crear Cliente**: `/api/v1/customers/`
3. **Crear Evento**: `/api/v1/events/`
4. **Procesar Venta**: `/api/v1/sales/transactions/`
5. **Generar Ticket**: `/api/v1/tickets/generate/`

¡Todas las funcionalidades están disponibles, solo necesitabas las URLs correctas!