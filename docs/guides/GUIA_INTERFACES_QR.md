# 🎫 Guía Completa: Dónde Ver y Generar Códigos QR

## 📍 **Ubicaciones de los Códigos QR en la Interfaz**

### **1. Dashboard Principal de Tickets**
```
URL: /tickets/
Descripción: Vista principal con todos los tickets digitales
```

**Qué puedes hacer:**
- ✅ Ver lista de todos los tickets generados
- ✅ Filtrar por estado, evento, cliente
- ✅ Buscar tickets específicos
- ✅ Acceder a detalles individuales
- ✅ Descargar PDFs con QR

**Cómo llegar:**
1. Navegar a `/tickets/` en tu navegador
2. O desde el menú principal → "Tickets Digitales"

### **2. Detalle Individual del Ticket**
```
URL: /tickets/ticket/{ticket_id}/
Descripción: Vista completa de un ticket específico con QR visible
```

**Qué puedes ver:**
- 🎯 **Código QR grande y visible** (imagen PNG)
- 📋 Información completa del ticket
- 👤 Datos del cliente
- 🎭 Información del evento
- 📊 Historial de validaciones
- ⚡ Acciones disponibles

**Acciones disponibles:**
- 📥 **Descargar PDF** con QR incluido
- 🔄 **Regenerar QR** (invalida el anterior)
- 📧 **Reenviar al cliente** (email/SMS/WhatsApp)
- ✅ **Validar ahora** (marcar como usado)

### **3. Interfaz de Validación**
```
URL: /tickets/validate/
Descripción: Interfaz para escanear y validar códigos QR
```

**Funcionalidades:**
- 📱 **Campo para escanear QR** o ingresar número
- ⚡ **Validación instantánea** con AJAX
- 🎯 **Dos modos**: "Validar y Usar" / "Solo Verificar"
- ⌨️ **Shortcuts de teclado** (F1, F2, Escape)
- 🔄 **Auto-limpieza** después de validación exitosa

### **4. Dashboard de Validación**
```
URL: /tickets/validation-dashboard/
Descripción: Monitoreo en tiempo real de validaciones
```

**Información mostrada:**
- 📊 **Estadísticas en tiempo real**
- 📋 **Log de validaciones recientes**
- 📈 **Tasas de éxito/fallo**
- 🕐 **Actividad del día**

## 🔄 **Proceso de Generación de QR**

### **Generación Automática**
Los códigos QR se generan **automáticamente** cuando:

1. **Se completa una transacción de venta**
   ```
   Venta Completada → 
   Sistema genera tickets digitales → 
   Cada ticket obtiene QR único → 
   Se envía por email/SMS al cliente
   ```

2. **Desde el Admin de Django**
   ```
   /admin/sales/transaction/
   - Buscar transacción completada
   - Ver "Digital Tickets" relacionados
   - Cada ticket tiene su QR generado
   ```

### **Generación Manual**
Puedes generar tickets manualmente:

1. **Desde la API**
   ```python
   POST /api/v1/tickets/generate/
   {
       "transaction_id": "uuid-de-transaccion",
       "regenerate": false
   }
   ```

2. **Desde el Admin**
   ```
   /admin/sales/digitalticket/
   - Crear nuevo ticket digital
   - El QR se genera automáticamente al guardar
   ```

3. **Regenerar QR existente**
   ```
   En /tickets/ticket/{id}/
   - Botón "Regenerate QR Code"
   - Invalida el QR anterior
   - Genera nuevo QR encriptado
   ```

## 📱 **Formatos de Entrega del QR**

### **1. PDF Descargable**
- **Ubicación**: Botón "Download PDF" en detalle del ticket
- **Contenido**: Ticket completo con QR, información del evento, términos
- **Uso**: Imprimir o mostrar en móvil

### **2. Email Automático**
- **Cuándo**: Automáticamente después de completar compra
- **Contenido**: Email HTML con QR embebido + PDF adjunto
- **Personalizable**: Templates configurables por tenant

### **3. SMS/WhatsApp**
- **Cuándo**: Opcional, configurable por evento
- **Contenido**: Información básica + enlace al ticket digital
- **Uso**: Para clientes sin email

### **4. Visualización Web**
- **Ubicación**: `/tickets/ticket/{id}/`
- **Formato**: Imagen PNG del QR
- **Tamaño**: Optimizado para escaneo (200x200px por defecto)

## 🔍 **Cómo Usar los Códigos QR**

### **Para Validación en Eventos**

1. **Escaneo Directo**
   ```
   Abrir /tickets/validate/
   → Escanear QR con cámara/lector
   → Sistema valida automáticamente
   → Muestra resultado instantáneo
   ```

2. **Entrada Manual**
   ```
   Si no hay escáner:
   → Ingresar número de ticket manualmente
   → Formato: "001-001-01" (FISCAL-ITEM-SECUENCIA)
   → Validar igual que QR
   ```

3. **Validación por Lotes**
   ```
   Para múltiples tickets:
   → Usar endpoint /api/v1/tickets/validation-logs/bulk_validate/
   → Procesar hasta 100 tickets simultáneamente
   ```

### **Para Clientes**

1. **Mostrar en Móvil**
   - Abrir email recibido
   - Mostrar QR en pantalla
   - Personal escanea en entrada

2. **Imprimir Ticket**
   - Descargar PDF del email
   - Imprimir en casa
   - Llevar papel al evento

3. **Backup con Número**
   - Si QR no funciona
   - Usar número de ticket como respaldo
   - Personal puede validar manualmente

## ⚙️ **Configuración y Personalización**

### **Templates de Tickets**
```
URL: /tickets/templates/
```

**Puedes personalizar:**
- 🎨 **Diseño HTML/CSS** del ticket
- 🖼️ **Inclusión de logo** del organizador
- 📐 **Tamaño y orientación** del PDF
- 🎯 **Posición del QR** en el diseño
- 📝 **Información mostrada**

### **Configuración por Tenant**
```python
# En settings.py o configuración del tenant
TICKET_ENCRYPTION_KEY = "clave-de-encriptacion-fernet"
QR_CODE_ERROR_CORRECTION = "L"  # L, M, Q, H
QR_CODE_BOX_SIZE = 10
QR_CODE_BORDER = 4
```

### **Personalización de Entrega**
- **Email templates** personalizables
- **SMS/WhatsApp** con mensajes custom
- **Múltiples idiomas** (español/inglés)
- **Branding** por organizador

## 🔐 **Seguridad del Sistema QR**

### **Encriptación**
- **Algoritmo**: AES-128 con Fernet
- **Datos incluidos**: ID ticket, evento, cliente, fechas
- **Validación**: Hash SHA-256 adicional
- **Rotación**: Soporte para cambio de claves

### **Prevención de Fraude**
- **QR único** por ticket
- **Datos inmutables** en el código
- **Timestamp validation** previene reutilización
- **Audit trail** completo de validaciones

## 🚀 **Flujo Completo de Uso**

### **1. Venta → Generación**
```
Cliente compra → 
Transacción completada → 
Sistema genera tickets digitales → 
QR encriptado creado → 
Email enviado automáticamente
```

### **2. Cliente → Recepción**
```
Cliente recibe email → 
Descarga PDF o guarda QR → 
Llega al evento con ticket digital
```

### **3. Evento → Validación**
```
Personal abre /tickets/validate/ → 
Escanea QR del cliente → 
Sistema valida en tiempo real → 
Permite o deniega entrada → 
Registra en log de auditoría
```

### **4. Monitoreo → Control**
```
Organizador ve /tickets/validation-dashboard/ → 
Monitorea validaciones en tiempo real → 
Revisa estadísticas y logs → 
Detecta problemas o patrones
```

## 📋 **URLs de Referencia Rápida**

| Función | URL | Descripción |
|---------|-----|-------------|
| **Dashboard Principal** | `/tickets/` | Lista todos los tickets |
| **Detalle del Ticket** | `/tickets/ticket/{id}/` | Ver QR y detalles |
| **Validar Tickets** | `/tickets/validate/` | Escanear/validar QR |
| **Dashboard Validación** | `/tickets/validation-dashboard/` | Monitoreo en tiempo real |
| **Templates** | `/tickets/templates/` | Personalizar diseño |
| **Analytics** | `/tickets/analytics/` | Reportes y estadísticas |
| **Admin Django** | `/admin/sales/digitalticket/` | Gestión administrativa |

## 💡 **Consejos de Uso**

### **Para Organizadores**
- ✅ Prueba la validación antes del evento
- ✅ Configura templates personalizados
- ✅ Monitorea el dashboard durante el evento
- ✅ Ten backup manual para emergencias

### **Para Personal de Entrada**
- ✅ Usa shortcuts de teclado (F1, F2)
- ✅ Mantén el campo de entrada enfocado
- ✅ Verifica información del cliente si hay dudas
- ✅ Usa "Solo Verificar" para consultas

### **Para Clientes**
- ✅ Guarda el email del ticket
- ✅ Descarga el PDF como backup
- ✅ Asegúrate de que el QR sea legible
- ✅ Lleva identificación como respaldo

El sistema está completamente implementado y listo para usar en producción, con todas las interfaces necesarias para generar, visualizar, personalizar y validar códigos QR de manera segura y eficiente.