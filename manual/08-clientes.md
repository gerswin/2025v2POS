# 8. Gestión de Clientes

## Introducción

El módulo de **Clientes** le permite gestionar la información de sus compradores, crear perfiles, hacer seguimiento de compras, y ofrecer un servicio personalizado.

---

## 👥 ¿Por Qué Gestionar Clientes?

### Beneficios

**Para su Negocio:**
- Base de datos organizada
- Marketing dirigido
- Análisis de comportamiento
- Fidelización de clientes
- Mejores decisiones comerciales

**Para sus Clientes:**
- Proceso de compra más rápido
- Historial de transacciones accesible
- Ofertas personalizadas
- Mejor servicio al cliente

---

## 📋 Información del Cliente

### Datos Básicos

**Información Personal:**
```
Nombre Completo: Juan Pérez García
Documento de Identidad: V-12345678
Tipo de Documento: Cédula, Pasaporte, RIF
Fecha de Nacimiento: 15/03/1985
```

**Información de Contacto:**
```
Email Principal: juan.perez@email.com
Teléfono Móvil: +58 414-555-1234
Teléfono Alternativo: +58 212-555-5678
```

**Dirección:**
```
País: Venezuela
Estado: Miranda
Ciudad: Caracas
Dirección: Av. Principal, Res. Las Flores, Apto 5-B
Código Postal: 1060
```

### Información Adicional

**Preferencias:**
```
Idioma Preferido: Español
Categoría: VIP, Regular, Corporativo
Intereses: Conciertos, Teatro, Deportes
Zona Preferida: VIP, Platea, General
```

**Marketing:**
```
☑ Acepta recibir emails promocionales
☑ Acepta recibir SMS
☐ Acepta llamadas telefónicas
☑ Acepta notificaciones push
```

---

## ✅ Crear un Cliente

### Método 1: Durante una Venta

El sistema crea el cliente automáticamente durante el checkout:

1. Cliente compra tickets
2. Ingresa información en formulario
3. Sistema crea perfil automáticamente
4. Cliente recibe email de bienvenida

**Ventaja:** Rápido y sin fricción

### Método 2: Registro Manual

Para crear clientes manualmente:

#### Paso 1: Acceder al Módulo

1. Vaya a **Clientes** en el menú principal
2. Haga clic en **+ Nuevo Cliente**

#### Paso 2: Información Básica

Complete el formulario:

```
┌─────────────────────────────────────┐
│ NUEVO CLIENTE                       │
├─────────────────────────────────────┤
│                                     │
│ Información Personal                │
│ ────────────────────────────        │
│ Nombre:        [____________]       │
│ Apellido:      [____________]       │
│ Tipo Doc:      [Cédula ▼]           │
│ Documento:     [____________]       │
│ Fecha Nac:     [DD/MM/AAAA]         │
│                                     │
│ Información de Contacto             │
│ ────────────────────────────        │
│ Email:         [____________]       │
│ Teléfono:      [____________]       │
│ Tel Alt:       [____________]       │
│                                     │
│ Dirección                           │
│ ────────────────────────────        │
│ País:          [Venezuela ▼]        │
│ Estado:        [Miranda ▼]          │
│ Ciudad:        [____________]       │
│ Dirección:     [____________]       │
│                [____________]       │
│                                     │
│ [Cancelar]  [Guardar Cliente]      │
└─────────────────────────────────────┘
```

#### Paso 3: Configuración de Preferencias

```
Categoría del Cliente:
○ Regular (Default)
○ VIP
○ Corporativo
○ Prensa
○ Cortesía

Intereses:
☑ Conciertos
☑ Teatro
☐ Deportes
☐ Conferencias
☐ Festivales

Comunicaciones:
☑ Email marketing
☑ SMS
☐ Llamadas
☑ WhatsApp
```

#### Paso 4: Guardar

1. Revise toda la información
2. Haga clic en **Guardar Cliente**
3. Sistema valida datos
4. Cliente creado con ID único

---

## 🔍 Buscar y Filtrar Clientes

### Panel de Clientes

**Vista Principal:**
```
┌──────────────────────────────────────────────────────┐
│ GESTIÓN DE CLIENTES                                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│ [Buscar...                           ] [🔍]         │
│                                                      │
│ Filtros:                                            │
│ Categoría: [Todos ▼] Estado: [Activos ▼]           │
│ Intereses: [Todos ▼]                                │
│                                                      │
│ Total: 1,234 clientes | [+ Nuevo Cliente]          │
│                                                      │
│ ┌────────────────────────────────────────────────┐  │
│ │ Juan Pérez García                              │  │
│ │ V-12345678 | juan.perez@email.com              │  │
│ │ ⭐ VIP | 15 compras | $2,450 total             │  │
│ │ Última compra: 15/10/2025                      │  │
│ │ [Ver Perfil] [Nueva Venta] [Historial]        │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌────────────────────────────────────────────────┐  │
│ │ María González                                 │  │
│ │ V-87654321 | maria.g@email.com                 │  │
│ │ Regular | 3 compras | $450 total               │  │
│ │ Última compra: 01/11/2025                      │  │
│ │ [Ver Perfil] [Nueva Venta] [Historial]        │  │
│ └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Búsqueda Avanzada

**Buscar por:**
```
• Nombre o apellido
• Documento de identidad
• Email
• Teléfono
• ID de transacción
• Evento asistido
```

**Ejemplo:**
```
Búsqueda: "juan perez"
Resultados: 3 clientes

1. Juan Pérez García (exacto)
2. Juan Carlos Pérez
3. Pedro Juan Pérez
```

### Filtros Disponibles

**Por Categoría:**
```
○ Todos
○ VIP
○ Regular
○ Corporativo
○ Prensa
○ Cortesía
```

**Por Actividad:**
```
○ Todos
○ Activos (compraron en últimos 6 meses)
○ Inactivos (sin compras en 6+ meses)
○ Nuevos (primera compra <30 días)
```

**Por Gasto Total:**
```
○ Todos
○ Alto valor (>$1000)
○ Medio valor ($300-$1000)
○ Bajo valor (<$300)
```

**Por Interés:**
```
☐ Conciertos
☐ Teatro
☐ Deportes
☐ Conferencias
```

---

## 👤 Perfil del Cliente

### Vista Detallada

Al hacer clic en un cliente, verá:

```
┌──────────────────────────────────────────────────────┐
│ PERFIL DE CLIENTE                                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│ 👤 Juan Pérez García                    ⭐ VIP      │
│    V-12345678                                        │
│    juan.perez@email.com                             │
│    +58 414-555-1234                                 │
│                                                      │
│ ┌──────────────────────────────────────────────┐    │
│ │ RESUMEN                                      │    │
│ ├──────────────────────────────────────────────┤    │
│ │ Cliente desde:      15/01/2024               │    │
│ │ Total de compras:   15                       │    │
│ │ Gasto total:        $2,450                   │    │
│ │ Promedio/compra:    $163                     │    │
│ │ Última actividad:   15/10/2025               │    │
│ │ Plan de pago activo: 1                       │    │
│ └──────────────────────────────────────────────┘    │
│                                                      │
│ [Editar Datos] [Nueva Venta] [Enviar Email]        │
│                                                      │
│ ═══════════════════════════════════════════════════ │
│                                                      │
│ 📊 ESTADÍSTICAS                                      │
│                                                      │
│ Eventos Favoritos:                                  │
│ • Conciertos (8 asistencias)                        │
│ • Teatro (5 asistencias)                            │
│ • Deportes (2 asistencias)                          │
│                                                      │
│ Zonas Preferidas:                                   │
│ • VIP (60%)                                          │
│ • Platea (30%)                                       │
│ • General (10%)                                      │
│                                                      │
│ Método de Pago Preferido:                           │
│ • Tarjeta de Crédito (70%)                          │
│ • Transferencia (20%)                               │
│ • Efectivo (10%)                                     │
└──────────────────────────────────────────────────────┘
```

### Pestañas del Perfil

#### 1. Información General
```
Datos personales completos
Preferencias de comunicación
Categorización
Estado de cuenta
```

#### 2. Historial de Compras
```
┌────────────────────────────────────────┐
│ HISTORIAL DE COMPRAS                   │
├────────────────────────────────────────┤
│                                        │
│ 15/10/2025 | TX-123456                 │
│ Concierto Rock 2025                    │
│ 2 x VIP - $400                         │
│ Estado: Completado ✓                   │
│ [Ver Detalle] [Reenviar Tickets]      │
│                                        │
│ 22/09/2025 | TX-123445                 │
│ Obra de Teatro                         │
│ 4 x Platea - $200                      │
│ Estado: Completado ✓                   │
│ [Ver Detalle]                          │
│                                        │
│ [Ver Más...]                           │
└────────────────────────────────────────┘
```

#### 3. Planes de Pago Activos
```
┌────────────────────────────────────────┐
│ PLANES DE PAGO                         │
├────────────────────────────────────────┤
│                                        │
│ #PP-001234                             │
│ Festival de Jazz 2026                  │
│ Total: $600 | Pagado: $300 (50%)       │
│ ██████████░░░░░░░░░░                   │
│ Próxima cuota: $150 - 15/12/2025       │
│ [Ver Plan] [Registrar Pago]           │
└────────────────────────────────────────┘
```

#### 4. Notas y Comentarios
```
┌────────────────────────────────────────┐
│ NOTAS INTERNAS                         │
├────────────────────────────────────────┤
│                                        │
│ 15/10/2025 - María (Ventas)            │
│ Cliente solicitó asientos en primera   │
│ fila. Atención especial en próximas    │
│ compras.                               │
│                                        │
│ 01/09/2025 - Pedro (Admin)             │
│ Cliente VIP desde 2024. Excelente      │
│ historial de pagos.                    │
│                                        │
│ [+ Agregar Nota]                       │
└────────────────────────────────────────┘
```

---

## ⭐ Gestión de Clientes VIP

### Criterios para VIP

Configure los criterios automáticos:

**Por Gasto Total:**
```
Configuración:
├── Gasto mínimo: $1,000
├── Período: Últimos 12 meses
└── Ascenso automático: ✓
```

**Por Frecuencia:**
```
Configuración:
├── Compras mínimas: 10
├── Período: Últimos 12 meses
└── Ascenso automático: ✓
```

**Manual:**
```
Casos especiales:
├── Influencers
├── Prensa
├── Relaciones comerciales
└── Discreción del administrador
```

### Beneficios VIP

**Descuentos:**
```
✓ 10% en todas las compras
✓ 15% en preventas
✓ 20% en eventos seleccionados
✓ Acceso a códigos exclusivos
```

**Prioridades:**
```
✓ Acceso anticipado a ventas
✓ Mejores asientos disponibles
✓ Sin comisión en planes de pago
✓ Atención prioritaria
```

**Extras:**
```
✓ Invitaciones a eventos exclusivos
✓ Meet & greet con artistas
✓ Estacionamiento preferencial
✓ Acceso a lounges VIP
```

### Gestionar Estatus VIP

**Ascender a VIP:**
```
1. Acceda al perfil del cliente
2. Sección "Categoría"
3. Seleccione "VIP"
4. Indique motivo
5. Guarde cambios
6. Sistema envía email de bienvenida VIP
```

**Descender de VIP:**
```
Motivos:
├── Inactividad prolongada (>12 meses)
├── Problemas de pago recurrentes
├── Violación de términos
└── Solicitud del cliente

Proceso:
1. Revisar historial
2. Notificar al cliente (advertencia)
3. Período de gracia: 30 días
4. Cambiar categoría si procede
```

---

## 📧 Comunicación con Clientes

### Emails Automáticos

**Emails Transaccionales:**
```
✓ Confirmación de compra
✓ Tickets adjuntos
✓ Recordatorio de evento (7 días antes)
✓ Recordatorio de evento (1 día antes)
✓ Confirmación de pago recibido
✓ Cambios en el evento
```

**Emails Promocionales:**
```
✓ Nuevos eventos anunciados
✓ Preventas exclusivas
✓ Descuentos personalizados
✓ Cumpleaños del cliente
✓ Eventos similares a sus intereses
```

### Enviar Email Individual

**Desde el Perfil:**
```
1. Acceda al perfil del cliente
2. Haga clic en "Enviar Email"
3. Complete el formulario:

┌─────────────────────────────────────┐
│ ENVIAR EMAIL                        │
├─────────────────────────────────────┤
│ Para: juan.perez@email.com          │
│                                     │
│ Plantilla: [Seleccionar ▼]         │
│                                     │
│ Asunto:                             │
│ [_____________________]             │
│                                     │
│ Mensaje:                            │
│ [_____________________]             │
│ [_____________________]             │
│ [_____________________]             │
│                                     │
│ Adjuntos:                           │
│ [Seleccionar archivos]              │
│                                     │
│ [Cancelar]  [Enviar Email]         │
└─────────────────────────────────────┘
```

### Campañas Masivas

**Crear Campaña:**
```
1. Vaya a **Clientes** → **Campañas**
2. Haga clic en **+ Nueva Campaña**
3. Configure:

Nombre de la campaña:
Preventa Exclusiva VIP

Segmento:
☑ Solo clientes VIP
☐ Clientes activos
☐ Por intereses: [Conciertos]

Plantilla:
[Seleccionar plantilla ▼]

Asunto:
Acceso Exclusivo: Preventa Concierto Rock

Programación:
○ Enviar ahora
● Programar: 05/11/2025 09:00

Preview:
[Vista previa del email]

Destinatarios: 234 clientes

[Guardar] [Programar] [Enviar Prueba]
```

---

## 🎁 Programas de Fidelización

### Sistema de Puntos

**Acumular Puntos:**
```
Compra de Tickets:
├── $1 = 1 punto
├── Compra VIP: $1 = 2 puntos
└── Preventas: Puntos x1.5

Acciones:
├── Referir amigo: 100 puntos
├── Compartir en redes: 25 puntos
├── Reseña del evento: 50 puntos
└── Cumpleaños: 200 puntos bonus
```

**Canjear Puntos:**
```
Niveles:
├── 500 pts = $10 descuento
├── 1,000 pts = $25 descuento
├── 2,500 pts = $75 descuento
└── 5,000 pts = $200 descuento

Beneficios:
├── Upgrade de zona
├── Entrada gratis
├── Merchandising
└── Experiencias VIP
```

### Programa de Referidos

**Cómo Funciona:**
```
1. Cliente recibe código único: JUAN2025
2. Comparte con amigos
3. Amigo usa código y obtiene 10% descuento
4. Cliente original recibe:
   ├── $10 crédito por cada referido
   └── 500 puntos bonus
```

**Configurar en Sistema:**
```
Marketing → Referidos → Configuración

Descuento para nuevo cliente: 10%
Bonificación para referidor: $10
Límite por cliente: 10 referidos/año
Vencimiento de código: Nunca
```

---

## 📊 Análisis de Clientes

### Dashboard de Clientes

```
┌──────────────────────────────────────────────────┐
│ ANÁLISIS DE CLIENTES                             │
├──────────────────────────────────────────────────┤
│                                                  │
│ Total de Clientes:      1,234                    │
│ Nuevos (30 días):       45 (+12%)                │
│ Clientes VIP:           156 (13%)                │
│                                                  │
│ Tasa de Retención:      68%                      │
│ Ticket Promedio:        $124                     │
│ Lifetime Value Prom:    $456                     │
│                                                  │
│ ═════════════════════════════════════════════    │
│                                                  │
│ 📈 CRECIMIENTO                                   │
│   ▁▃▅▇█                                          │
│   +234 clientes en últimos 6 meses               │
│                                                  │
│ 🎯 SEGMENTACIÓN                                  │
│   VIP:        ████░░░░░░  13%                    │
│   Regular:    ██████████  82%                    │
│   Corporativo: █░░░░░░░░░   5%                   │
│                                                  │
│ 💰 REVENUE POR SEGMENTO                          │
│   VIP:        $245,000  (45%)                    │
│   Regular:    $280,000  (52%)                    │
│   Corporativo: $18,000   (3%)                    │
└──────────────────────────────────────────────────┘
```

### Reportes Disponibles

**Reporte de Actividad:**
```
Período: Últimos 3 meses

Clientes Activos:     456
Clientes Nuevos:      123
Clientes Inactivos:   678
Tasa de Conversión:   45%

Mejores Clientes (Top 10):
1. Juan Pérez - $2,450 (15 compras)
2. María González - $1,890 (12 compras)
...
```

**Reporte de Retención:**
```
Cohorte: Clientes de Enero 2025

Mes 1: 100% activos (234 clientes)
Mes 2: 78% activos (182 clientes)
Mes 3: 65% activos (152 clientes)
Mes 6: 52% activos (122 clientes)
```

**Reporte de Segmentación:**
```
Por Intereses:
├── Conciertos:     567 clientes (46%)
├── Teatro:         345 clientes (28%)
├── Deportes:       234 clientes (19%)
└── Conferencias:   88 clientes (7%)

Por Rango de Edad:
├── 18-25: 234 (19%)
├── 26-35: 456 (37%)
├── 36-45: 345 (28%)
├── 46+:   199 (16%)
```

---

## 🔒 Privacidad y Protección de Datos

### GDPR / LOPD Compliance

**Consentimientos:**
```
Obligatorios:
☑ Términos y condiciones
☑ Política de privacidad
☑ Procesamiento de datos de compra

Opcionales:
☐ Marketing por email
☐ Marketing por SMS
☐ Compartir datos con socios
☐ Análisis de comportamiento
```

**Derechos del Cliente:**
```
Acceso:     Ver todos sus datos
Corrección: Actualizar información
Supresión:  "Derecho al olvido"
Portabilidad: Exportar sus datos
Objeción:   Detener procesamiento
```

### Implementar Solicitudes

**Solicitud de Datos:**
```
1. Cliente solicita copia de sus datos
2. Sistema genera reporte completo:
   ├── Información personal
   ├── Historial de compras
   ├── Comunicaciones
   └── Preferencias
3. Envío cifrado en 30 días
```

**Eliminación de Datos:**
```
1. Cliente solicita eliminación
2. Verificar identidad
3. Revisar obligaciones legales
4. Anonimizar datos (si hay compras)
5. Eliminar información personal
6. Confirmar a cliente en 30 días
```

---

## 💡 Mejores Prácticas

### ✅ Recomendaciones

1. **Actualizar Regularmente**
   - Solicitar confirmación de datos anualmente
   - Actualizar automáticamente con cada compra
   - Verificar emails regularmente

2. **Segmentación Efectiva**
   - Crear segmentos significativos
   - Personalizar comunicaciones
   - Medir efectividad de campañas

3. **Comunicación Balanceada**
   - No saturar con emails
   - Contenido relevante y personalizado
   - Respetar preferencias de comunicación

4. **Programa de Fidelización Atractivo**
   - Beneficios claros y alcanzables
   - Múltiples formas de ganar puntos
   - Opciones interesantes de canje

5. **Atención Personalizada**
   - Notas para clientes especiales
   - Reconocer clientes frecuentes
   - Resolver problemas rápidamente

### ❌ Errores Comunes

1. **Spam de Emails**
   - Problema: Emails diarios no relevantes
   - Solución: Máximo 1-2 por semana, segmentados

2. **No Actualizar Datos**
   - Problema: Información desactualizada
   - Solución: Validación en cada compra

3. **Ignorar Clientes VIP**
   - Problema: No diferenciar servicio
   - Solución: Programa VIP robusto

4. **Sin Seguimiento**
   - Problema: Clientes inactivos olvidados
   - Solución: Campañas de reactivación

---

## 🎯 Checklist de Gestión

### Diario
```
☐ Revisar nuevos registros
☐ Responder consultas de clientes
☐ Actualizar estados de planes de pago
☐ Procesar solicitudes especiales
```

### Semanal
```
☐ Análisis de nuevos clientes
☐ Seguimiento de clientes VIP
☐ Revisar campañas activas
☐ Actualizar segmentos
```

### Mensual
```
☐ Reporte de retención
☐ Análisis de lifetime value
☐ Campaña de reactivación
☐ Actualización de beneficios VIP
☐ Limpieza de base de datos
```

---

## ❓ Preguntas Frecuentes

### ¿Puedo importar clientes de otro sistema?

Sí, puede importar via:
- Archivo CSV
- Excel
- API
- Migración asistida

### ¿Cómo fusiono clientes duplicados?

Sistema detecta duplicados y permite:
1. Revisar coincidencias
2. Seleccionar registro principal
3. Fusionar historiales
4. Mantener un solo perfil

### ¿Puedo eliminar un cliente?

Solo si no tiene transacciones. Si tiene compras, puede:
- Anonimizar (cumplimiento legal)
- Marcar como inactivo
- Eliminar datos personales pero mantener transacciones

### ¿Cómo exporto la base de datos?

Vaya a **Clientes** → **Exportar**:
- CSV para Excel
- PDF para impresión
- JSON para integración
- Respeta permisos de privacidad

---

[← Anterior: Pagos Parciales](07-pagos-parciales.md) | [Volver al Índice](README.md) | [Siguiente: Reportes →](09-reportes.md)
