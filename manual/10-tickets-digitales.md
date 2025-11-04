# 10. Tickets Digitales

## Introducción

Los **tickets digitales** son la representación electrónica de las entradas a eventos. Ofrecen comodidad, seguridad y reducen costos operativos eliminando la necesidad de tickets físicos.

---

## 🎫 ¿Qué es un Ticket Digital?

Un ticket digital incluye:

```
┌──────────────────────────────────────────┐
│  🎵 CONCIERTO ROCK 2025                  │
├──────────────────────────────────────────┤
│                                          │
│  [█████████ QR CODE █████████]           │
│                                          │
│  Evento:   Concierto Rock 2025           │
│  Fecha:    30 Diciembre 2025             │
│  Hora:     20:00                         │
│                                          │
│  Lugar:    Teatro Nacional               │
│           Av. Lecuna, Caracas            │
│                                          │
│  Zona:     VIP                           │
│  Fila:     A                             │
│  Asiento:  5                             │
│                                          │
│  Cliente:  Juan Pérez                    │
│  Ticket:   #TK-123456789                 │
│                                          │
│  Precio:   $100.00                       │
│  Estado:   VÁLIDO ✓                      │
│                                          │
│  ⚠️ Este ticket es válido solo           │
│     para 1 persona                       │
│  ⚠️ No transferible sin autorización     │
└──────────────────────────────────────────┘
```

### Componentes del Ticket

**Código QR:**
- Identificador único encriptado
- Imposible de duplicar
- Escaneable en la entrada
- Contiene toda la información

**Información del Evento:**
- Nombre completo
- Fecha y hora exacta
- Ubicación detallada
- Puertas de acceso

**Información del Asiento:**
- Zona asignada
- Fila y número (si aplica)
- Precio pagado
- Categoría

**Seguridad:**
- Número de ticket único
- Marca de agua digital
- Hologramas (PDF)
- Estado en tiempo real

---

## ✅ Generación de Tickets

### Automática

Los tickets se generan automáticamente cuando:

**1. Pago Completo Recibido:**
```
Cliente completa compra
       ↓
Sistema valida pago
       ↓
Genera tickets digitales
       ↓
Envía email con adjuntos
       ↓
Cliente descarga
```

**2. Plan de Pago Completado:**
```
Cliente paga última cuota
       ↓
Sistema marca plan completo
       ↓
Genera tickets automáticamente
       ↓
Email con tickets adjuntos
       ↓
Asientos confirmados
```

**3. Emisión Manual (Cortesías):**
```
Admin crea ticket cortesía
       ↓
Selecciona evento y asiento
       ↓
Genera ticket manual
       ↓
Envía por email
```

### Proceso de Generación

```
┌────────────────────────────────────────────┐
│ GENERACIÓN DE TICKET                       │
├────────────────────────────────────────────┤
│                                            │
│ 1. Validación de Transacción               │
│    ✓ Pago confirmado                       │
│    ✓ Asientos disponibles                  │
│    ✓ Datos del cliente completos           │
│                                            │
│ 2. Creación del Ticket                     │
│    ✓ Asignar número único                  │
│    ✓ Generar código QR                     │
│    ✓ Aplicar diseño del evento             │
│    ✓ Añadir información de seguridad       │
│                                            │
│ 3. Generación de Archivo                   │
│    ✓ Crear PDF de alta calidad             │
│    ✓ Añadir marca de agua                  │
│    ✓ Optimizar para móvil                  │
│    ✓ Adjuntar wallet pass (opcional)       │
│                                            │
│ 4. Entrega al Cliente                      │
│    ✓ Enviar email automático               │
│    ✓ Disponible en cuenta de usuario       │
│    ✓ Opción de descarga directa            │
│    ✓ Añadir a wallet móvil                 │
└────────────────────────────────────────────┘
```

---

## 📱 Formatos de Tickets

### PDF

**Características:**
```
✓ Alta calidad de impresión
✓ Compatible con todos los dispositivos
✓ Tamaño estándar (A4 o carta)
✓ Múltiples tickets en un archivo
✓ Código QR de alta resolución
```

**Uso:**
```
Ideal para:
├── Imprimir en casa
├── Guardar en computadora
├── Compartir por email
└── Archivo permanente
```

### Apple Wallet (.pkpass)

**Características:**
```
✓ Integración nativa con iPhone
✓ Aparece en pantalla de bloqueo
✓ Actualización en tiempo real
✓ Notificaciones automáticas
✓ Uso sin internet
```

**Proceso:**
```
1. Cliente recibe email
2. Abre adjunto .pkpass
3. "Añadir a Apple Wallet"
4. Ticket disponible en Wallet
5. Acceso rápido desde bloqueo
```

### Google Wallet

**Características:**
```
✓ Integración con Android
✓ Recordatorios automáticos
✓ Estado en tiempo real
✓ Acceso offline
✓ Notificaciones inteligentes
```

---

## 🔒 Seguridad de Tickets

### Prevención de Fraude

**Código QR Encriptado:**
```
Datos incluidos (encriptados):
├── ID único del ticket
├── ID de la transacción
├── Timestamp de creación
├── Información del asiento
├── Hash de validación
└── Firma digital
```

**Sistema de Validación:**
```
1. Escaneo del QR en entrada
2. Desencriptación del código
3. Validación en base de datos
4. Verificación de:
   ├── Ticket no usado previamente
   ├── Evento correcto
   ├── Fecha y hora válidas
   └── No cancelado/reembolsado
5. Marca como USADO
6. Permite acceso
```

**Protección Anti-Duplicación:**
```
⚠️ Si se escanea el mismo QR dos veces:

Primera entrada: ✓ ACCESO PERMITIDO
Segunda entrada: ✗ TICKET YA USADO

Sistema alerta:
├── Timestamp primera entrada
├── Puerta de acceso original
├── Notificación a seguridad
└── Bloqueo automático
```

### Marcas de Agua y Hologramas

**En PDF:**
```
✓ Marca de agua con logo del evento
✓ Patrón de seguridad en fondo
✓ Números de serie únicos
✓ Código de barras de respaldo
✓ Fecha de emisión visible
```

**Verificación Visual:**
```
Personal de seguridad verifica:
├── Calidad de impresión
├── Código QR nítido
├── Información coherente
├── Sin alteraciones evidentes
└── Coincidencia con documento ID
```

---

## 📧 Entrega de Tickets

### Email Automático

**Plantilla de Email:**
```
──────────────────────────────────────
De: tickets@plataforma.com
Para: cliente@email.com
Asunto: Sus Tickets - Concierto Rock 2025
──────────────────────────────────────

¡Hola Juan!

Sus tickets para Concierto Rock 2025 están listos.

📅 Fecha: 30 de Diciembre 2025
🕐 Hora: 20:00
📍 Lugar: Teatro Nacional, Caracas

🎫 Tickets:
   • VIP Fila A, Asiento 5
   • VIP Fila A, Asiento 6

📱 Opciones de Tickets:
   [Descargar PDF] [Añadir a Apple Wallet] [Google Wallet]

💡 Instrucciones:
   1. Descargue sus tickets
   2. Presente el código QR en la entrada
   3. Llegue 30 minutos antes del evento
   4. Traiga identificación válida

⚠️ Importante:
   • Cada ticket es válido para 1 persona
   • Los tickets no son transferibles
   • No se permiten reentradas

[Ver Detalles del Evento]
[Gestionar Mi Compra]

¿Preguntas? Contáctenos:
📧 soporte@plataforma.com
📞 +58 212-555-1234

──────────────────────────────────────
```

### Portal del Cliente

**Acceso en Línea:**
```
1. Cliente accede a cuenta
2. Sección "Mis Tickets"
3. Ve lista de eventos:

┌────────────────────────────────────────┐
│ MIS TICKETS                            │
├────────────────────────────────────────┤
│                                        │
│ 🎸 Concierto Rock 2025                 │
│    30 Dic 2025 • 20:00                 │
│    2 tickets VIP                       │
│    [Descargar] [Ver] [Compartir]      │
│                                        │
│ 🎭 Obra de Teatro                      │
│    15 Nov 2025 • 19:00                 │
│    4 tickets Platea                    │
│    [Descargar] [Ver] [Compartir]      │
└────────────────────────────────────────┘
```

### Opciones de Descarga

```
┌────────────────────────────────────────┐
│ DESCARGAR TICKETS                      │
├────────────────────────────────────────┤
│                                        │
│ Seleccione formato:                    │
│                                        │
│ 📄 PDF                                 │
│    └─ [Descargar todos] [Individual]  │
│                                        │
│ 📱 Apple Wallet                        │
│    └─ [Añadir a Wallet]                │
│                                        │
│ 📲 Google Wallet                       │
│    └─ [Guardar en Google Pay]         │
│                                        │
│ 📧 Reenviar por Email                  │
│    Email: [_________________]          │
│    └─ [Enviar]                         │
│                                        │
│ 💬 Compartir por WhatsApp              │
│    └─ [Compartir]                      │
└────────────────────────────────────────┘
```

---

## ✏️ Gestión de Tickets Emitidos

### Ver Tickets de un Evento

**Panel de Control:**
```
1. Vaya a **Eventos** → Seleccione evento
2. Pestaña **Tickets Emitidos**
3. Vista de todos los tickets:

┌────────────────────────────────────────────────┐
│ TICKETS EMITIDOS - Concierto Rock 2025         │
├────────────────────────────────────────────────┤
│                                                │
│ Total Emitidos: 750 / 1,000                    │
│                                                │
│ Filtros:                                       │
│ Zona: [Todas ▼] Estado: [Todos ▼]             │
│ Buscar: [_______________] 🔍                   │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ #TK-123456789                            │  │
│ │ Juan Pérez • VIP-A5                      │  │
│ │ Estado: Válido ✓ • Comprado: 15/10/2025  │  │
│ │ [Ver] [Reenviar] [Invalidar]            │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ #TK-123456790                            │  │
│ │ María González • Platea-K12              │  │
│ │ Estado: Usado ✓ • Entrada: 30/12 19:45   │  │
│ │ [Ver Detalles]                           │  │
│ └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### Estados de Tickets

**Válido (Valid)** ✅
```
• Ticket emitido y listo para usar
• No ha sido escaneado
• Dentro del período válido
• Sin problemas detectados
```

**Usado (Used)** ✓
```
• Ya se escaneó en la entrada
• Timestamp de ingreso registrado
• No puede volver a usarse
• Evento completado
```

**Cancelado (Cancelled)** ❌
```
• Cliente canceló su compra
• Reembolso procesado
• Ticket invalidado
• Asiento liberado
```

**Expirado (Expired)** ⏰
```
• Evento ya pasó
• No se usó el ticket
• No válido para reembolso
• Archivado
```

**Suspendido (Suspended)** ⚠️
```
• Problema detectado
• Pendiente de investigación
• Acceso bloqueado temporalmente
• Requiere atención manual
```

### Acciones Administrativas

**Reenviar Ticket:**
```
1. Seleccione el ticket
2. Click en "Reenviar"
3. Confirme email del cliente
4. Sistema envía nuevamente
```

**Invalidar Ticket:**
```
Casos de uso:
├── Ticket robado/perdido
├── Sospecha de fraude
├── Cambio de asientos
└── Solicitud del cliente

Proceso:
1. Seleccione ticket
2. "Invalidar Ticket"
3. Indique motivo
4. Confirme acción
5. Ticket marcado como inválido
```

**Transferir Ticket:**
```
Si está permitido:
1. Cliente solicita transferencia
2. Admin verifica política
3. Genera nuevo ticket
4. Invalida ticket original
5. Envía a nuevo titular
```

---

## 🎟️ Tickets Especiales

### Tickets de Cortesía

**Crear Cortesía:**
```
┌────────────────────────────────────────┐
│ EMITIR TICKET DE CORTESÍA              │
├────────────────────────────────────────┤
│                                        │
│ Evento:                                │
│ [Concierto Rock 2025 ▼]                │
│                                        │
│ Zona:                                  │
│ [VIP ▼]                                │
│                                        │
│ Asiento:                               │
│ Fila: [A▼]  Número: [10▼]              │
│                                        │
│ Destinatario:                          │
│ Nombre: [_______________]              │
│ Email:  [_______________]              │
│                                        │
│ Motivo:                                │
│ ○ Prensa                               │
│ ○ Invitado especial                    │
│ ● Cortesía promocional                 │
│ ○ Staff                                │
│ ○ Otro                                 │
│                                        │
│ Notas internas:                        │
│ [______________________]               │
│                                        │
│ [Cancelar]  [Generar Cortesía]        │
└────────────────────────────────────────┘
```

**Marca en el Ticket:**
```
┌──────────────────────────────────────┐
│  🎵 CONCIERTO ROCK 2025              │
│                                      │
│  TICKET DE CORTESÍA                  │
│  [QR CODE]                           │
│                                      │
│  Este ticket fue emitido como        │
│  cortesía promocional.               │
│                                      │
│  No válido para reventa.             │
└──────────────────────────────────────┘
```

### Tickets para Staff

**Características:**
```
✓ Acceso especial (backstage, áreas técnicas)
✓ Identificación visual diferente
✓ Permisos adicionales
✓ Múltiples reentradas permitidas
✓ Válido para montaje/desmontaje
```

**Tipos de Staff:**
```
🎤 Artistas/Talento
   ├── Acceso total
   ├── Backstage
   └── Camarines

🎸 Equipo Técnico
   ├── Área de sonido
   ├── Iluminación
   └── Escenario

📸 Prensa
   ├── Área de prensa
   ├── Zona fotográfica
   └── Sala de conferencias

🛡️ Seguridad
   ├── Todas las áreas
   ├── Múltiples reentradas
   └── Acceso permanente

🍿 Catering/Servicios
   ├── Áreas de servicio
   ├── Cocinas
   └── Almacenes
```

### Pases VIP Especiales

**VIP All Access:**
```
Beneficios incluidos:
✓ Acceso prioritario
✓ Lounge VIP
✓ Meet & Greet
✓ Estacionamiento premium
✓ Merchandising exclusivo
✓ Bebidas incluidas

Ticket diferenciado:
• Color dorado
• Logo especial
• Banda holográfica
• QR con permisos adicionales
```

---

## 📱 Validación en el Evento

### Aplicación de Escaneo

**Dashboard del Scanner:**
```
┌────────────────────────────────────────┐
│ 🎫 SCANNER - Concierto Rock 2025       │
├────────────────────────────────────────┤
│                                        │
│ Puerta: ENTRADA PRINCIPAL              │
│ Operador: Carlos Ramírez               │
│                                        │
│ ══════════════════════════════════════ │
│                                        │
│ 📊 ESTADÍSTICAS                        │
│                                        │
│ Total Esperado:     1,000              │
│ Ya Ingresaron:      456 (46%)          │
│ Pendientes:         544                │
│                                        │
│ Última hora:        89 personas        │
│ Promedio/min:       2.3                │
│                                        │
│ ══════════════════════════════════════ │
│                                        │
│ [ESCANEAR TICKET]                      │
│                                        │
│ 📷 Apunte al código QR                 │
└────────────────────────────────────────┘
```

### Proceso de Validación

**Escaneo Exitoso:**
```
✅ ACCESO PERMITIDO

┌────────────────────────────────────────┐
│ ✓ TICKET VÁLIDO                        │
├────────────────────────────────────────┤
│                                        │
│ Nombre:   Juan Pérez                   │
│ Ticket:   #TK-123456789                │
│                                        │
│ Zona:     VIP                          │
│ Asiento:  Fila A, #5                   │
│                                        │
│ Compra:   15/10/2025                   │
│ Precio:   $100.00                      │
│                                        │
│ ✓ Primera entrada                      │
│ ✓ Evento correcto                      │
│ ✓ Hora válida                          │
│                                        │
│ [PERMITIR ACCESO]                      │
└────────────────────────────────────────┘
```

**Escaneo con Error:**
```
❌ ACCESO DENEGADO

┌────────────────────────────────────────┐
│ ✗ TICKET YA USADO                      │
├────────────────────────────────────────┤
│                                        │
│ Ticket:   #TK-123456789                │
│                                        │
│ ⚠️ Este ticket ya fue escaneado        │
│                                        │
│ Primera entrada:                       │
│ • Hora:   19:45                        │
│ • Puerta: Entrada Principal            │
│ • Por:    Carlos Ramírez               │
│                                        │
│ POSIBLE DUPLICACIÓN                    │
│                                        │
│ [DENEGAR] [LLAMAR SUPERVISOR]         │
└────────────────────────────────────────┘
```

### Modo Offline

**Sin Conexión a Internet:**
```
Sistema descarga lista de tickets válidos:
├── Antes del evento
├── Incluye todos los tickets emitidos
├── Actualización cada hora
└── Sincroniza al recuperar conexión

Durante escaneo offline:
✓ Valida contra lista local
✓ Marca tickets usados localmente
✓ Registra timestamp
✓ Sincroniza cuando vuelva internet

⚠️ Limitación:
   No detecta cancelaciones en tiempo real
   desde la última sincronización
```

---

## 🔄 Modificaciones de Tickets

### Cambio de Asiento

**Proceso:**
```
1. Cliente solicita cambio
2. Admin verifica:
   ├── Disponibilidad nuevo asiento
   ├── Política de cambios
   └── Diferencia de precio (si aplica)
3. Cobra/reembolsa diferencia
4. Invalida ticket original
5. Genera nuevo ticket
6. Envía a cliente
```

**Diferencia de Precio:**
```
De Platea ($50) a VIP ($100):
├── Diferencia: $50
├── Cliente paga adicional
└── Nuevo ticket emitido

De VIP ($100) a Platea ($50):
├── Diferencia: -$50
├── Opciones:
│   ├── Crédito para futuras compras
│   ├── Reembolso
│   └── Upgrade en otro ticket
└── Nuevo ticket emitido
```

### Cancelaciones y Reembolsos

**Solicitud de Cancelación:**
```
1. Cliente solicita cancelación
2. Sistema verifica política de reembolso
3. Calcula monto según días restantes:

Política Estándar:
├── >60 días: 100% reembolso
├── 30-60 días: 75% reembolso
├── 15-30 días: 50% reembolso
├── 7-15 días: 25% reembolso
└── <7 días: No reembolso

4. Procesa reembolso
5. Invalida ticket
6. Libera asiento
7. Notifica al cliente
```

---

## 📊 Reportes de Tickets

### Reporte de Emisión

```
┌────────────────────────────────────────────────┐
│ REPORTE DE TICKETS EMITIDOS                    │
├────────────────────────────────────────────────┤
│ Evento: Concierto Rock 2025                    │
│ Período: 01/10/2025 - 03/11/2025               │
│                                                │
│ Total Emitidos:      750                       │
│ ├─ Vendidos:         700 (93%)                 │
│ ├─ Cortesías:        35 (5%)                   │
│ ├─ Staff:            10 (1%)                   │
│ └─ Cancelados:       5 (1%)                    │
│                                                │
│ Por Zona:                                      │
│ ├─ VIP:              180 / 200 (90%)           │
│ ├─ Platea:           380 / 500 (76%)           │
│ └─ General:          190 / 300 (63%)           │
│                                                │
│ Estado Actual:                                 │
│ ├─ Válidos:          745 (99%)                 │
│ ├─ Cancelados:       5 (1%)                    │
│ └─ Suspendidos:      0                         │
│                                                │
│ Entrega:                                       │
│ ├─ Email enviado:    750 (100%)                │
│ ├─ Descargados:      682 (91%)                 │
│ ├─ Apple Wallet:     234 (31%)                 │
│ └─ Google Wallet:    156 (21%)                 │
└────────────────────────────────────────────────┘
```

### Reporte de Ingreso

**Durante/Después del Evento:**
```
┌────────────────────────────────────────────────┐
│ REPORTE DE INGRESOS AL EVENTO                  │
├────────────────────────────────────────────────┤
│ Evento: Concierto Rock 2025                    │
│ Fecha: 30/12/2025                              │
│                                                │
│ Asistencia:                                    │
│ ├─ Tickets emitidos:  750                      │
│ ├─ Ingresaron:        698 (93%)                │
│ ├─ No asistieron:     52 (7%)                  │
│                                                │
│ Por Puerta:                                    │
│ ├─ Entrada Principal: 456 (65%)                │
│ ├─ Entrada VIP:       180 (26%)                │
│ └─ Entrada Lateral:   62 (9%)                  │
│                                                │
│ Flujo de Ingreso:                              │
│ ├─ 18:00-19:00:       145 personas             │
│ ├─ 19:00-19:30:       389 personas             │
│ ├─ 19:30-20:00:       156 personas             │
│ └─ 20:00+:            8 personas               │
│                                                │
│ Incidencias:                                   │
│ ├─ Tickets duplicados: 3                       │
│ ├─ Tickets inválidos:  2                       │
│ ├─ Problemas técnicos: 1                       │
│ └─ Resueltos:          6 (100%)                │
└────────────────────────────────────────────────┘
```

---

## 💡 Mejores Prácticas

### ✅ Recomendaciones

1. **Envío Inmediato**
   - Generar tickets al recibir pago
   - Email de confirmación instantáneo
   - Incluir múltiples formatos

2. **Comunicación Clara**
   - Instrucciones simples
   - Información completa
   - Soporte disponible

3. **Múltiples Opciones**
   - PDF para imprimir
   - Wallet para móvil
   - Descarga desde cuenta
   - Reenvío fácil

4. **Seguridad Robusta**
   - QR encriptado
   - Validación en tiempo real
   - Detección de duplicados
   - Registros completos

5. **Respaldo**
   - Guardar copias en múltiples lugares
   - Permitir reenvío ilimitado
   - Portal de auto-servicio

### ❌ Errores Comunes

1. **No Verificar Email**
   - Problema: Tickets enviados a email incorrecto
   - Solución: Validación y confirmación

2. **Diseño Poco Claro**
   - Problema: Cliente confundido
   - Solución: Layout estándar y profesional

3. **QR de Baja Calidad**
   - Problema: No escanea
   - Solución: Alta resolución, testing

4. **Sin Instrucciones**
   - Problema: Clientes perdidos
   - Solución: Guía paso a paso

---

## ❓ Preguntas Frecuentes

### ¿Qué pasa si el cliente pierde su ticket?

Puede:
- Descargar desde su cuenta
- Solicitar reenvío por email
- Contactar soporte
- Todos sin costo

### ¿Los tickets son transferibles?

Depende de la configuración del evento:
- Si está permitido: Proceso de transferencia
- Si no: Requiere ID que coincida

### ¿Funciona sin internet?

Wallet passes sí funcionan offline:
- QR se guarda localmente
- Scanner puede trabajar offline
- Sincronización posterior

### ¿Puedo imprimir en casa?

Sí:
- PDF de alta calidad
- Papel normal
- QR escaneable
- Igualmente válido

---

[← Anterior: Reportes](09-reportes.md) | [Volver al Índice](README.md) | [Siguiente: Administración →](11-administracion.md)
