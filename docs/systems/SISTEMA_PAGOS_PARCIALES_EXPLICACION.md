# 💳 Sistema de Pagos Parciales (Abonos) - Venezuelan POS

## 🎯 **Resumen del Sistema**

El Venezuelan POS System implementa un **sistema completo de pagos parciales** que permite a los clientes comprar tickets mediante:
- **Planes de Cuotas Fijas** (Installment Plans)
- **Pagos Flexibles** (Flexible Payments)
- **Reservas Temporales** con expiración automática

---

## 🏗️ **Arquitectura del Sistema**

### **Modelos Principales:**

#### **1. PaymentPlan (Plan de Pagos)**
```python
class PaymentPlan(TenantAwareModel):
    # Tipos de planes
    class PlanType(models.TextChoices):
        INSTALLMENT = 'installment'  # Cuotas fijas
        FLEXIBLE = 'flexible'        # Pagos flexibles
    
    # Campos principales
    transaction = OneToOneField(Transaction)  # Una transacción = un plan
    customer = ForeignKey(Customer)
    plan_type = CharField(choices=PlanType.choices)
    
    # Montos
    total_amount = DecimalField()      # Monto total a pagar
    paid_amount = DecimalField()       # Monto ya pagado
    remaining_balance = DecimalField() # Saldo pendiente
    
    # Para planes de cuotas
    installment_count = PositiveIntegerField()  # Número de cuotas
    installment_amount = DecimalField()         # Monto por cuota
    
    # Timing
    expires_at = DateTimeField()  # Cuándo expira el plan
    completed_at = DateTimeField() # Cuándo se completó
```

#### **2. ReservedTicket (Tickets Reservados)**
```python
class ReservedTicket(TenantAwareModel):
    transaction = ForeignKey(Transaction)
    seat = ForeignKey(Seat)           # Para asientos numerados
    zone = ForeignKey(Zone)           # Para admisión general
    quantity = PositiveIntegerField() # Cantidad reservada
    reserved_until = DateTimeField()  # Hasta cuándo está reservado
    status = CharField()              # active, expired, completed, cancelled
```

#### **3. Payment (Pagos Individuales)**
```python
class Payment(TenantAwareModel):
    transaction = ForeignKey(Transaction)
    payment_plan = ForeignKey(PaymentPlan)  # Opcional
    payment_method = ForeignKey(PaymentMethod)
    
    amount = DecimalField()           # Monto del pago
    processing_fee = DecimalField()   # Comisión
    net_amount = DecimalField()       # Monto neto
    
    status = CharField()              # pending, completed, failed, etc.
    reference_number = CharField()    # Referencia bancaria
```

---

## 🔄 **Flujo de Pagos Parciales**

### **Paso 1: Configuración del Evento**
```python
# EventConfiguration - Habilitar pagos parciales
event_config = EventConfiguration.objects.create(
    event=event,
    partial_payments_enabled=True,
    installment_plans_enabled=True,
    flexible_payments_enabled=True,
    max_installments=3,                    # Máximo 3 cuotas
    min_down_payment_percentage=25.00,     # Mínimo 25% inicial
    payment_plan_expiry_days=30            # Expira en 30 días
)
```

### **Paso 2: Creación de Transacción con Reserva**
```python
# 1. Cliente selecciona asientos/tickets
# 2. Se crea transacción en estado RESERVED
transaction = Transaction.objects.create(
    tenant=tenant,
    event=event,
    customer=customer,
    status=Transaction.Status.RESERVED,  # ⚠️ No COMPLETED aún
    total_amount=Decimal('150.00')
)

# 3. Se crean reservas temporales de asientos
for seat in selected_seats:
    ReservedTicket.objects.create(
        tenant=tenant,
        transaction=transaction,
        seat=seat,
        zone=seat.zone,
        reserved_until=timezone.now() + timedelta(hours=72),  # 72 horas
        status=ReservedTicket.Status.ACTIVE
    )
```

### **Paso 3: Creación del Plan de Pagos**

#### **Opción A: Plan de Cuotas Fijas**
```python
# POST /api/v1/payments/payment-plans/
{
    \"transaction_id\": \"uuid-transaction\",
    \"plan_type\": \"installment\",
    \"installment_count\": 3,
    \"expires_at\": \"2024-12-31T23:59:59Z\"
}

# Resultado: 3 cuotas de $50 cada una
payment_plan = PaymentPlan.objects.create(
    transaction=transaction,
    customer=customer,
    plan_type=PaymentPlan.PlanType.INSTALLMENT,
    total_amount=Decimal('150.00'),
    installment_count=3,
    installment_amount=Decimal('50.00'),  # 150/3 = 50
    expires_at=expires_at
)
```

#### **Opción B: Plan Flexible**
```python
# POST /api/v1/payments/payment-plans/
{
    \"transaction_id\": \"uuid-transaction\",
    \"plan_type\": \"flexible\",
    \"expires_at\": \"2024-12-31T23:59:59Z\"
}

# Resultado: Cliente puede pagar cualquier monto cuando quiera
payment_plan = PaymentPlan.objects.create(
    transaction=transaction,
    customer=customer,
    plan_type=PaymentPlan.PlanType.FLEXIBLE,
    total_amount=Decimal('150.00'),
    expires_at=expires_at
)
```

### **Paso 4: Procesamiento de Abonos**

#### **Primer Pago (Abono Inicial)**
```python
# POST /api/v1/payments/payments/
{
    \"transaction_id\": \"uuid-transaction\",
    \"payment_method_id\": \"uuid-payment-method\",
    \"amount\": \"50.00\",
    \"reference_number\": \"REF123456\"
}

# Se crea el pago
payment = Payment.objects.create(
    transaction=transaction,
    payment_plan=payment_plan,
    payment_method=payment_method,
    amount=Decimal('50.00'),
    status=Payment.Status.PENDING
)

# POST /api/v1/payments/payments/{payment_id}/mark_completed/
# Al completarse:
payment_plan.add_payment(Decimal('50.00'))
# paid_amount: 50.00
# remaining_balance: 100.00
# Status: ACTIVE (aún no completado)
```

#### **Segundo Pago**
```python
# Otro abono de $50
payment_plan.add_payment(Decimal('50.00'))
# paid_amount: 100.00
# remaining_balance: 50.00
# Status: ACTIVE
```

#### **Pago Final**
```python
# Último abono de $50
payment_plan.add_payment(Decimal('50.00'))
# paid_amount: 150.00
# remaining_balance: 0.00
# Status: COMPLETED ✅
# completed_at: timezone.now()

# 🎉 Al completarse el plan:
transaction.status = Transaction.Status.COMPLETED
transaction.save()

# Las reservas se convierten en tickets reales
for reservation in transaction.reserved_tickets.all():
    reservation.status = ReservedTicket.Status.COMPLETED
```

---

## 📊 **Estados y Transiciones**

### **Estados de PaymentPlan:**
- **ACTIVE** → Plan activo, aceptando pagos
- **COMPLETED** → Plan completado, transacción finalizada
- **EXPIRED** → Plan expirado, reservas liberadas
- **CANCELLED** → Plan cancelado manualmente

### **Estados de ReservedTicket:**
- **ACTIVE** → Asiento reservado temporalmente
- **COMPLETED** → Reserva convertida en ticket real
- **EXPIRED** → Reserva expirada, asiento liberado
- **CANCELLED** → Reserva cancelada

### **Estados de Payment:**
- **PENDING** → Pago creado, esperando procesamiento
- **PROCESSING** → Pago en proceso
- **COMPLETED** → Pago completado exitosamente
- **FAILED** → Pago falló
- **CANCELLED** → Pago cancelado
- **REFUNDED** → Pago reembolsado

---

## 🔧 **APIs Disponibles**

### **Gestión de Planes de Pago**
```bash
# Crear plan de cuotas
POST /api/v1/payments/payment-plans/
{
    \"transaction_id\": \"uuid\",
    \"plan_type\": \"installment\",
    \"installment_count\": 3,
    \"expires_at\": \"2024-12-31T23:59:59Z\"
}

# Crear plan flexible
POST /api/v1/payments/payment-plans/
{
    \"transaction_id\": \"uuid\",
    \"plan_type\": \"flexible\",
    \"expires_at\": \"2024-12-31T23:59:59Z\"
}

# Listar planes activos
GET /api/v1/payments/payment-plans/active/

# Extender expiración
POST /api/v1/payments/payment-plans/{id}/extend_expiry/
{
    \"expires_at\": \"2025-01-31T23:59:59Z\"
}

# Cancelar plan
POST /api/v1/payments/payment-plans/{id}/cancel/
```

### **Procesamiento de Pagos**
```bash
# Crear pago (abono)
POST /api/v1/payments/payments/
{
    \"transaction_id\": \"uuid\",
    \"payment_method_id\": \"uuid\",
    \"amount\": \"50.00\",
    \"currency\": \"USD\",
    \"reference_number\": \"REF123\"
}

# Completar pago
POST /api/v1/payments/payments/{id}/mark_completed/
{
    \"external_transaction_id\": \"BANK_TXN_123\",
    \"processor_response\": {\"status\": \"approved\"}
}

# Marcar como fallido
POST /api/v1/payments/payments/{id}/mark_failed/
{
    \"notes\": \"Fondos insuficientes\"
}
```

---

## ⚡ **Funcionalidades Avanzadas**

### **1. Validación de Pagos**
```python
# Para planes de cuotas: monto debe ser exacto
if plan_type == PaymentPlan.PlanType.INSTALLMENT:
    expected_amount = payment_plan.next_installment_amount
    if amount != expected_amount:
        raise ValidationError(f\"Debe pagar exactamente {expected_amount}\")

# Para planes flexibles: cualquier monto válido
if amount > payment_plan.remaining_balance:
    raise ValidationError(\"Monto excede saldo pendiente\")
```

### **2. Expiración Automática**
```python
# Tarea Celery que se ejecuta cada 5 minutos
@shared_task
def cleanup_expired_reservations():
    expired_plans = PaymentPlan.objects.filter(
        status=PaymentPlan.Status.ACTIVE,
        expires_at__lte=timezone.now()
    )
    
    for plan in expired_plans:
        plan.expire()  # Libera reservas y marca como expirado
```

### **3. Notificaciones Automáticas**
```python
# Al recibir un abono
def _send_payment_received_notification(self):
    context = {
        'customer': self.transaction.customer,
        'amount_paid': self.amount,
        'remaining_balance': self.payment_plan.remaining_balance,
        'next_installment': self.payment_plan.next_installment_amount
    }
    
    NotificationService.send_notification(
        template_name='payment_received',
        recipient=customer.email,
        channel='email',
        context=context
    )
```

### **4. Integración Fiscal**
```python
# Solo se genera serie fiscal al completar el plan
if payment_plan.is_completed:
    # Generar serie fiscal consecutiva
    fiscal_series = FiscalSeriesCounter.objects.get_next_series(
        tenant=transaction.tenant,
        event=transaction.event
    )
    transaction.fiscal_series = fiscal_series
    transaction.save()
```

---

## 📈 **Métricas y Reportes**

### **Propiedades Útiles del PaymentPlan:**
```python
# Porcentaje de completitud
payment_plan.completion_percentage  # 66.67% si pagó 2 de 3 cuotas

# Cuotas pagadas/pendientes
payment_plan.installments_paid      # 2
payment_plan.installments_remaining # 1

# Próximo monto a pagar
payment_plan.next_installment_amount # 50.00

# Validar si puede recibir pago
can_pay, message = payment_plan.can_accept_payment(Decimal('50.00'))
```

### **Estadísticas de Pagos:**
```bash
# Resumen de pagos
GET /api/v1/payments/payments/summary/
{
    \"total_amount\": \"1500.00\",
    \"total_count\": 30,
    \"by_method\": {
        \"Efectivo\": {\"total_amount\": \"500.00\", \"total_count\": 10},
        \"Transferencia\": {\"total_amount\": \"1000.00\", \"total_count\": 20}
    },
    \"by_status\": {
        \"Completado\": {\"total_amount\": \"1200.00\", \"total_count\": 24},
        \"Pendiente\": {\"total_amount\": \"300.00\", \"total_count\": 6}
    }
}
```

---

## 🎯 **Casos de Uso Reales**

### **Caso 1: Concierto de $150 en 3 cuotas**
```
1. Cliente selecciona asiento → Reserva por 72 horas
2. Crea plan de 3 cuotas de $50 cada una
3. Paga 1ra cuota → Reserva se mantiene
4. Paga 2da cuota → Reserva se mantiene  
5. Paga 3ra cuota → ✅ Ticket generado con QR
```

### **Caso 2: Evento corporativo con pagos flexibles**
```
1. Empresa reserva 50 tickets por $5000
2. Crea plan flexible con 60 días de plazo
3. Paga $2000 inicial → Reserva activa
4. Paga $1500 a los 15 días → Reserva activa
5. Paga $1500 final → ✅ 50 tickets generados
```

### **Caso 3: Plan expirado**
```
1. Cliente reserva ticket por $100
2. Crea plan de 2 cuotas, expira en 30 días
3. Paga 1ra cuota de $50 → OK
4. No paga 2da cuota en 30 días → ❌ Plan expira
5. Reserva se libera automáticamente
6. Asiento queda disponible para otros
```

---

## 🔒 **Seguridad y Validaciones**

### **Prevención de Overselling:**
- Reservas temporales bloquean asientos
- Solo un plan activo por transacción
- Validación atómica de disponibilidad

### **Integridad Fiscal:**
- Series fiscales solo al completar pago total
- Auditoría completa de todos los abonos
- Trazabilidad de cada pago individual

### **Gestión de Expiración:**
- Cleanup automático cada 5 minutos
- Liberación inmediata de reservas expiradas
- Notificaciones de recordatorio antes de expirar

---

## 🎉 **Conclusión**

El sistema de pagos parciales del Venezuelan POS es **robusto y completo**, ofreciendo:

✅ **Flexibilidad** - Cuotas fijas o pagos variables  
✅ **Seguridad** - Reservas temporales sin overselling  
✅ **Automatización** - Expiración y cleanup automático  
✅ **Trazabilidad** - Auditoría completa de cada abono  
✅ **Integración** - Fiscal, notificaciones, reportes  
✅ **APIs Completas** - Gestión total vía REST API  

**El sistema está 100% implementado y funcional** para manejar cualquier escenario de pagos parciales en eventos.