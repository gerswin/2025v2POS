# 🔒 Sistema de Bloqueo Temporal de Items en Carrito

## 🎯 Objetivo
Prevenir overselling mediante bloqueo automático de items por 15 minutos al agregarlos al carrito, con liberación automática o manual.

## 🏗️ Arquitectura del Sistema

### 1. **Modelo de Bloqueo Temporal**
```python
class CartItemLock(TenantAwareModel):
    """Bloqueo temporal de items en carrito para prevenir overselling."""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        RELEASED = 'released', 'Released'
        CONVERTED = 'converted', 'Converted to Sale'
    
    # Identificación
    session_key = models.CharField(max_length=40)  # Django session key
    user = models.ForeignKey(User, null=True, blank=True)  # Usuario si está logueado
    
    # Item bloqueado
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, null=True, blank=True)  # Para asientos numerados
    quantity = models.PositiveIntegerField(default=1)  # Para admisión general
    
    # Control temporal
    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # locked_at + 15 minutos
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    
    # Metadatos
    price_at_lock = models.DecimalField(max_digits=10, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True)
```

### 2. **Servicio de Gestión de Bloqueos**
```python
class CartLockService:
    LOCK_DURATION_MINUTES = 15
    
    @classmethod
    def lock_items(cls, session_key, user, items_data):
        """Bloquear items al agregarlos al carrito."""
        
    @classmethod
    def release_locks(cls, session_key, item_keys=None):
        """Liberar bloqueos específicos o todos de una sesión."""
        
    @classmethod
    def extend_locks(cls, session_key, minutes=15):
        """Extender bloqueos existentes."""
        
    @classmethod
    def cleanup_expired_locks(cls):
        """Limpiar bloqueos expirados (tarea Celery)."""
```

### 3. **Integración con Disponibilidad**
```python
# En Zone.available_capacity
def available_capacity(self):
    if self.zone_type == self.ZoneType.NUMBERED:
        # Excluir asientos bloqueados
        locked_seats = CartItemLock.objects.filter(
            zone=self,
            seat__isnull=False,
            status=CartItemLock.Status.ACTIVE,
            expires_at__gt=timezone.now()
        ).values_list('seat_id', flat=True)
        
        return self.seats.filter(
            status=Seat.Status.AVAILABLE
        ).exclude(id__in=locked_seats).count()
    else:
        # Para admisión general, restar tickets bloqueados
        locked_quantity = CartItemLock.objects.filter(
            zone=self,
            seat__isnull=True,
            status=CartItemLock.Status.ACTIVE,
            expires_at__gt=timezone.now()
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        sold_tickets = self.get_sold_tickets_count()
        return max(self.capacity - sold_tickets - locked_quantity, 0)
```

## 🔄 Flujo de Operaciones

### 1. **Agregar al Carrito**
```
Usuario selecciona items → Verificar disponibilidad → Crear bloqueos → Agregar al carrito
```

### 2. **Checkout**
```
Iniciar checkout → Verificar bloqueos válidos → Convertir a venta → Marcar bloqueos como CONVERTED
```

### 3. **Expiración Automática**
```
Cada 5 minutos → Tarea Celery → Marcar bloqueos expirados → Liberar items → Actualizar cache
```

### 4. **Liberación Manual**
```
Usuario abandona carrito → Endpoint de liberación → Marcar como RELEASED → Actualizar disponibilidad
```

## 🛠️ Implementación Técnica

### Endpoints API
- `POST /sales/cart/lock/` - Bloquear items
- `DELETE /sales/cart/lock/` - Liberar bloqueos
- `PUT /sales/cart/lock/extend/` - Extender bloqueos
- `GET /sales/cart/lock/status/` - Estado de bloqueos

### Integración Frontend
- Timer visual de expiración
- Notificaciones de bloqueo/liberación
- Auto-extensión antes de expirar
- Liberación al cerrar pestaña

### Monitoreo
- Dashboard de bloqueos activos
- Métricas de conversión carrito→venta
- Alertas de bloqueos masivos
- Análisis de abandono de carrito

## 🎛️ Configuración

### Variables de Entorno
```python
CART_LOCK_DURATION_MINUTES = 15
CART_LOCK_CLEANUP_INTERVAL = 5
CART_LOCK_WARNING_MINUTES = 2
MAX_LOCKS_PER_SESSION = 50
```

### Por Tenant
```python
class TenantSettings:
    cart_lock_duration = models.IntegerField(default=15)
    max_locks_per_session = models.IntegerField(default=50)
    auto_extend_locks = models.BooleanField(default=True)
```