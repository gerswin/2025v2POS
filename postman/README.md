# Venezuelan POS System - Postman Collection

Esta colección de Postman contiene todas las peticiones necesarias para probar y desarrollar con la API del Sistema POS Venezolano.

## 📋 Contenido

### Archivos Incluidos

- `Venezuelan_POS_System.postman_collection.json` - Colección principal con todas las peticiones
- `Venezuelan_POS_Development.postman_environment.json` - Variables de entorno para desarrollo
- `Venezuelan_POS_Production.postman_environment.json` - Variables de entorno para producción

## 🚀 Configuración Inicial

### 1. Importar en Postman

1. Abre Postman
2. Haz clic en "Import" 
3. Arrastra los archivos JSON o selecciona "Upload Files"
4. Importa tanto la colección como los entornos

### 2. Configurar Entorno

1. Selecciona el entorno "Venezuelan POS - Development"
2. Verifica que las variables estén configuradas:
   - `base_url`: http://127.0.0.1:8000
   - `username`: admin
   - `password`: admin123

### 3. Autenticación

1. Ve a la carpeta "🔐 Authentication"
2. Ejecuta "Login - Get JWT Token"
3. Los tokens se guardarán automáticamente en las variables de entorno

## 📚 Estructura de la Colección

### 🔐 Authentication
- Login y obtención de tokens JWT
- Refresh de tokens automático
- Logout

### 🏢 Tenant Management
- Gestión de inquilinos (organizaciones)
- Configuración multi-tenant

### 🎫 Event Management
- Creación y gestión de eventos
- Eventos de admisión general y asientos numerados

### 🎯 Zone & Seating Management
- Configuración de zonas
- Gestión de asientos y mesas
- Verificación de disponibilidad

### 💰 Pricing Management
- Configuración de etapas de precios
- Precios por fila
- Cálculo de precios dinámicos

### 🛒 Sales & Transactions
- Procesamiento de ventas
- Pagos completos y parciales
- Gestión de transacciones

### 💳 Payment Processing
- Procesamiento de pagos
- Múltiples métodos de pago
- Historial de pagos

### 🎟️ Ticket Validation
- Validación por código QR
- Validación por serie fiscal
- Estado de tickets

### 📊 Reports & Analytics
- Reportes de ventas
- Análisis de ocupación
- Mapas de calor

### 📋 Fiscal Compliance
- Reportes X y Z
- Cumplimiento fiscal venezolano
- Series fiscales

### 📱 Offline Sync
- Bloques offline
- Sincronización de ventas
- Estado de sincronización

### 🔍 System Health & Monitoring
- Health checks
- Métricas del sistema
- Esquema de API

## 🔧 Características Especiales

### Auto-Refresh de Tokens
La colección incluye scripts que automáticamente:
- Refrescan tokens expirados
- Manejan errores de autenticación
- Guardan tokens en variables de entorno

### Variables Dinámicas
- IDs se guardan automáticamente después de crear recursos
- Timestamps y UUIDs generados automáticamente
- Claves de idempotencia únicas

### Logging Automático
- Estado de respuestas
- Tiempo de respuesta
- Manejo de errores comunes

## 🧪 Flujo de Pruebas Recomendado

### 1. Configuración Inicial
```
Authentication → Login
Tenant Management → Create Tenant
```

### 2. Configuración de Eventos
```
Event Management → Create Event
Zone & Seating → Create Zone
Pricing Management → Create Price Stage
```

### 3. Procesamiento de Ventas
```
Sales & Transactions → Create Transaction
Payment Processing → Process Payment
Ticket Validation → Validate Ticket
```

### 4. Reportes y Análisis
```
Reports & Analytics → Sales Report
Fiscal Compliance → Generate X-Report
```

## 🌍 Entornos

### Development
- URL: http://127.0.0.1:8000
- Usuario: admin
- Contraseña: admin123

### Production
- URL: https://api.venezuelanpos.com
- Credenciales: Configurar según el entorno

## 📝 Notas Importantes

### Autenticación
- Todos los endpoints (excepto login y health) requieren autenticación JWT
- Los tokens se refrescan automáticamente
- Duración del token: 60 minutos

### Idempotencia
- Las transacciones usan claves de idempotencia para evitar duplicados
- Se generan automáticamente usando `{{$randomUUID}}`

### Zona Horaria
- Todas las fechas deben estar en zona horaria America/Caracas
- Formato: ISO 8601 con offset (-04:00)

### Moneda
- Moneda base: USD
- Tasas de cambio configurables por evento

## 🐛 Troubleshooting

### Error 401 - Unauthorized
- Ejecutar "Login - Get JWT Token"
- Verificar credenciales en el entorno

### Error 403 - Forbidden
- Verificar permisos del usuario
- Confirmar que el tenant esté activo

### Error 404 - Not Found
- Verificar que los IDs en las variables sean correctos
- Confirmar que los recursos existan

### Timeout de Conexión
- Verificar que el servidor esté corriendo
- Confirmar la URL base en el entorno

## 📞 Soporte

Para soporte técnico o preguntas sobre la API:
- Documentación: http://127.0.0.1:8000/api/docs/
- Esquema: http://127.0.0.1:8000/api/schema/
- Health Check: http://127.0.0.1:8000/health/

## 🔄 Actualizaciones

Esta colección se actualiza regularmente. Para obtener la última versión:
1. Descarga los archivos JSON actualizados
2. Reimporta en Postman
3. Verifica las nuevas funcionalidades en el changelog