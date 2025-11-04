# 7. Pagos Parciales y Planes de Pago

## Introducción

El sistema de **pagos parciales** permite a sus clientes reservar tickets sin pagar el monto completo de inmediato. Esto aumenta las ventas y facilita el acceso a eventos de alto costo.

---

## 💳 ¿Qué son los Planes de Pago?

Los planes de pago permiten dividir el costo total de una compra en múltiples pagos más pequeños y manejables.

### Beneficios

**Para el Cliente:**
- Acceso a eventos de alto costo
- Flexibilidad financiera
- Reserva inmediata con pago inicial
- Opciones de pago cómodas

**Para el Organizador:**
- Aumento en ventas
- Reducción de cancelaciones
- Cash flow predecible
- Mayor alcance de público

---

## 🎯 Tipos de Planes de Pago

### 1. Plan Flexible

El cliente define cuánto y cuándo pagar dentro de un plazo límite.

**Características:**
```
✓ Cliente controla monto de cada pago
✓ Fecha límite definida
✓ Mínimo inicial requerido
✓ Ideal para eventos lejanos
```

**Ejemplo:**
```
Evento: Concierto Premium
Costo Total: $500

Plan Flexible:
├── Pago inicial mínimo: $100 (20%)
├── Fecha límite: 30 días antes del evento
├── Cliente decide: Cuando pagar el resto
└── Opciones: Semanal, quincenal, mensual
```

### 2. Plan de Cuotas (Installments)

El sistema divide el costo en cuotas fijas y automáticas.

**Características:**
```
✓ Cuotas iguales predefinidas
✓ Fechas automáticas
✓ Recordatorios programados
✓ Ideal para eventos premium
```

**Ejemplo:**
```
Evento: Festival de 3 Días
Costo Total: $600

Plan de 4 Cuotas:
├── Cuota 1 (Inicial): $150 - Hoy
├── Cuota 2: $150 - En 30 días
├── Cuota 3: $150 - En 60 días
└── Cuota 4: $150 - En 90 días
```

---

## ✅ Configurar Planes de Pago para un Evento

### Paso 1: Acceder a Configuración

1. Vaya a **Eventos** → Seleccione el evento
2. Haga clic en **Editar Evento**
3. Vaya a la sección **Configuración de Pagos**

### Paso 2: Habilitar Pagos Parciales

**Activar la Función:**
```
☑ Permitir pagos parciales
```

### Paso 3: Configurar Parámetros

#### Pago Inicial Mínimo

**Porcentaje Mínimo:**
```
Ejemplo: 20%
```
- Mínimo que el cliente debe pagar inicialmente
- Típicamente entre 10% - 50%
- Asegura compromiso del cliente

**Monto Mínimo Absoluto:**
```
Ejemplo: $50
```
- Valor mínimo en dinero
- Evita cuotas muy pequeñas

#### Fecha Límite de Pago

**Días Antes del Evento:**
```
Recomendado: 7 días
```
- Todo debe estar pagado antes de esta fecha
- Permite tiempo para procesamiento
- Evita problemas de último momento

**Fecha Específica:**
```
Ejemplo: 2025-12-15
```
- Para eventos con fecha de corte específica

#### Número de Cuotas Permitidas

**Para Planes de Cuotas:**
```
Mínimo: 2 cuotas
Máximo: 12 cuotas
Recomendado: 3-6 cuotas
```

#### Recargos por Pagos Parciales

**Cargo Administrativo:**
```
Opciones:
- Porcentaje: 5% del total
- Monto fijo: $10 por plan
- Sin cargo
```

### Paso 4: Configurar Recordatorios

**Notificaciones Automáticas:**
```
☑ Email cuando se crea el plan
☑ Recordatorio 7 días antes de cuota
☑ Recordatorio 3 días antes de cuota
☑ Recordatorio 1 día antes de cuota
☑ Alerta de pago vencido
☑ Confirmación de pago completado
```

### Paso 5: Guardar Configuración

1. Revise todas las configuraciones
2. Haga clic en **Guardar**
3. El sistema validará los parámetros

---

## 💰 Crear un Plan de Pago (Proceso de Venta)

### Flujo Normal de Venta con Plan de Pago

#### 1. Selección de Tickets

El cliente selecciona sus tickets normalmente:
```
Evento: Concierto Rock
Zona: VIP - Fila A, Asientos 5-6
Cantidad: 2 tickets
Precio unitario: $250
Total: $500
```

#### 2. En el Carrito

El cliente ve opciones de pago:
```
┌─────────────────────────────────┐
│ RESUMEN DE COMPRA               │
├─────────────────────────────────┤
│ Total: $500                     │
│                                 │
│ Opciones de Pago:               │
│ ○ Pago Completo ($500)          │
│ ● Plan de Pago Parcial          │
└─────────────────────────────────┘
```

#### 3. Configurar Plan

**Si el cliente selecciona Plan de Pago:**

**Opción A: Plan Flexible**
```
┌─────────────────────────────────┐
│ PLAN DE PAGO FLEXIBLE           │
├─────────────────────────────────┤
│ Total a Pagar: $500             │
│                                 │
│ Pago Inicial:                   │
│ Mínimo: $100 (20%)              │
│ Ingrese: [____] ($)             │
│                                 │
│ Fecha Límite:                   │
│ 2025-12-25                      │
│                                 │
│ Saldo Restante: $XXX            │
│ Cuotas Sugeridas: X pagos       │
└─────────────────────────────────┘
```

**Opción B: Plan de Cuotas**
```
┌─────────────────────────────────┐
│ PLAN DE CUOTAS                  │
├─────────────────────────────────┤
│ Total a Pagar: $500             │
│                                 │
│ Seleccione Plan:                │
│ ○ 2 cuotas de $250              │
│ ○ 3 cuotas de $166.67           │
│ ● 4 cuotas de $125              │
│ ○ 6 cuotas de $83.33            │
│                                 │
│ Calendario de Pagos:            │
│ ├─ Cuota 1: Hoy - $125          │
│ ├─ Cuota 2: 30 días - $125      │
│ ├─ Cuota 3: 60 días - $125      │
│ └─ Cuota 4: 90 días - $125      │
└─────────────────────────────────┘
```

#### 4. Información del Cliente

Capture información adicional:
```
Nombre Completo: _______________
Email: __________________________
Teléfono: _______________________
Documento: ______________________

☑ Acepto términos y condiciones del plan de pago
☑ Acepto recibir recordatorios de pago
```

#### 5. Pago Inicial

Procese el primer pago:
```
Método de Pago:
○ Tarjeta de Crédito
○ Transferencia Bancaria
● Efectivo
○ Pago Móvil
```

#### 6. Confirmación

Sistema genera:
```
✓ Plan de Pago Creado: #PP-001234
✓ Referencia de Transacción: #TX-567890
✓ Email de Confirmación Enviado
✓ Tickets Reservados (No Emitidos)
```

---

## 📊 Gestionar Planes de Pago

### Panel de Control

Acceda a **Pagos** → **Planes de Pago**

**Vista Principal:**
```
┌──────────────────────────────────────────────────┐
│ PLANES DE PAGO ACTIVOS                           │
├──────────────────────────────────────────────────┤
│                                                  │
│ Filtros:                                         │
│ Estado: [Todos ▼] Evento: [Todos ▼]             │
│                                                  │
│ Lista de Planes:                                 │
│                                                  │
│ #PP-001234 | Juan Pérez                          │
│ Evento: Concierto Rock | Total: $500             │
│ ██████████░░░░░░ 60% Pagado                      │
│ Próxima cuota: $125 - 15/12/2025                 │
│ [Ver Detalle] [Registrar Pago]                   │
│                                                  │
│ #PP-001235 | María González                      │
│ Evento: Festival Jazz | Total: $300              │
│ ████░░░░░░░░░░░░ 25% Pagado                      │
│ Próxima cuota: $75 - 10/12/2025 ⚠️ Vencida       │
│ [Ver Detalle] [Registrar Pago]                   │
└──────────────────────────────────────────────────┘
```

### Estados de Planes de Pago

**Activo (Active)** 🟢
- Plan en curso
- Pagos al día
- Sin retrasos

**Vencido (Overdue)** 🟡
- Pago retrasado
- Requiere atención
- Dentro de período de gracia

**Completado (Completed)** ✅
- Todo pagado
- Tickets emitidos
- Plan finalizado

**Cancelado (Cancelled)** 🔴
- Cliente canceló
- Reembolso procesado (si aplica)
- Tickets liberados

**Expirado (Expired)** ⚫
- Plazo vencido sin completar
- Tickets liberados
- Acción requerida

---

## 💵 Registrar Pagos Manualmente

### Cuando un Cliente Paga

#### Paso 1: Localizar el Plan

1. Vaya a **Pagos** → **Planes de Pago**
2. Busque por:
   - Número de plan
   - Nombre del cliente
   - Evento
   - Número de documento

#### Paso 2: Registrar Pago

1. Haga clic en el plan
2. Click en **Registrar Pago**
3. Complete el formulario:

```
┌─────────────────────────────────┐
│ REGISTRAR PAGO                  │
├─────────────────────────────────┤
│ Plan: #PP-001234                │
│ Cliente: Juan Pérez             │
│ Saldo Pendiente: $300           │
│                                 │
│ Monto a Pagar:                  │
│ [____] USD                      │
│                                 │
│ Método de Pago:                 │
│ [Seleccione ▼]                  │
│                                 │
│ Referencia/Comprobante:         │
│ [____________________]          │
│                                 │
│ Fecha del Pago:                 │
│ [03/11/2025]                    │
│                                 │
│ Notas:                          │
│ [____________________]          │
│                                 │
│ [Cancelar] [Registrar Pago]    │
└─────────────────────────────────┘
```

#### Paso 3: Confirmación

Sistema actualiza:
```
✓ Pago registrado: $125
✓ Saldo actualizado: $175 restantes
✓ Progreso: 65%
✓ Email enviado al cliente
✓ Próxima cuota: $125 - 15/01/2026
```

#### Paso 4: Si es el Último Pago

```
✓ Plan de Pago COMPLETADO
✓ Tickets emitidos automáticamente
✓ Email con tickets adjunto
✓ Cliente puede descargar tickets
✓ Asientos confirmados definitivamente
```

---

## 📧 Notificaciones y Recordatorios

### Emails Automáticos

#### 1. Confirmación de Plan Creado

**Enviado:** Inmediatamente después de crear el plan

**Contenido:**
```
Asunto: Plan de Pago Creado - Concierto Rock

Hola Juan,

Su plan de pago ha sido creado exitosamente.

Detalles:
- Plan: #PP-001234
- Evento: Concierto Rock
- Fecha del Evento: 30/12/2025
- Total: $500
- Pagado: $125 (25%)
- Saldo: $375

Próximos Pagos:
- 15/12/2025: $125
- 15/01/2026: $125
- 15/02/2026: $125

[Ver Mi Plan] [Pagar Ahora]
```

#### 2. Recordatorio de Cuota Próxima

**Enviado:** 7, 3, y 1 días antes de la fecha de vencimiento

**Contenido:**
```
Asunto: Recordatorio: Cuota vence en 3 días

Hola Juan,

Recordatorio amistoso: Su próxima cuota vence pronto.

Monto: $125
Fecha de Vencimiento: 15/12/2025
Plan: #PP-001234

[Pagar Ahora]
```

#### 3. Pago Recibido

**Enviado:** Después de cada pago exitoso

**Contenido:**
```
Asunto: Pago Recibido - $125

Hola Juan,

Hemos recibido su pago. ¡Gracias!

Monto: $125
Referencia: #PAY-78910
Saldo Restante: $250 (50%)

Próximo Pago: 15/01/2026 - $125

[Ver Estado del Plan]
```

#### 4. Pago Vencido

**Enviado:** Si no se recibe pago en la fecha

**Contenido:**
```
Asunto: ⚠️ Cuota Vencida - Acción Requerida

Hola Juan,

Su cuota del 15/12/2025 está vencida.

Monto Pendiente: $125
Días de Retraso: 2

Por favor, realice su pago lo antes posible para
mantener su reserva.

[Pagar Ahora] [Contactar Soporte]
```

#### 5. Plan Completado

**Enviado:** Al recibir el último pago

**Contenido:**
```
Asunto: ✅ ¡Plan Completado! - Sus Tickets

Hola Juan,

¡Felicidades! Su plan de pago está completo.

Sus tickets están adjuntos a este email.

Evento: Concierto Rock
Fecha: 30/12/2025
Tickets: 2 x VIP Fila A
Asientos: A5, A6

[Descargar Tickets] [Ver Detalles]
```

---

## 🔔 Gestión de Pagos Vencidos

### Proceso de Seguimiento

#### Día 0: Fecha de Vencimiento
```
✓ Email automático de recordatorio
✓ Estado: "Pending"
```

#### Día +1: Un Día de Retraso
```
⚠️ Email de recordatorio
⚠️ Estado: "Overdue"
⚠️ Marca en el panel de control
```

#### Día +3: Tres Días de Retraso
```
⚠️ Email urgente
⚠️ Notificación al administrador
⚠️ Contacto telefónico sugerido
```

#### Día +7: Una Semana de Retraso
```
🔴 Último recordatorio
🔴 Advertencia de cancelación
🔴 Plazo de 48 horas
```

#### Día +9: Plan Expirado
```
❌ Cancelación automática
❌ Tickets liberados
❌ Reembolso procesado (si aplica)
```

### Acciones del Administrador

**Panel de Pagos Vencidos:**

1. Vaya a **Pagos** → **Vencidos**
2. Verá lista priorizada:

```
┌──────────────────────────────────────────────┐
│ PAGOS VENCIDOS                               │
├──────────────────────────────────────────────┤
│                                              │
│ 🔴 URGENTE (>7 días)                         │
│ #PP-001240 | $200 | 9 días | María C.       │
│ [Contactar] [Extender Plazo] [Cancelar]     │
│                                              │
│ 🟡 ATENCIÓN (3-7 días)                       │
│ #PP-001235 | $150 | 5 días | Pedro R.       │
│ [Recordar] [Llamar] [Extender]              │
│                                              │
│ 🟠 RECIENTE (1-3 días)                       │
│ #PP-001238 | $100 | 2 días | Ana M.         │
│ [Recordar] [Registrar Pago]                 │
└──────────────────────────────────────────────┘
```

**Opciones de Gestión:**

1. **Registrar Pago Manual**
   - Cliente pagó pero no se registró
   - Usar "Registrar Pago"

2. **Extender Plazo**
   - Cliente pidió más tiempo
   - Máximo: 15 días adicionales
   - Requiere aprobación

3. **Cancelar Plan**
   - Cliente no responde
   - Libera tickets
   - Procesa reembolso

4. **Contacto Manual**
   - Llamada telefónica
   - Email personalizado
   - Mensaje SMS

---

## 🎫 Emisión de Tickets con Planes de Pago

### Estados de Tickets

**Durante el Plan:**
```
Estado: RESERVADO
- Asientos bloqueados
- No transferibles
- No válidos para ingreso
- Pendiente de pago completo
```

**Al Completar Pago:**
```
Estado: EMITIDO
- Válidos para ingreso
- QR code generado
- Transferibles (si está permitido)
- Descargables
```

### Política de Reservas

**Tiempo de Reserva:**
- Asientos reservados durante el plan
- No disponibles para otros clientes
- Se liberan si plan se cancela

**Confirmación Final:**
- Requiere 100% de pago
- Fecha límite: 7 días antes del evento
- Sin excepciones

---

## 💡 Estrategias de Planes de Pago

### Para Eventos de Alto Costo

**Festival de 3 Días - $600**

```
Plan Recomendado:
├── Opción 1: Plan Súper Anticipado (6 meses)
│   ├── 6 cuotas de $100
│   ├── Sin recargo
│   └── Descuento early bird incluido
│
├── Opción 2: Plan Anticipado (3 meses)
│   ├── 4 cuotas de $150
│   ├── Recargo 5%
│   └── Precio regular
│
└── Opción 3: Plan Express (1 mes)
    ├── 2 cuotas de $300
    ├── Recargo 10%
    └── Últimos tickets
```

### Para Eventos Familiares

**Show Infantil - $200 (4 tickets)**

```
Plan Familiar:
├── Pago inicial: 30% ($60)
├── 3 cuotas mensuales de $46.67
├── Sin recargo para familias
└── Incluye merchandising gratis
```

### Para Eventos Corporativos

**Conferencia Empresarial - $300**

```
Plan Corporativo:
├── Facturación después del evento
├── Cupo confirmado con 20% inicial
├── Pago diferido a 30 días
└── Descuento por volumen
```

---

## 📊 Reportes de Planes de Pago

### Dashboard de Planes

Acceda a **Reportes** → **Planes de Pago**

**Métricas Principales:**
```
┌─────────────────────────────────────────────┐
│ RESUMEN DE PLANES DE PAGO                   │
├─────────────────────────────────────────────┤
│                                             │
│ Total de Planes:        234                 │
│ Planes Activos:         156 (67%)           │
│ Planes Completados:      68 (29%)           │
│ Planes Vencidos:         10 (4%)            │
│                                             │
│ Revenue Comprometido:   $117,000            │
│ Revenue Recaudado:      $78,000 (67%)       │
│ Revenue Pendiente:      $39,000 (33%)       │
│                                             │
│ Promedio de Cuotas:     3.5 cuotas          │
│ Tiempo Promedio:        78 días             │
│ Tasa de Completación:   87%                 │
└─────────────────────────────────────────────┘
```

### Por Evento

**Análisis Individual:**
```
Evento: Concierto Rock
Fecha: 30/12/2025

Planes de Pago:
├── Total de Planes: 45
├── Completados: 12 (27%)
├── En Progreso: 30 (67%)
└── Vencidos: 3 (6%)

Financiero:
├── Comprometido: $22,500
├── Recaudado: $15,750 (70%)
├── Pendiente: $6,750 (30%)

Proyección:
└── Si 87% completa: $19,575 total
```

### Análisis de Comportamiento

**Tasa de Completación por Tipo:**
```
Plan Flexible:      85% completados
Plan 2 Cuotas:      92% completados
Plan 3 Cuotas:      88% completados
Plan 4+ Cuotas:     79% completados
```

**Mejor Momento de Creación:**
```
60+ días antes:     91% completados
30-60 días:         86% completados
15-30 días:         78% completados
<15 días:           65% completados
```

---

## ⚙️ Configuración Avanzada

### Políticas de Reembolso

**Si Cliente Cancela:**
```
Reembolso Escalonado:
├── >60 días antes: 100% reembolso
├── 30-60 días:     75% reembolso
├── 15-30 días:     50% reembolso
├── 7-15 días:      25% reembolso
└── <7 días:        No reembolso
```

**Configurar en Sistema:**
1. **Eventos** → **Configuración General**
2. **Políticas de Cancelación**
3. Configure porcentajes por rango de días
4. Guarde cambios

### Recargos Automáticos

**Por Mora:**
```
Configuración:
├── Activar recargos por mora: ☑
├── Días de gracia: 3
├── Tipo de recargo: Porcentaje
├── Monto: 5% de la cuota
└── Recargo máximo: $50
```

**Por Uso de Plan:**
```
Opciones:
├── Sin recargo (promocional)
├── Porcentaje fijo: 3-10%
├── Monto fijo: $5-$20
└── Escalonado por número de cuotas
```

### Integraciones de Pago

**Pagos Recurrentes Automáticos:**

Si el cliente autoriza, puede configurar:
```
☑ Cargo automático a tarjeta
☑ Débito directo bancario
☑ Billetera digital

Beneficios:
✓ Pago automático en fecha
✓ Sin olvidos del cliente
✓ Reducción de vencidos
✓ Mejor experiencia
```

---

## 💡 Mejores Prácticas

### ✅ Recomendaciones

1. **Pago Inicial Adecuado**
   - Mínimo 20-30% para eventos grandes
   - Asegura compromiso real
   - Reduce cancelaciones

2. **Plazos Razonables**
   - Cierre 7-14 días antes del evento
   - Tiempo para resolver problemas
   - Evitar estrés de último momento

3. **Comunicación Clara**
   - Enviar recordatorios frecuentes
   - Múltiples canales (email, SMS, WhatsApp)
   - Instrucciones de pago claras

4. **Flexibilidad con Límites**
   - Permitir cambios de fecha (1 vez)
   - Extensiones excepcionales
   - Pero mantener políticas claras

5. **Seguimiento Proactivo**
   - Contactar antes del vencimiento
   - Ofrecer facilidades de pago
   - Resolver dudas rápidamente

### ❌ Errores Comunes

1. **Plazos Muy Largos**
   - Problema: Cliente olvida el compromiso
   - Solución: Máximo 6 meses

2. **Muchas Cuotas Pequeñas**
   - Problema: Difícil de gestionar
   - Solución: Máximo 6 cuotas

3. **No Seguimiento**
   - Problema: Alta tasa de vencidos
   - Solución: Sistema de recordatorios automático

4. **Emisión Prematura de Tickets**
   - Problema: Cliente no completa pago
   - Solución: Emitir solo al 100%

---

## 🎯 Checklist para Planes de Pago

### Antes de Habilitar

```
☐ Políticas de pago definidas
☐ Porcentaje inicial configurado
☐ Fechas límite establecidas
☐ Sistema de notificaciones activo
☐ Proceso de reembolso definido
☐ Términos y condiciones actualizados
☐ Personal capacitado
☐ Sistema de seguimiento en funcionamiento
```

### Durante Operación

```
☐ Revisar planes vencidos diariamente
☐ Responder consultas en <24 horas
☐ Procesar pagos el mismo día
☐ Enviar confirmaciones inmediatas
☐ Mantener comunicación clara
☐ Actualizar proyecciones semanalmente
```

### Fin del Plan

```
☐ Confirmar pago al 100%
☐ Emitir tickets inmediatamente
☐ Enviar confirmación con tickets
☐ Actualizar estado del plan
☐ Cerrar plan en sistema
☐ Archivar documentación
```

---

## 📝 Ejemplo Práctico Completo

### Caso: Concierto de Año Nuevo

**Configuración del Evento:**
```
Evento: Gala de Año Nuevo 2026
Fecha: 31/12/2025
Tickets VIP: $400
Tickets General: $200
```

**Configuración de Planes:**
```
Plan Habilitado: ✓

Parámetros VIP:
├── Pago inicial: 25% ($100)
├── Cuotas disponibles: 2, 3, 4
├── Fecha límite: 24/12/2025
├── Recargo: 5%

Parámetros General:
├── Pago inicial: 30% ($60)
├── Cuotas disponibles: 2, 3
├── Fecha límite: 24/12/2025
├── Recargo: 0% (promoción)
```

**Cliente: María González**

**Día 1 (01/10/2025):** María crea plan
```
Selección:
- 2 Tickets VIP @ $400 = $800
- Plan elegido: 4 cuotas
- Pago inicial: $200 (25%)

Calendario:
├── Cuota 1: $200 - 01/10/2025 ✓ Pagado
├── Cuota 2: $200 - 01/11/2025 Pendiente
├── Cuota 3: $200 - 01/12/2025 Pendiente
└── Cuota 4: $200 - 20/12/2025 Pendiente

Email enviado con confirmación
Tickets reservados: VIP-A5, VIP-A6
```

**Día 25 (25/10/2025):** Recordatorio cuota 2
```
Email automático:
"Su próxima cuota vence en 7 días"
```

**Día 32 (01/11/2025):** María paga cuota 2
```
Método: Transferencia bancaria
Monto: $200
Progreso: 50% (2 de 4 cuotas)
Saldo: $400
```

**Día 62 (01/12/2025):** María paga cuota 3
```
Método: Pago móvil
Monto: $200
Progreso: 75% (3 de 4 cuotas)
Saldo: $200
```

**Día 80 (19/12/2025):** Un día antes de cuota 4
```
Email urgente:
"Última cuota vence mañana"
```

**Día 81 (20/12/2025):** María completa pago
```
Método: Tarjeta de crédito
Monto: $200
Progreso: 100% ✓

Sistema automáticamente:
✓ Emite tickets VIP-A5, VIP-A6
✓ Genera QR codes
✓ Envía email con tickets adjuntos
✓ Marca plan como COMPLETADO
✓ Confirma asientos definitivamente
```

**Día 93 (31/12/2025):** Día del evento
```
María escanea QR en entrada
Sistema valida:
✓ Tickets válidos
✓ Plan completado
✓ Asientos: VIP-A5, VIP-A6
✓ Acceso concedido
```

---

## ❓ Preguntas Frecuentes

### ¿Qué pasa si el cliente no completa el plan?

Si no se completa antes de la fecha límite:
1. Plan se marca como EXPIRADO
2. Tickets se liberan automáticamente
3. Se procesa reembolso según política
4. Cliente recibe notificación

### ¿Puedo cambiar las fechas de las cuotas?

Sí, el administrador puede:
- Extender hasta 15 días adicionales
- Modificar montos de cuotas
- Reagendar pagos
- Requiere autorización

### ¿El cliente puede pagar todo antes de tiempo?

Sí, puede pagar:
- El saldo completo en cualquier momento
- Cuotas por adelantado
- Sistema recalcula automáticamente

### ¿Qué métodos de pago se aceptan?

Todos los configurados en el evento:
- Efectivo
- Tarjetas de crédito/débito
- Transferencias bancarias
- Pagos móviles
- Billeteras digitales

### ¿Puedo ofrecer descuentos en planes de pago?

Sí, puede configurar:
- Descuento por pago anticipado completo
- Promociones en pago inicial alto
- Descuentos estacionales
- Códigos promocionales

---

[← Anterior: Ventas](06-ventas.md) | [Volver al Índice](README.md) | [Siguiente: Clientes →](08-clientes.md)
