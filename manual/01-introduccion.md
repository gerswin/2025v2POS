# 1. Introducción al Sistema Tiquemax POS

## ¿Qué es Tiquemax POS?

Tiquemax POS es un sistema completo de gestión y venta de tickets para eventos. Permite administrar lugares, crear eventos, configurar precios dinámicos, vender tickets y gestionar pagos de manera eficiente y segura.

---

## 🎯 Características Principales

### Gestión de Lugares
- Creación y administración de venues
- Configuración de zonas (VIP, General, Palcos, etc.)
- Mapas de asientos personalizables
- Entrada general con capacidad controlada

### Gestión de Eventos
- Creación rápida de eventos
- Múltiples eventos simultáneos
- Configuración flexible de fechas
- Estados de evento (Borrador, Activo, Finalizado)

### Sistema de Precios Dinámicos
- **Precios por zona**: Diferentes precios para cada área
- **Precios por fila**: Precios específicos para filas numeradas
- **Etapas de precios**: Precios que cambian automáticamente
- **Triggers de disponibilidad**: Precios que suben cuando quedan pocos tickets

### Ventas Flexibles
- Selección visual de asientos
- Carrito de compras
- Múltiples métodos de pago
- Planes de pago parciales
- Reservas temporales

### Pagos Parciales
- **Planes flexibles**: Cliente paga cuando puede
- **Planes de cuotas**: Pagos programados
- Gestión de saldos pendientes
- Notificaciones automáticas

### Tickets Digitales
- Generación automática de tickets
- Códigos QR únicos
- Envío por email
- Validación en tiempo real

### Reportes y Análisis
- Dashboard en tiempo real
- Reportes de ventas
- Análisis de ocupación
- Reportes financieros

---

## 🖥️ Interfaz del Sistema

### Panel Principal (Dashboard)

El dashboard es su punto de partida. Desde aquí puede ver:

```
┌─────────────────────────────────────────────────┐
│  TIQUEMAX POS - Dashboard                       │
├─────────────────────────────────────────────────┤
│                                                  │
│  📊 Ventas Hoy: $15,450.00                      │
│  🎫 Tickets Vendidos: 234                        │
│  ⏳ Pendientes: 12                               │
│  📅 Eventos Activos: 5                           │
│                                                  │
│  Eventos Activos        Transacciones Recientes │
│  ┌──────────────┐      ┌──────────────────────┐│
│  │ Concierto    │      │ #12345 - $125.00     ││
│  │ Rock 2025    │      │ Cliente: Juan Pérez  ││
│  │ [Vender] →   │      │ Estado: Completado   ││
│  └──────────────┘      └──────────────────────┘│
│                                                  │
└─────────────────────────────────────────────────┘
```

### Menú de Navegación

El menú principal incluye:

- **🏠 Inicio**: Dashboard principal
- **📍 Lugares**: Gestión de venues
- **📅 Eventos**: Crear y gestionar eventos
- **💰 Precios**: Configurar etapas y precios
- **🎫 Ventas**: Proceso de venta
- **💳 Pagos**: Gestión de pagos y planes
- **👥 Clientes**: Base de datos de clientes
- **🎟️ Tickets**: Gestión de tickets digitales
- **📊 Reportes**: Análisis y reportes
- **⚙️ Administración**: Configuración del sistema

---

## 🔐 Acceso al Sistema

### Primer Acceso

1. Abra su navegador web
2. Ingrese la URL: `https://su-dominio.tiquemax.com`
3. Ingrese sus credenciales:
   - **Usuario**: Su email registrado
   - **Contraseña**: Contraseña proporcionada

4. En el primer acceso, se le pedirá cambiar su contraseña

### Roles de Usuario

El sistema maneja diferentes roles:

#### 🔵 Administrador
- Acceso completo al sistema
- Configuración de precios y etapas
- Gestión de usuarios
- Reportes financieros
- Configuración del sistema

#### 🟢 Vendedor
- Acceso al módulo de ventas
- Ver eventos y precios
- Procesar transacciones
- Gestionar clientes
- Ver reportes de ventas

#### 🟡 Supervisor
- Todo lo del vendedor
- Aprobar descuentos
- Cancelar transacciones
- Reportes avanzados

#### 🟠 Auditor
- Solo lectura
- Acceso a reportes
- Auditoría de transacciones

---

## 📱 Navegación del Sistema

### Breadcrumbs (Migas de Pan)

En la parte superior siempre verá su ubicación:
```
Inicio > Eventos > Crear Evento
```

### Botones de Acción

Los botones siguen un código de colores:

- **🔵 Azul**: Acción principal (Guardar, Crear)
- **🟢 Verde**: Confirmación (Completar, Aprobar)
- **🟡 Amarillo**: Advertencia (Editar, Reservar)
- **🔴 Rojo**: Peligro (Eliminar, Cancelar)
- **⚪ Gris**: Navegación (Volver, Cancelar)

### Notificaciones

El sistema muestra notificaciones en la esquina superior derecha:

- ✅ **Verde**: Operación exitosa
- ⚠️ **Amarillo**: Advertencia
- ❌ **Rojo**: Error
- 📘 **Azul**: Información

---

## 🔄 Flujo de Trabajo Típico

### Configuración Inicial (Una sola vez)

1. **Configurar Empresa**
   - Información fiscal
   - Logo y marca
   - Métodos de pago

2. **Crear Lugares**
   - Información del venue
   - Configurar zonas
   - Definir asientos

3. **Configurar Precios**
   - Precios base por zona
   - Etapas de precios
   - Reglas de transición

### Para Cada Evento

1. **Crear Evento**
   - Información básica
   - Seleccionar lugar
   - Configurar fechas

2. **Activar Venta**
   - Publicar evento
   - Habilitar métodos de pago
   - Configurar opciones de venta

3. **Vender Tickets**
   - Seleccionar asientos
   - Procesar pagos
   - Generar tickets

4. **Gestionar Ventas**
   - Monitorear ventas
   - Procesar pagos parciales
   - Validar tickets en el evento

---

## ⚡ Atajos de Teclado

Para usuarios avanzados:

- `Ctrl + N`: Nueva transacción
- `Ctrl + B`: Buscar cliente
- `Ctrl + S`: Guardar (en formularios)
- `Esc`: Cancelar operación
- `F5`: Actualizar dashboard

---

## 💡 Mejores Prácticas

### ✅ Hacer

- Crear eventos con anticipación
- Configurar etapas de precios antes de publicar
- Hacer backup de datos importantes
- Revisar reportes diariamente
- Validar información de clientes

### ❌ Evitar

- Cambiar precios durante ventas activas sin planificación
- Eliminar eventos con ventas realizadas
- Compartir contraseñas entre usuarios
- Ignorar advertencias del sistema

---

## 🆘 Ayuda Rápida

### En Cada Pantalla

Busque el ícono de **ayuda (?)** en la esquina superior derecha para obtener ayuda contextual.

### Centro de Ayuda

Acceda al centro de ayuda completo desde:
```
Menú Usuario → Centro de Ayuda
```

### Videos Tutoriales

Disponibles en:
```
Administración → Tutoriales
```

---

## 📚 Próximos Pasos

Ahora que conoce lo básico del sistema, continúe con:

1. [Gestión de Lugares](02-lugares.md) - Aprenda a crear y configurar venues
2. [Gestión de Eventos](03-eventos.md) - Cree su primer evento
3. [Sistema de Precios](04-precios.md) - Configure precios dinámicos

---

## 🎓 Glosario de Términos

- **Venue**: Lugar físico donde se realiza el evento
- **Zona**: Área del venue (VIP, General, Palco)
- **Etapa**: Período de tiempo con precios específicos
- **Trigger**: Condición que activa un cambio automático
- **Plan de Pago**: Acuerdo de pago parcial con el cliente
- **Reserva**: Asientos bloqueados temporalmente
- **Ticket Digital**: Comprobante electrónico con código QR

---

[← Volver al Índice](README.md) | [Siguiente: Lugares →](02-lugares.md)
