# 🎫 Sistema de Entradas QR - Funcionamiento Completo

## 🎯 Resumen del Sistema

El sistema de entradas QR del Venezuelan POS es una solución completa de tickets digitales que genera códigos QR encriptados para cada entrada vendida, permitiendo validación segura y control de acceso en tiempo real.

## 🏗️ Arquitectura del Sistema

### 1. **Generación de Tickets Digitales**

#### Proceso Automático
```python
# Cuando se completa una transacción
transaction.complete() → 
DigitalTicket.objects.generate_for_transaction(transaction) →
Genera tickets individuales por cada item/cantidad →
Cada ticket obtiene QR único encriptado
```

#### Estructura del Ticket Digital
```python
class DigitalTicket:
    # Identificación única
    ticket_number = "FISCAL_SERIES-ITEM-SEQUENCE"  # Ej: "001-001-01"
    
    # Información del evento
    event = ForeignKey(Event)
    zone = ForeignKey(Zone)
    seat = ForeignKey(Seat, null=True)  # Solo para asientos numerados
    
    # Datos del cliente
    customer = ForeignKey(Customer)
    
    # Control de uso
    status = ['active', 'used', 'expired', 'cancelled']
    usage_count = 0
    max_usage_count = 1  # Puede ser > 1 para multi-entrada
    
    # Validación QR
    qr_code_data = "DATOS_ENCRIPTADOS_BASE64"
    qr_code_image = ImageField()  # Imagen PNG del QR
    validation_hash = "SHA256_HASH"
```

### 2. **Generación del Código QR**

#### Datos Incluidos en el QR
```python
validation_data = {
    'ticket_id': str(ticket.id),
    'ticket_number': ticket.ticket_number,
    'event_id': str(ticket.event.id),
    'customer_id': str(ticket.customer.id),
    'zone_id': str(ticket.zone.id),
    'seat_id': str(ticket.seat.id) if ticket.seat else None,
    'valid_from': ticket.valid_from.isoformat(),
    'valid_until': ticket.valid_until.isoformat(),
    'max_usage': ticket.max_usage_count,
    'created_at': ticket.created_at.isoformat(),
}
```

#### Proceso de Encriptación
```python
# 1. Convertir datos a JSON
json_data = json.dumps(validation_data, sort_keys=True)

# 2. Encriptar con Fernet (AES 128)
fernet = Fernet(TICKET_ENCRYPTION_KEY)
encrypted = fernet.encrypt(json_data.encode())

# 3. Codificar en Base64 para QR
qr_code_data = base64.b64encode(encrypted).decode()

# 4. Generar imagen QR
qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_L)
qr.add_data(qr_code_data)
qr_image = qr.make_image()
```

### 3. **Sistema de Validación**

#### Flujo de Validación Completo
```
1. Escanear QR / Ingresar número de ticket
2. Desencriptar datos del QR
3. Buscar ticket en base de datos
4. Validar autenticidad (IDs coinciden)
5. Verificar estado y reglas de uso
6. Marcar como usado (opcional)
7. Registrar en log de auditoría
8. Retornar resultado
```

#### Validaciones de Seguridad
```python
# Autenticidad
- ticket_id coincide con QR
- ticket_number coincide con QR  
- event_id coincide con QR
- customer_id coincide con QR
- timestamp de creación válido

# Estado del ticket
- status == 'active'
- usage_count < max_usage_count
- valid_from <= now <= valid_until
- evento no ha terminado (+ 2 horas gracia)

# Reglas de negocio
- Un uso por defecto (configurable)
- Ventana de entrada (1 hora antes del evento)
- Prevención de doble uso
```

## 🔐 Seguridad del Sistema

### Encriptación
- **Algoritmo**: Fernet (AES 128 en modo CBC)
- **Clave**: Configurada en `TICKET_ENCRYPTION_KEY`
- **Rotación**: Soporta rotación de claves
- **Integridad**: Hash SHA-256 adicional

### Prevención de Fraude
- **Datos Inmutables**: QR contiene IDs que no pueden modificarse
- **Timestamp Validation**: Previene QRs antiguos reutilizados
- **Usage Tracking**: Control estricto de usos
- **Audit Trail**: Log completo de todas las validaciones

### Validación Offline (Futuro)
- QR contiene datos suficientes para validación básica
- Hash de validación para verificar integridad
- Sincronización posterior de validaciones offline

## 📱 Interfaces de Validación

### 1. **Interfaz Web de Validación**
```
URL: /tickets/validate/
- Campo de entrada para QR o número de ticket
- Botones: "Validar y Usar" / "Solo Verificar"
- Resultado en tiempo real
- Shortcuts de teclado (F1, F2, Escape)
- Auto-limpieza después de validación exitosa
```

### 2. **API REST para Validación**
```python
POST /api/v1/tickets/validate_ticket/
{
    "qr_code_data": "BASE64_ENCRYPTED_DATA",
    "validation_system_id": "entrance_gate_1",
    "validation_location": "Main Entrance",
    "mark_as_used": true
}

Response:
{
    "valid": true,
    "ticket_number": "001-001-01",
    "customer_name": "Juan Pérez",
    "event_name": "Concierto Rock",
    "seat_label": "Platea - Fila A, Asiento 15",
    "usage_count": 1,
    "max_usage": 1,
    "remaining_uses": 0,
    "validation_timestamp": "2024-11-01T20:30:00Z"
}
```

### 3. **Validación por Lotes**
```python
POST /api/v1/tickets/validation-logs/bulk_validate/
{
    "ticket_identifiers": ["QR1", "QR2", "TICKET-001"],
    "validation_system_id": "bulk_scanner",
    "mark_as_used": true
}
```

### 4. **Multi-Entrada (Eventos de Múltiples Días)**
```python
POST /api/v1/tickets/validate_multi_entry/
{
    "qr_code_data": "BASE64_DATA",
    "action": "check_in",  # o "check_out"
    "validation_system_id": "day_pass_gate"
}
```

## 📊 Dashboard de Validación

### Estadísticas en Tiempo Real
- **Total de validaciones** (hoy/histórico)
- **Tasa de éxito** (válidos vs inválidos)
- **Validaciones por método** (QR vs número)
- **Validaciones por sistema** (puerta 1, 2, etc.)
- **Actividad reciente** (últimas 24 horas)

### Log de Auditoría
```python
class TicketValidationLog:
    ticket = ForeignKey(DigitalTicket)
    validation_result = BooleanField()  # Éxito/Fallo
    validation_method = ['qr_code', 'ticket_number', 'manual']
    validation_system_id = CharField()  # ID del sistema validador
    validation_location = CharField()   # Ubicación física
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    validated_at = DateTimeField()
    metadata = JSONField()  # Datos adicionales
```

## 🎨 Personalización de Tickets

### Templates de Tickets
```python
class TicketTemplate:
    template_type = ['pdf', 'email', 'mobile']
    html_content = TextField()  # HTML con placeholders
    css_styles = TextField()    # Estilos CSS
    include_qr_code = BooleanField()
    include_logo = BooleanField()
    is_default = BooleanField()
```

### Variables Disponibles en Templates
```html
{{ ticket.ticket_number }}
{{ event.name }}
{{ event.start_date }}
{{ venue.name }}
{{ customer.full_name }}
{{ zone.name }}
{{ seat.seat_label }}
{{ ticket.qr_code_image.url }}
{{ ticket.total_price }}
```

### Generación de PDF
- **ReportLab**: Para PDFs programáticos
- **WeasyPrint**: Para PDFs desde HTML/CSS (opcional)
- **Plantillas**: Personalizables por tenant
- **Elementos**: Logo, QR, información del evento, términos

## 📧 Entrega de Tickets

### Métodos de Entrega
```python
# Email con PDF adjunto
TicketDeliveryService.send_ticket_email(ticket, custom_message)

# SMS con información básica
TicketDeliveryService.send_ticket_sms(ticket, custom_message)

# WhatsApp con formato enriquecido
TicketDeliveryService.send_ticket_whatsapp(ticket, custom_message)
```

### Reenvío de Tickets
- **API Endpoint**: `/api/v1/tickets/resend/`
- **Métodos**: Email, SMS, WhatsApp
- **Filtros**: Por ticket, cliente, evento
- **Personalización**: Mensaje personalizado

## 🔧 Configuración del Sistema

### Variables de Entorno
```bash
# Encriptación
TICKET_ENCRYPTION_KEY=base64_encoded_fernet_key

# Validación
TICKET_VALIDATION_WINDOW_HOURS=1  # Ventana antes del evento
TICKET_GRACE_PERIOD_HOURS=2       # Gracia después del evento
TICKET_MAX_USAGE_DEFAULT=1        # Usos por defecto

# QR Code
QR_CODE_ERROR_CORRECTION=L         # L, M, Q, H
QR_CODE_BOX_SIZE=10               # Tamaño de caja
QR_CODE_BORDER=4                  # Borde
```

### Por Tenant
```python
class TenantSettings:
    ticket_template_pdf = ForeignKey(TicketTemplate)
    ticket_template_email = ForeignKey(TicketTemplate)
    auto_generate_tickets = BooleanField(default=True)
    auto_send_tickets = BooleanField(default=True)
    validation_grace_period = IntegerField(default=2)  # horas
```

## 📱 Casos de Uso Comunes

### 1. **Evento Simple (Concierto)**
```
1. Cliente compra ticket online
2. Sistema genera ticket digital con QR
3. Cliente recibe email con PDF del ticket
4. En el evento: escanean QR en entrada
5. Sistema valida y marca como usado
6. Cliente entra al evento
```

### 2. **Evento con Asientos Numerados (Teatro)**
```
1. Cliente selecciona asiento específico
2. Ticket incluye información de fila y asiento
3. QR contiene datos del asiento
4. Validación verifica asiento correcto
5. Acomodador puede verificar ubicación
```

### 3. **Evento Multi-Día (Festival)**
```
1. Ticket configurado para múltiples usos
2. max_usage_count = 3 (3 días)
3. Cada día: check-in con QR
4. Sistema rastrea usos: 1/3, 2/3, 3/3
5. Después del último uso: ticket marcado como 'used'
```

### 4. **Validación Offline (Emergencia)**
```
1. QR contiene datos básicos del ticket
2. App móvil puede validar sin internet
3. Verificación de hash de integridad
4. Sincronización posterior cuando hay conexión
```

## 🚀 Ventajas del Sistema

### Para Organizadores
- **Control Total**: Seguimiento en tiempo real de entradas
- **Prevención de Fraude**: Encriptación y validación robusta
- **Flexibilidad**: Múltiples tipos de eventos y configuraciones
- **Auditoría Completa**: Log detallado de todas las validaciones
- **Escalabilidad**: Soporta eventos masivos

### Para Clientes
- **Conveniencia**: Ticket digital en el móvil
- **Seguridad**: No se puede perder o falsificar fácilmente
- **Información Completa**: Todos los detalles en un lugar
- **Múltiples Formatos**: PDF, email, SMS, WhatsApp

### Para Personal de Entrada
- **Validación Rápida**: Escaneo instantáneo
- **Información Clara**: Datos del cliente y evento visibles
- **Múltiples Métodos**: QR o número de ticket
- **Dashboard en Tiempo Real**: Estadísticas y monitoreo

## 🔮 Funcionalidades Avanzadas

### Próximas Mejoras
- **NFC Support**: Validación por proximidad
- **Blockchain Verification**: Inmutabilidad adicional
- **AI Fraud Detection**: Detección de patrones sospechosos
- **Mobile App**: App dedicada para validadores
- **Geofencing**: Validación por ubicación GPS
- **Biometric Integration**: Validación biométrica adicional

El sistema de entradas QR del Venezuelan POS es una solución completa, segura y escalable que cubre todos los aspectos desde la generación hasta la validación de tickets digitales, proporcionando una experiencia fluida tanto para organizadores como para asistentes.