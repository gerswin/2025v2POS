# 🎯 Guía para Probar las Interfaces de Ventas

## ✅ Datos de Prueba Creados

Se han creado exitosamente los siguientes datos de prueba:

### 👤 Usuario de Prueba
- **Usuario:** `sales_operator`
- **Contraseña:** `testpass123`
- **Rol:** Event Operator
- **Tenant:** Test Venue

### 🏢 Venue y Evento
- **Venue:** Teatro Principal (Caracas, Venezuela)
- **Evento:** Concierto de Prueba (activo, en 7 días)

### 🎫 Zonas Configuradas
1. **Zona VIP** (Numerada)
   - 50 asientos (5 filas × 10 asientos)
   - Precio base: $100.00
   - Asientos numerados con selección individual

2. **Zona General** (Admisión General)
   - Capacidad: 200 personas
   - Precio base: $50.00
   - Venta por cantidad

### 👥 Clientes de Prueba
- Juan Pérez (V-12345678, +58 414 123 4567)
- María González (V-87654321, +58 424 987 6543)

## 🚀 Cómo Probar las Interfaces

### 1. Acceso al Sistema
1. Abre tu navegador y ve a: **http://localhost:8000/**
2. Serás redirigido al login: **http://localhost:8000/auth/login/**
3. Ingresa las credenciales:
   - Usuario: `sales_operator`
   - Contraseña: `testpass123`

### 2. Navegación Principal
Una vez logueado, verás el dashboard principal con:
- Menú lateral con opciones: Dashboard, Venues, Events, Pricing, **Sales**
- Información del tenant: "Test Venue"
- Rol del usuario: "Event Operator"

### 3. Dashboard de Ventas
1. Haz clic en **"Sales"** en el menú lateral
2. URL: **http://localhost:8000/sales/**
3. Verás:
   - Estadísticas del día (ventas, ingresos, transacciones pendientes)
   - Lista de eventos activos con botón "Sell Tickets"
   - Transacciones recientes
   - Reservaciones que expiran pronto

### 4. Proceso de Venta Completo

#### Paso 1: Selección de Asientos
1. En el Dashboard de Ventas, haz clic en **"Sell Tickets"** del evento "Concierto de Prueba"
2. URL: **http://localhost:8000/sales/events/[EVENT-ID]/select-seats/**
3. Verás:
   - Información del evento (nombre, venue, fecha)
   - Tarjetas de zonas disponibles (VIP y General)
   - Carrito de compras (inicialmente vacío)

#### Paso 2: Seleccionar Zona VIP (Asientos Numerados)
1. Haz clic en la tarjeta de la **Zona VIP**
2. Se abrirá un modal con:
   - Mapa de asientos interactivo (5 filas × 10 asientos)
   - Leyenda de colores (disponible, seleccionado, vendido, etc.)
   - Indicador de escenario
3. Haz clic en asientos disponibles (verdes) para seleccionarlos
4. Los asientos seleccionados se marcan en azul
5. Aparece resumen de selección con precio total
6. Haz clic en **"Add to Cart"**

#### Paso 3: Seleccionar Zona General (Admisión General)
1. Haz clic en la tarjeta de la **Zona General**
2. Se abrirá un modal con:
   - Selector de cantidad de tickets
   - Botones de selección rápida (1, 2, 3, 4, 5, 10)
   - Indicador de disponibilidad
   - Precio total calculado
3. Selecciona la cantidad deseada
4. Haz clic en **"Add to Cart"**

#### Paso 4: Carrito de Compras
1. El carrito se actualiza automáticamente
2. Puedes ver todos los items agregados
3. Opciones disponibles:
   - Ver detalles de cada item
   - Remover items individuales
   - Limpiar carrito completo
   - **"Proceed to Checkout"**

#### Paso 5: Checkout - Selección de Cliente
1. URL: **http://localhost:8000/sales/checkout/**
2. Opciones disponibles:
   - Seleccionar cliente existente (Juan Pérez o María González)
   - Crear nuevo cliente (formulario completo)
3. Selecciona un cliente existente o crea uno nuevo
4. Haz clic en **"Continue to Payment"**

#### Paso 6: Checkout - Método de Pago
1. URL: **http://localhost:8000/sales/checkout/payment/**
2. Métodos disponibles:
   - Efectivo (Cash Payment) - seleccionado por defecto
   - Tarjeta de Crédito/Débito
   - Transferencia Bancaria
   - PagoMovil
3. Selecciona método de pago
4. Haz clic en **"Continue to Confirmation"**

#### Paso 7: Confirmación Final
1. URL: **http://localhost:8000/sales/checkout/confirm/**
2. Revisa:
   - Información del cliente
   - Detalles de los tickets
   - Información del evento
   - Total a pagar
3. Acepta términos y condiciones
4. Haz clic en **"Complete Purchase"**

#### Paso 8: Transacción Completada
1. Se genera automáticamente:
   - Número de serie fiscal
   - Transacción completada
   - Asientos marcados como vendidos
2. Redirección a página de detalles de transacción
3. Opciones disponibles:
   - Imprimir recibo
   - Ver detalles completos
   - Volver al dashboard

### 5. Gestión de Transacciones
1. Ve a **http://localhost:8000/sales/transactions/**
2. Funcionalidades:
   - Lista de todas las transacciones
   - Filtros por estado, evento, fecha, cliente
   - Búsqueda por serie fiscal o nombre
   - Paginación
   - Detalles de cada transacción

### 6. Gestión de Reservaciones
1. Ve a **http://localhost:8000/sales/reservations/**
2. Funcionalidades:
   - Lista de reservaciones activas
   - Tiempo restante en tiempo real
   - Extender reservaciones
   - Cancelar reservaciones
   - Auto-refresh cada 30 segundos

## 🎨 Características de la Interfaz

### ✨ Interactividad
- **Tiempo Real:** Actualizaciones automáticas de disponibilidad
- **Responsive:** Funciona en desktop, tablet y móvil
- **Animaciones:** Hover effects y transiciones suaves
- **AJAX:** Actualizaciones sin recargar página

### 🎯 Funcionalidades Avanzadas
- **Carrito Persistente:** Se mantiene entre páginas
- **Validación en Tiempo Real:** Disponibilidad de asientos
- **Multi-idioma:** Soporte para español e inglés
- **Recibos Imprimibles:** Formato fiscal completo
- **Dashboard Estadísticas:** KPIs en tiempo real

### 🔒 Seguridad
- **Autenticación:** Login requerido
- **Autorización:** Control por roles
- **CSRF Protection:** Formularios seguros
- **Validación:** Datos validados en frontend y backend

## 🐛 Solución de Problemas

### Problema: "Servidor no responde"
**Solución:** Ejecuta `python manage.py runserver`

### Problema: "Usuario no encontrado"
**Solución:** Ejecuta `python create_sales_test_data.py`

### Problema: "Evento no activo"
**Solución:** Verifica que el evento tenga status "Active" y fechas futuras

### Problema: "Asientos no aparecen"
**Solución:** Verifica que la zona VIP sea tipo "numbered" y tenga asientos generados

## 📞 URLs de Referencia Rápida

- **Login:** http://localhost:8000/auth/login/
- **Dashboard Principal:** http://localhost:8000/
- **Dashboard Ventas:** http://localhost:8000/sales/
- **Transacciones:** http://localhost:8000/sales/transactions/
- **Reservaciones:** http://localhost:8000/sales/reservations/
- **Carrito:** http://localhost:8000/sales/cart/

## 🎉 ¡Listo para Probar!

Las interfaces de ventas están completamente funcionales y listas para usar. Sigue esta guía paso a paso para explorar todas las funcionalidades implementadas.

**¡Disfruta probando el nuevo sistema de ventas!** 🎫✨