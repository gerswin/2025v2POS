# Solución para Crear Superusuario

## 🐛 Problema Identificado

El comando estándar `python manage.py createsuperuser` falla con el error:
```
CommandError: Non-admin users must have a tenant assigned
```

Esto ocurre porque el modelo de usuario personalizado requiere que los usuarios no-admin tengan un tenant asignado, pero el comando estándar no maneja los roles correctamente.

## ✅ Solución: Usar el Comando Personalizado

El sistema ya incluye un comando personalizado que maneja correctamente la creación de usuarios admin.

### Opción 1: Crear Solo Admin User
```bash
python manage.py create_admin_user --username gerswin --email g3rswin@gmail.com --password tu_password_seguro
```

### Opción 2: Crear Admin + Tenant Demo (Recomendado)
```bash
python manage.py create_admin_user --username gerswin --email g3rswin@gmail.com --password tu_password_seguro --create-tenant
```

Esta opción crea:
- ✅ **Admin User** (gerswin) - Acceso completo al sistema
- ✅ **Demo Tenant** - Organización de prueba
- ✅ **Tenant Admin** (tenant_admin) - Administrador del tenant
- ✅ **Event Operator** (operator) - Operador de eventos

## 🚀 Comandos Paso a Paso

### 1. Crear el Admin User con Tenant Demo
```bash
python manage.py create_admin_user \
  --username gerswin \
  --email g3rswin@gmail.com \
  --password MiPasswordSeguro123 \
  --create-tenant
```

### 2. Verificar la Creación
```bash
# Iniciar el servidor
python manage.py runserver

# Acceder al admin
# URL: http://localhost:8000/admin/
# Usuario: gerswin
# Password: MiPasswordSeguro123
```

## 👥 Usuarios Creados

Después de ejecutar el comando con `--create-tenant`:

| Usuario | Password | Rol | Tenant | Acceso |
|---------|----------|-----|---------|---------|
| gerswin | MiPasswordSeguro123 | Admin User | - | Admin completo |
| tenant_admin | tenant123 | Tenant Admin | Demo Tenant | Admin del tenant |
| operator | operator123 | Event Operator | Demo Tenant | Operador |

## 🔐 Roles del Sistema

### Admin User (gerswin)
- ✅ Acceso completo a Django Admin
- ✅ Puede gestionar todos los tenants
- ✅ Puede crear/editar usuarios de cualquier tenant
- ✅ No está asociado a ningún tenant específico

### Tenant Admin (tenant_admin)
- ✅ Acceso a Django Admin limitado a su tenant
- ✅ Puede gestionar eventos, usuarios y configuración de su tenant
- ✅ Asociado al "Demo Tenant"

### Event Operator (operator)
- ✅ Acceso a interfaces de operación
- ✅ Puede procesar ventas y gestionar eventos
- ✅ Asociado al "Demo Tenant"

## 🏢 Demo Tenant Creado

El tenant demo incluye:
- **Nombre**: Demo Tenant
- **Slug**: demo-tenant
- **Email**: demo@example.com
- **Prefijo Fiscal**: DT
- **Configuración**: USD, America/Caracas

## 🧪 Probar el Sistema

### 1. Acceder al Admin
```
URL: http://localhost:8000/admin/
Usuario: gerswin
Password: MiPasswordSeguro123
```

### 2. Verificar Tenants
- Ir a "Tenants" → Deberías ver "Demo Tenant"
- Ir a "Users" → Deberías ver los 3 usuarios creados

### 3. Probar APIs
```bash
# Login como admin
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "gerswin",
    "password": "MiPasswordSeguro123"
  }'

# Login como tenant admin
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tenant_admin",
    "password": "tenant123"
  }'
```

## 🔧 Si Necesitas Crear Usuarios Adicionales

### Crear Otro Admin User
```bash
python manage.py create_admin_user --username otro_admin --email admin2@example.com --password password123
```

### Crear Usuario de Tenant (via Django Admin)
1. Acceder al admin como gerswin
2. Ir a "Users" → "Add User"
3. Completar datos y seleccionar:
   - **Tenant**: Demo Tenant (o el que corresponda)
   - **Role**: Tenant Admin o Event Operator

## 🚨 Importante: Seguridad

- ✅ Cambia las passwords por defecto en producción
- ✅ Usa passwords seguras (mínimo 12 caracteres)
- ✅ El Admin User tiene acceso completo - úsalo con cuidado
- ✅ En producción, crea tenants específicos para cada organización

## 📝 Próximos Pasos

Una vez creado el superusuario, puedes continuar con la guía de pruebas:

1. ✅ **Crear Venues** - Lugares para eventos
2. ✅ **Crear Eventos** - Configurar eventos con zonas
3. ✅ **Configurar Precios** - Etapas de precios dinámicos
4. ✅ **Probar Ventas** - Proceso completo de venta de tickets

¡Ya tienes todo listo para empezar a usar el sistema!