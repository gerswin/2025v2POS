# 6. Proceso de Ventas

## Introducción

El módulo de ventas es donde se concreta todo el trabajo de configuración. Aquí los clientes (o vendedores) seleccionan tickets, realizan el pago y reciben sus entradas digitales.

---

## 🎯 Flujo de Venta Completo

```
1. Seleccionar Evento
   └→ Ver eventos disponibles

2. Elegir Asientos / Cantidad
   └→ Mapa visual o selector de cantidad

3. Agregar al Carrito
   └→ Revisar selección

4. Información del Cliente
   └→ Datos personales y fiscales

5. Método de Pago
   └→ Seleccionar cómo pagar

6. Confirmar y Pagar
   └→ Procesar transacción

7. Recibir Tickets
   └→ Email con QR codes
```

---

## ✅ Iniciar una Venta

### Paso 1: Acceder al Módulo

1. En el menú principal, haga clic en **Ventas**
2. Verá el dashboard de ventas con eventos activos
3. Haga clic en **Nueva Venta** o seleccione un evento

### Paso 2: Seleccionar Evento

```
┌─────────────────────────────────────────┐
│ EVENTOS DISPONIBLES                     │
├─────────────────────────────────────────┤
│                                          │
│ [🎵] Concierto Rock Sinfónico          │
│      20/03/2025 - 20:00                 │
│      Teatro Nacional                    │
│      Desde: $100                        │
│      [Vender →]                         │
│                                          │
│ [🎭] El Avaro - Molière                │
│      25/03/2025 - 19:30                 │
│      Teatro Municipal                   │
│      Desde: $40                         │
│      [Vender →]                         │
│                                          │
└─────────────────────────────────────────┘
```

Haga clic en **[Vender →]** del evento deseado.

---

## 🪑 Selección de Asientos Numerados

### Mapa Interactivo

Verá una representación visual del venue:

```
TEATRO NACIONAL - CONCIERTO ROCK SINFÓNICO
════════════════════════════════════════════

         [ ESCENARIO ]
════════════════════════════════════════════

PLATEA VIP - $150
Fila A: [🟩][🟩][🟥][🟥][🟩][🟩]
Fila B: [🟩][🟨][🟨][🟩][🟩][🟩]
Fila C: [🟩][🟩][🟩][🟩][🟩][🟩]

PLATEA GENERAL - $100
Fila D: [🟩][🟩][🟩][🟩][🟥][🟩]
Fila E: [🟩][🟩][🟩][🟩][🟩][🟩]

Leyenda:
🟩 Disponible  🟨 Reservado  🟥 Vendido  ⬜ Bloqueado
```

### Seleccionar Asientos

1. **Haga clic** en los asientos deseados
2. Los asientos se marcan con un **borde amarillo**
3. Puede seleccionar múltiples asientos
4. Haga clic nuevamente para deseleccionar

### Información del Asiento

Al pasar el mouse sobre un asiento:

```
┌─────────────────────┐
│ Asiento: A5         │
│ Zona: Platea VIP    │
│ Fila: A             │
│ Precio: $150.00     │
│ Estado: Disponible  │
│ [Seleccionar]       │
└─────────────────────┘
```

### Vista de Selección

En el lateral derecha:

```
┌─────────────────────────────────┐
│ SELECCIÓN ACTUAL                │
├─────────────────────────────────┤
│                                  │
│ 🪑 Platea VIP A5                │
│    $150.00                       │
│    [❌ Quitar]                  │
│                                  │
│ 🪑 Platea VIP A6                │
│    $150.00                       │
│    [❌ Quitar]                  │
│                                  │
│ ─────────────────────────       │
│ Subtotal: $300.00                │
│ IVA (16%): $48.00                │
│ Total: $348.00                   │
│                                  │
│ [Agregar al Carrito]             │
│                                  │
└─────────────────────────────────┘
```

### Opciones Avanzadas

**Selección Rápida**
```
☐ Seleccionar mejores disponibles
  Cantidad: [2] asientos
  Zona: [Platea VIP ▼]
  [Buscar]
```

**Filtros**
```
Mostrar solo:
☑ Disponibles
☐ Reservados (si soy el propietario)
☐ Todos

Rango de precio:
Min: [$50] Max: [$200]
```

---

## 👥 Selección de Entrada General

Para zonas sin asientos asignados:

```
┌─────────────────────────────────────┐
│ TERRAZAS - ENTRADA GENERAL          │
├─────────────────────────────────────┤
│                                      │
│ Precio por ticket: $50.00           │
│                                      │
│ Disponible: 85 / 100                │
│                                      │
│ Cantidad de tickets:                │
│ [  -  ]  [ 2 ]  [  +  ]            │
│                                      │
│ Límite por compra: 10 tickets       │
│                                      │
│ Subtotal: $100.00                   │
│ IVA (16%): $16.00                   │
│ Total: $116.00                      │
│                                      │
│ [Agregar al Carrito]                 │
│                                      │
└─────────────────────────────────────┘
```

---

## 🛒 Carrito de Compras

### Ver Carrito

```
┌─────────────────────────────────────────────┐
│ CARRITO DE COMPRAS                          │
├─────────────────────────────────────────────┤
│                                              │
│ Evento: Concierto Rock Sinfónico            │
│ Fecha: 20/03/2025 20:00                     │
│                                              │
│ Items:                                      │
│ ┌─────────────────────────────────────────┐│
│ │ 🪑 Platea VIP - A5       $150.00      ❌││
│ └─────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────┐│
│ │ 🪑 Platea VIP - A6       $150.00      ❌││
│ └─────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────┐│
│ │ 👥 Terrazas x2           $100.00      ❌││
│ └─────────────────────────────────────────┘│
│                                              │
│ Subtotal:        $400.00                    │
│ IVA (16%):       $ 64.00                    │
│ ──────────────────────────                  │
│ Total:           $464.00                    │
│                                              │
│ [Continuar Comprando] [Proceder al Pago →] │
│                                              │
└─────────────────────────────────────────────┘
```

### Aplicar Código Promocional

```
┌─────────────────────────────────┐
│ ¿Tienes un código promocional?  │
│                                  │
│ Código: [EARLY2025_________]    │
│         [Aplicar]               │
│                                  │
│ ✅ Código aplicado: -20%         │
│ Nuevo total: $371.20             │
└─────────────────────────────────┘
```

---

## 👤 Información del Cliente

### Paso 1: Buscar Cliente Existente

```
┌─────────────────────────────────────┐
│ INFORMACIÓN DEL CLIENTE             │
├─────────────────────────────────────┤
│                                      │
│ Buscar cliente:                     │
│ 🔍 [Cédula, email o teléfono____]  │
│                                      │
│ O crear nuevo cliente:              │
│ [+ Nuevo Cliente]                   │
│                                      │
└─────────────────────────────────────┘
```

### Paso 2: Datos del Cliente

#### Persona Natural

**Datos Personales** ✅
```
Nombre: [Juan____________]
Apellido: [Pérez__________]
```

**Identificación** ✅
```
Tipo: [Cédula ▼]
Número: [V-12345678]
```

**Contacto** ✅
```
Email: [juan@email.com_____]
Teléfono: [+58 414-1234567_]
```

**Dirección** (Opcional)
```
Dirección: [Av. Principal, Edificio...]
Ciudad: [Caracas▼]
Estado: [Miranda▼]
```

#### Persona Jurídica

Si requiere factura fiscal:

```
☑ Persona Jurídica (Empresa)

Razón Social: [Empresa C.A.__________]
RIF: [J-123456789]
Dirección Fiscal: [____________]
```

### Paso 3: Guardar Cliente

```
☑ Guardar en base de datos
☑ Enviar tickets por email
☐ Enviar SMS de confirmación
☐ Suscribir a newsletter
```

---

## 💳 Métodos de Pago

### Seleccionar Método

```
┌─────────────────────────────────────┐
│ MÉTODO DE PAGO                      │
├─────────────────────────────────────┤
│                                      │
│ ○ Efectivo                          │
│ ○ Transferencia Bancaria            │
│ ● Tarjeta de Débito/Crédito        │
│ ○ Pago Móvil                        │
│ ○ Zelle                             │
│                                      │
└─────────────────────────────────────┘
```

### Información por Método

#### Efectivo 💵
```
Total a pagar: $464.00

El cliente pagará en efectivo al momento
del retiro o en punto de venta.

Referencia: [Número de referencia______]
(Opcional)
```

#### Transferencia Bancaria 🏦
```
Cuenta: Banco Nacional
Nro: 0102-1234-56-1234567890
A nombre de: Tiquemax C.A.
RIF: J-123456789

Referencia: [Nro de confirmación_____]
(Requerido)

Monto: $464.00
```

#### Tarjeta de Crédito/Débito 💳
```
Número de Tarjeta:
[____] [____] [____] [____]

Vencimiento: [MM] / [YY]
CVV: [___]

Titular: [JUAN PEREZ_____________]

☑ Guardar para futuros pagos
```

#### Pago Móvil 📱
```
Banco Origen: [Banco Caribe ▼]
Teléfono: [0414-1234567_______]

Referencia: [123456___________]
(Requerido)

Monto: Bs. 17,856.00
```

### Procesar con Plan de Pago

```
┌─────────────────────────────────────┐
│ OPCIONES DE PAGO                    │
├─────────────────────────────────────┤
│                                      │
│ ● Pago Completo ($464.00)          │
│                                      │
│ ○ Plan de Pago                      │
│   Inicial: $139.20 (30%)            │
│   Saldo: $324.80                    │
│   Vencimiento: 7 días               │
│   [Ver Detalles →]                  │
│                                      │
└─────────────────────────────────────┘
```

💡 Ver más detalles en [Capítulo 7: Pagos Parciales](07-pagos-parciales.md)

---

## ✅ Confirmar y Completar

### Resumen Final

```
┌─────────────────────────────────────────┐
│ CONFIRMAR COMPRA                        │
├─────────────────────────────────────────┤
│                                          │
│ Evento: Concierto Rock Sinfónico        │
│ Fecha: 20/03/2025 20:00                 │
│ Teatro Nacional                         │
│                                          │
│ Cliente: Juan Pérez                     │
│ Email: juan@email.com                   │
│                                          │
│ Tickets:                                │
│ • Platea VIP A5                         │
│ • Platea VIP A6                         │
│ • Terrazas x2                           │
│                                          │
│ Total: $464.00                          │
│ Método: Tarjeta de Crédito              │
│                                          │
│ ☑ Acepto términos y condiciones         │
│                                          │
│ [← Volver] [Confirmar y Pagar →]       │
│                                          │
└─────────────────────────────────────────┘
```

### Procesando Pago

```
┌─────────────────────────────┐
│ ⏳ PROCESANDO PAGO...       │
│                              │
│ Por favor espere...          │
│ No cierre esta ventana       │
│                              │
│ [████████░░░░░░░░] 60%      │
└─────────────────────────────┘
```

### Confirmación Exitosa

```
┌─────────────────────────────────────┐
│ ✅ ¡COMPRA EXITOSA!                 │
├─────────────────────────────────────┤
│                                      │
│ Transacción: #EV-2025-0234          │
│ Fecha: 03/11/2025 22:45             │
│                                      │
│ Se ha enviado la confirmación y     │
│ los tickets digitales a:            │
│ juan@email.com                      │
│                                      │
│ [Ver Tickets] [Imprimir Recibo]     │
│ [Nueva Venta]                       │
│                                      │
└─────────────────────────────────────┘
```

---

## 🎟️ Después de la Venta

### Email de Confirmación

El cliente recibe automáticamente:

```
De: Tiquemax POS <noreply@tiquemax.com>
Para: juan@email.com
Asunto: Tus tickets - Concierto Rock Sinfónico

¡Gracias por tu compra!

Evento: Concierto Rock Sinfónico
Fecha: 20 de Marzo, 2025 - 20:00
Lugar: Teatro Nacional

Tus tickets:
[QR CODE] Platea VIP - A5
[QR CODE] Platea VIP - A6
[QR CODE] Terrazas - General x2

Total pagado: $464.00
Referencia: EV-2025-0234

[Descargar Tickets PDF]
[Agregar a Calendario]

Importante:
• Presenta este email o el código QR en la entrada
• Llega con 30 minutos de anticipación
• No se permiten reembolsos

¿Problemas? Contacta: soporte@tiquemax.com
```

### Tickets Digitales

Cada ticket incluye:
- Código QR único
- Nombre del evento
- Fecha y hora
- Ubicación del asiento
- Nombre del comprador
- Términos y condiciones

---

## 🔍 Gestión de Transacciones

### Ver Todas las Transacciones

```
Ventas → Transacciones

Filtros:
└ Fecha: [Hoy ▼]
└ Estado: [Todas ▼]
└ Evento: [Todos ▼]
└ Buscar: [Cliente, ticket...____]
```

### Detalle de Transacción

```
┌─────────────────────────────────────────┐
│ TRANSACCIÓN #EV-2025-0234               │
├─────────────────────────────────────────┤
│                                          │
│ Estado: ✅ Completada                    │
│ Fecha: 03/11/2025 22:45                 │
│                                          │
│ Cliente: Juan Pérez                     │
│ Email: juan@email.com                   │
│ CI: V-12345678                          │
│                                          │
│ Evento: Concierto Rock Sinfónico        │
│ 20/03/2025 20:00                        │
│                                          │
│ Items:                                  │
│ • Platea VIP A5 - $150.00               │
│ • Platea VIP A6 - $150.00               │
│ • Terrazas x2 - $100.00                 │
│                                          │
│ Total: $464.00                          │
│ Método: Tarjeta ****1234                │
│                                          │
│ [Imprimir] [Reenviar Email]             │
│ [Ver Tickets] [Cancelar]                │
│                                          │
└─────────────────────────────────────────┘
```

---

## 🛠️ Operaciones Especiales

### Cancelar una Venta

⚠️ **Solo si no se ha completado el pago**

1. Vaya a la transacción
2. Haga clic en **Cancelar**
3. Indique el motivo:
   ```
   Motivo: [Cliente cambió de opinión__]
   ```
4. Confirme la cancelación
5. Los asientos se liberan automáticamente

### Cambiar Asientos

📝 **Política**: Según configuración del evento

1. Vaya a la transacción completada
2. Haga clic en **Modificar**
3. Seleccione los nuevos asientos
4. Sistema calcula diferencia de precio
5. Procese cobro adicional o reembolso

### Reenviar Tickets

1. Vaya a la transacción
2. Haga clic en **Reenviar Email**
3. Confirme el email destino
4. Los tickets se reenvían inmediatamente

---

## 📊 Reportes de Ventas

### Dashboard del Día

```
┌─────────────────────────────────────┐
│ VENTAS HOY - 03/11/2025             │
├─────────────────────────────────────┤
│                                      │
│ Transacciones: 45                   │
│ Tickets Vendidos: 123               │
│ Ingresos: $15,450.00                │
│                                      │
│ Por Evento:                         │
│ • Concierto Rock: $8,200 (15 trans)│
│ • El Avaro: $7,250 (30 trans)      │
│                                      │
│ Métodos de Pago:                    │
│ • Tarjeta: 60% ($9,270)            │
│ • Transferencia: 30% ($4,635)      │
│ • Efectivo: 10% ($1,545)           │
│                                      │
└─────────────────────────────────────┘
```

---

## 💡 Mejores Prácticas

### ✅ Hacer

1. **Verificar Disponibilidad**
   - Revisar asientos antes de prometer
   - Advertir al cliente sobre tiempos de reserva

2. **Confirmar Datos**
   - Email correcto (tickets se envían allí)
   - Teléfono válido
   - Identificación correcta

3. **Comunicar Claramente**
   - Políticas de cancelación
   - Información del evento
   - Instrucciones de acceso

4. **Procesar Rápido**
   - No dejar al cliente esperando
   - Tener métodos de pago listos
   - Conocer el sistema

### ❌ Evitar

1. **Prometer sin Verificar**
   - "Seguro hay disponible" sin revisar

2. **Datos Incorrectos**
   - Email mal escrito = tickets no llegan

3. **Cobros Erróneos**
   - Verificar monto antes de procesar

---

## ❓ Preguntas Frecuentes

### ¿Cuánto tiempo tengo para completar una compra?

Los asientos se reservan temporalmente por 10 minutos. Después se liberan automáticamente.

### ¿Puedo vender por teléfono?

Sí, un vendedor puede procesar la venta ingresando los datos del cliente.

### ¿Qué pasa si el pago falla?

La transacción queda pendiente. El cliente puede reintentar o usar otro método.

### ¿Se pueden vender tickets para múltiples eventos en una transacción?

No, cada evento requiere una transacción separada.

---

[← Anterior: Etapas](05-etapas-precios.md) | [Volver al Índice](README.md) | [Siguiente: Pagos Parciales →](07-pagos-parciales.md)
