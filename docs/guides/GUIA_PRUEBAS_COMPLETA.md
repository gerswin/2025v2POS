# Guía Completa de Pruebas - Sistema POS Venezolano

Esta guía te permitirá probar todas las funcionalidades implementadas del sistema POS venezolano paso a paso.

## 📋 Requisitos Previos

### 1. Configuración del Entorno
```bash
# 1. Activar entorno virtual
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 4. Ejecutar migraciones
python manage.py migrate

# 5. Compilar traducciones
python manage.py compilemessages

# 6. Crear datos de prueba
python setup_test_data.py
```

### 2. Iniciar Servicios
```bash
# Terminal 1: Servidor Django
python manage.py runserver

# Terminal 2: Redis (si no usas Docker)
redis-server

# Terminal 3: Celery Worker
celery -A venezuelan_pos worker -l info

# Terminal 4: Celery Beat
celery -A venezuelan_pos beat -l info
```

## 🏢 PARTE 1: Gestión Multi-Tenant y Autenticación

### Paso 1.1: Crear y Gestionar Tenants
```bash
# Crear superusuario del sistema
python manage.py createsuperuser

# Acceder al admin de Django
# URL: http://localhost:8000/admin/
```

**Pruebas en Django Admin:**
1. **Crear Tenant:**
   - Ir a "Tenants" → "Add Tenant"
   - Nombre: "Eventos Caracas"
   - Slug: "eventos-caracas"
   - Configuración fiscal: Prefijo "EC"
   - Guardar

2. **Crear Usuario Tenant Admin:**
   - Ir a "Users" → "Add User"
   - Username: "admin_caracas"
   - Email: "admin@eventoscaracas.com"
   - Tenant: "Eventos Caracas"
   - Role: "Tenant Admin"
   - Guardar

### Paso 1.2: Probar Autenticación JWT
```bash
# Probar login via API
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin_caracas",
    "password": "tu_password"
  }'

# Respuesta esperada: tokens de acceso y refresh
```

## 🎪 PARTE 2: Gestión de Eventos y Venues

### Paso 2.1: Crear Venue
**En Django Admin:**
1. Ir a "Venues" → "Add Venue"
2. Completar datos:
   - Nombre: "Teatro Teresa Carreño"
   - Dirección: "Av. Paseo Colón, Caracas"
   - Ciudad: "Caracas"
   - Capacidad: 2000
   - Tipo: "Physical Venue"

### Paso 2.2: Crear Evento
**En Django Admin:**
1. Ir a "Events" → "Add Event"
2. Completar:
   - Nombre: "Concierto Sinfónico 2025"
   - Venue: "Teatro Teresa Carreño"
   - Tipo: "Numbered Seat Event"
   - Fecha inicio: Fecha futura
   - Fecha fin: Mismo día, 3 horas después
   - Estado: "Active"

### Paso 2.3: Configurar Zonas y Asientos
**Crear Zona Numerada:**
1. Ir a "Zones" → "Add Zone"
2. Configurar:
   - Evento: "Concierto Sinfónico 2025"
   - Nombre: "Platea"
   - Tipo: "Numbered Zone"
   - Filas: 20
   - Asientos por fila: 25
   - Precio base: 50.00 USD

**Crear Zona General:**
1. Crear segunda zona:
   - Nombre: "Balcón"
   - Tipo: "General Zone"
   - Capacidad: 200
   - Precio base: 30.00 USD

### Paso 2.4: Verificar Generación Automática de Asientos
```bash
# Verificar en Django shell
python manage.py shell

# En el shell:
from venezuelan_pos.apps.zones.models import Zone, Seat
zona_platea = Zone.objects.get(name="Platea")
print(f"Asientos generados: {zona_platea.seats.count()}")
# Debe mostrar: 500 asientos (20 filas × 25 asientos)

# Ver algunos asientos
for seat in zona_platea.seats.all()[:5]:
    print(f"Fila {seat.row_number}, Asiento {seat.seat_number}")
```

## 💰 PARTE 3: Sistema de Precios Dinámicos

### Paso 3.1: Configurar Etapas de Precios
**En Django Admin:**
1. Ir a "Price Stages" → "Add Price Stage"
2. **Etapa 1 - Early Bird:**
   - Evento: "Concierto Sinfónico 2025"
   - Nombre: "Early Bird"
   - Orden: 1
   - Fecha inicio: Hoy
   - Fecha fin: En 7 días
   - Límite cantidad: 100
   - Tipo modificador: "Percentage"
   - Valor modificador: -0.25 (25% descuento)
   - Alcance: "Event-wide"

3. **Etapa 2 - Regular:**
   - Nombre: "Regular"
   - Orden: 2
   - Fecha inicio: En 8 días
   - Fecha fin: En 15 días
   - Límite cantidad: 200
   - Valor modificador: 0.00 (precio normal)

4. **Etapa 3 - Last Minute:**
   - Nombre: "Last Minute"
   - Orden: 3
   - Fecha inicio: En 16 días
   - Fecha fin: Día del evento
   - Límite cantidad: 150
   - Valor modificador: 0.15 (15% recargo)

### Paso 3.2: Configurar Precios por Fila
**En Django Admin:**
1. Ir a "Row Pricings" → "Add Row Pricing"
2. Configurar precios premium:
   - Zona: "Platea"
   - Fila: 1-5 (filas delanteras)
   - Multiplicador: 1.50 (50% más caro)
   - Fila: 6-10 (filas medias)
   - Multiplicador: 1.25 (25% más caro)
   - Fila: 11-20 (filas traseras)
   - Multiplicador: 1.00 (precio base)

### Paso 3.3: Probar Cálculo de Precios
```bash
# Probar API de precios
curl -X GET "http://localhost:8000/api/pricing/calculate/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -G \
  -d "zone_id=ZONE_UUID" \
  -d "row_number=1" \
  -d "quantity=2"

# Respuesta esperada:
# {
#   "base_price": 50.00,
#   "stage_modifier": -0.25,
#   "row_modifier": 1.50,
#   "final_price": 56.25,
#   "stage_name": "Early Bird",
#   "total_amount": 112.50
# }
```

### Paso 3.4: Verificar Transiciones Automáticas
```bash
# Simular venta de 100 tickets para activar transición
python manage.py shell

# En el shell:
from venezuelan_pos.apps.pricing.services import PricingService
from venezuelan_pos.apps.events.models import Event

evento = Event.objects.get(name="Concierto Sinfónico 2025")
pricing_service = PricingService()

# Simular venta que active transición
current_stage = pricing_service.get_current_stage(evento)
print(f"Etapa actual: {current_stage.name}")

# Verificar transición automática
# (Esto se activaría automáticamente al vender 100 tickets)
```

## 👥 PARTE 4: Gestión de Clientes

### Paso 4.1: Registrar Cliente
**Via API:**
```bash
curl -X POST http://localhost:8000/api/customers/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "María",
    "surname": "González",
    "phone": "+58-414-1234567",
    "email": "maria.gonzalez@email.com",
    "identification": "V-12345678",
    "preferences": {
      "email_notifications": true,
      "sms_notifications": false,
      "whatsapp_notifications": true
    }
  }'
```

### Paso 4.2: Buscar Cliente
```bash
# Buscar por teléfono
curl -X GET "http://localhost:8000/api/customers/search/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -G \
  -d "phone=+58-414-1234567"

# Buscar por email
curl -X GET "http://localhost:8000/api/customers/search/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -G \
  -d "email=maria.gonzalez@email.com"
```

## 🎫 PARTE 5: Proceso de Ventas

### Paso 5.1: Seleccionar Asientos
```bash
# Ver disponibilidad de asientos
curl -X GET "http://localhost:8000/api/zones/ZONE_UUID/seats/availability/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Reservar asientos específicos
curl -X POST http://localhost:8000/api/sales/reserve-seats/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seats": [
      {"zone_id": "ZONE_UUID", "row": 1, "seat": 15},
      {"zone_id": "ZONE_UUID", "row": 1, "seat": 16}
    ],
    "customer_id": "CUSTOMER_UUID"
  }'
```

### Paso 5.2: Crear Transacción
```bash
curl -X POST http://localhost:8000/api/sales/transactions/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVENT_UUID",
    "customer_id": "CUSTOMER_UUID",
    "items": [
      {
        "zone_id": "ZONE_UUID",
        "seat_id": "SEAT_UUID_1",
        "quantity": 1
      },
      {
        "zone_id": "ZONE_UUID",
        "seat_id": "SEAT_UUID_2",
        "quantity": 1
      }
    ]
  }'
```

### Paso 5.3: Probar Interfaz Web de Ventas
**Acceder a:**
- URL: `http://localhost:8000/sales/dashboard/`
- Probar selección de asientos interactiva
- Verificar cálculo de precios en tiempo real
- Probar carrito de compras

## 💳 PARTE 6: Procesamiento de Pagos

### Paso 6.1: Configurar Métodos de Pago
**En Django Admin:**
1. Ir a "Payment Methods" → "Add Payment Method"
2. Crear métodos:
   - Efectivo (Cash)
   - Tarjeta de Crédito (Credit Card)
   - Transferencia Bancaria (Bank Transfer)
   - PagoMóvil

### Paso 6.2: Procesar Pago Completo
```bash
curl -X POST http://localhost:8000/api/payments/process/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TRANSACTION_UUID",
    "payment_method": "cash",
    "amount": 112.50,
    "reference_number": "CASH-001"
  }'
```

### Paso 6.3: Configurar Plan de Pagos
```bash
# Crear plan de cuotas
curl -X POST http://localhost:8000/api/payments/installment-plan/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TRANSACTION_UUID",
    "installments": 3,
    "down_payment": 37.50,
    "installment_amount": 25.00,
    "due_dates": [
      "2025-02-15",
      "2025-03-15",
      "2025-04-15"
    ]
  }'
```

### Paso 6.4: Procesar Pago Parcial
```bash
# Primer pago del plan
curl -X POST http://localhost:8000/api/payments/installment-payment/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_plan_id": "PLAN_UUID",
    "amount": 37.50,
    "payment_method": "credit_card",
    "reference_number": "CC-12345"
  }'
```

## 📧 PARTE 7: Sistema de Notificaciones

### Paso 7.1: Configurar Plantillas de Notificación
**En Django Admin:**
1. Ir a "Notification Templates" → "Add Template"
2. Crear plantillas:
   - **Confirmación de Compra:**
     - Nombre: "purchase_confirmation"
     - Asunto: "Confirmación de compra - {{event.name}}"
     - Contenido: "Hola {{customer.name}}, tu compra ha sido confirmada..."
   
   - **Recordatorio de Pago:**
     - Nombre: "payment_reminder"
     - Asunto: "Recordatorio de pago pendiente"
     - Contenido: "Tienes un pago pendiente de {{amount}} para {{event.name}}"

### Paso 7.2: Probar Envío de Notificaciones
```bash
# Enviar notificación manual
curl -X POST http://localhost:8000/api/notifications/send/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "purchase_confirmation",
    "customer_id": "CUSTOMER_UUID",
    "channels": ["email", "whatsapp"],
    "context": {
      "event": {"name": "Concierto Sinfónico 2025"},
      "transaction_id": "TRANSACTION_UUID"
    }
  }'
```

### Paso 7.3: Verificar Cola de Celery
```bash
# Ver tareas en cola
celery -A venezuelan_pos inspect active

# Ver estadísticas
celery -A venezuelan_pos inspect stats

# Monitorear con Flower (opcional)
# URL: http://localhost:5555/
```

## 🎟️ PARTE 8: Tickets Digitales y Validación

### Paso 8.1: Generar Tickets Digitales
```bash
# Generar ticket después del pago completo
curl -X POST http://localhost:8000/api/tickets/generate/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TRANSACTION_UUID"
  }'
```

### Paso 8.2: Validar Tickets
```bash
# Validar por código QR
curl -X POST http://localhost:8000/api/tickets/validate/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_code": "ENCRYPTED_QR_DATA",
    "validation_type": "entry"
  }'

# Validar por serie fiscal
curl -X GET "http://localhost:8000/api/tickets/validate/EC00000001/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Paso 8.3: Probar Interfaz de Validación
**Acceder a:**
- URL: `http://localhost:8000/tickets/validation/`
- Probar escáner de QR (simulado)
- Verificar historial de validaciones

## 📊 PARTE 9: Reportes y Analytics

### Paso 9.1: Generar Reportes de Ventas
```bash
# Reporte por período
curl -X GET "http://localhost:8000/api/reports/sales/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -G \
  -d "start_date=2025-01-01" \
  -d "end_date=2025-01-31" \
  -d "event_id=EVENT_UUID"

# Reporte por zona
curl -X GET "http://localhost:8000/api/reports/occupancy/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -G \
  -d "event_id=EVENT_UUID"
```

### Paso 9.2: Visualizar Heat Maps
**Acceder a:**
- URL: `http://localhost:8000/reports/heat-map/`
- Seleccionar evento
- Ver mapa de calor de ocupación por zonas

### Paso 9.3: Dashboard de Analytics
**Acceder a:**
- URL: `http://localhost:8000/reports/dashboard/`
- Ver KPIs en tiempo real
- Analizar tendencias de ventas

## 🧾 PARTE 10: Cumplimiento Fiscal

### Paso 10.1: Configurar Impuestos
**En Django Admin:**
1. Ir a "Tax Configurations" → "Add Tax Configuration"
2. Configurar IVA:
   - Nombre: "IVA"
   - Tipo: "Percentage"
   - Tasa: 16.00%
   - Aplicable a: Todos los eventos

### Paso 10.2: Generar Reportes Fiscales
```bash
# Generar reporte X (sin cerrar día fiscal)
curl -X POST http://localhost:8000/api/fiscal/x-report/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-15"
  }'

# Generar reporte Z (cerrar día fiscal)
curl -X POST http://localhost:8000/api/fiscal/z-report/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-15"
  }'
```

### Paso 10.3: Verificar Series Fiscales
```bash
# Ver series consecutivas
curl -X GET http://localhost:8000/api/fiscal/series/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -G \
  -d "start_date=2025-01-01" \
  -d "end_date=2025-01-31"
```

## 🔍 PARTE 11: Monitoreo y Performance

### Paso 11.1: Verificar Health Checks
```bash
# Health check general
curl http://localhost:8000/health/

# Health check detallado
curl http://localhost:8000/health/?format=json
```

### Paso 11.2: Monitorear Performance
**Acceder a herramientas de desarrollo:**
- Django Silk: `http://localhost:8000/silk/`
- Debug Toolbar: Visible en páginas web
- Métricas Prometheus: `http://localhost:8000/metrics/`

### Paso 11.3: Verificar Logs
```bash
# Ver logs de la aplicación
tail -f logs/django.log

# Ver logs de performance
tail -f logs/performance.log

# Ver logs de seguridad
tail -f logs/security.log
```

## 🧪 PARTE 12: Pruebas de Estrés y Concurrencia

### Paso 12.1: Probar Ventas Concurrentes
```bash
# Ejecutar script de pruebas de carga
python venezuelan_pos/core/management/commands/load_test.py

# O usar Artillery (si está configurado)
cd load_testing
./run_load_tests.sh
```

### Paso 12.2: Probar Transiciones de Etapas
```bash
# Simular múltiples compras simultáneas durante transición
python manage.py shell

# En el shell, ejecutar script de prueba de concurrencia
exec(open('test_concurrent_stage_transitions.py').read())
```

## 📱 PARTE 13: Integración con APIs Externas

### Paso 13.1: Probar Endpoints para Tiquemax
```bash
# Obtener información de ticket para impresión
curl -X GET "http://localhost:8000/api/external/ticket/EC00000001/" \
  -H "Authorization: Bearer EXTERNAL_API_TOKEN"

# Validar ticket desde sistema externo
curl -X POST http://localhost:8000/api/external/validate/ \
  -H "Authorization: Bearer EXTERNAL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fiscal_series": "EC00000001",
    "validation_point": "ENTRANCE_1"
  }'
```

## 🔧 PARTE 14: Resolución de Problemas Comunes

### Problema 1: Error de Conexión Redis
```bash
# Verificar Redis
redis-cli ping
# Debe responder: PONG

# Si no funciona, reiniciar Redis
sudo systemctl restart redis
```

### Problema 2: Celery no Procesa Tareas
```bash
# Verificar workers activos
celery -A venezuelan_pos inspect active

# Reiniciar worker si es necesario
celery -A venezuelan_pos worker --purge -l info
```

### Problema 3: Errores de Migración
```bash
# Verificar estado de migraciones
python manage.py showmigrations

# Aplicar migraciones pendientes
python manage.py migrate

# Si hay conflictos, hacer merge
python manage.py makemigrations --merge
```

### Problema 4: Cache Inconsistente
```bash
# Limpiar todos los caches
python manage.py clear_caches

# Verificar estadísticas de cache
python manage.py cache_stats
```

## ✅ Lista de Verificación Final

### Funcionalidades Básicas
- [ ] Login y autenticación JWT
- [ ] Creación de tenants y usuarios
- [ ] Gestión de eventos y venues
- [ ] Configuración de zonas y asientos
- [ ] Sistema de precios dinámicos
- [ ] Registro de clientes
- [ ] Proceso de ventas completo
- [ ] Procesamiento de pagos
- [ ] Generación de tickets digitales
- [ ] Sistema de notificaciones
- [ ] Reportes y analytics
- [ ] Cumplimiento fiscal

### Funcionalidades Avanzadas
- [ ] Pagos parciales e instalments
- [ ] Transiciones automáticas de precios
- [ ] Validación de tickets con QR
- [ ] Heat maps de ocupación
- [ ] Integración con APIs externas
- [ ] Monitoreo de performance
- [ ] Logs estructurados
- [ ] Health checks

### Performance y Escalabilidad
- [ ] Caching con Redis funcionando
- [ ] Procesamiento asíncrono con Celery
- [ ] Optimización de queries
- [ ] Manejo de concurrencia
- [ ] Métricas de performance

## 📞 Soporte y Documentación

### Recursos Adicionales
- **API Documentation**: `http://localhost:8000/api/docs/`
- **Django Admin**: `http://localhost:8000/admin/`
- **Postman Collection**: `postman/Venezuelan_POS_System.postman_collection.json`
- **Logs Directory**: `logs/`
- **Test Data Scripts**: `setup_test_data.py`, `cleanup_test_data.py`

### Comandos Útiles de Gestión
```bash
# Crear usuario admin para tenant
python manage.py create_admin_user

# Optimizar base de datos
python manage.py optimize_database

# Monitorear performance
python manage.py monitor_performance

# Limpiar reservas expiradas
python manage.py cleanup_expired_reservations

# Regenerar códigos QR
python manage.py regenerate_qr_codes
```

Esta guía cubre todas las funcionalidades principales del sistema. Cada sección incluye tanto pruebas via API como interfaces web cuando están disponibles. Sigue los pasos en orden para una experiencia completa del sistema.