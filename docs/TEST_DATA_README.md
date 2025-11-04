# Scripts de Datos de Prueba

Este directorio contiene scripts para generar, gestionar y limpiar datos de prueba para el sistema POS venezolano.

## 📁 Archivos Disponibles

### 1. `setup_test_data.py` - Generación Completa de Datos
Script principal que crea un conjunto completo de datos de prueba incluyendo:
- 3 tenants (Teatro Nacional, Centro de Convenciones, Poliedro)
- Usuarios admin y operadores para cada tenant
- Venues y eventos realistas
- Zonas con configuración de asientos
- Sistema de precios con etapas y precios por fila
- Clientes de prueba

### 2. `quick_setup.py` - Configuración Rápida
Script simplificado para crear datos mínimos y empezar a probar rápidamente:
- 1 tenant demo
- 1 usuario admin
- 1 venue y evento básico
- 3 zonas (VIP, Premium, General)
- 3 clientes de prueba

### 3. `cleanup_test_data.py` - Limpieza de Datos
Script interactivo para limpiar datos de prueba con opciones:
- Eliminar todos los datos
- Eliminar datos de un tenant específico
- Eliminar solo eventos (mantener tenants y usuarios)
- Mostrar resumen de datos actuales

### 4. `TEST_DATA_README.md` - Esta documentación

## 🚀 Uso de los Scripts

### Configuración Inicial

Antes de ejecutar cualquier script, asegúrate de que el entorno esté configurado:

```bash
# Activar entorno virtual
source .venv/bin/activate

# Ejecutar migraciones
python manage.py migrate

# Compilar traducciones
python manage.py compilemessages
```

### Generación Completa de Datos

Para crear un conjunto completo de datos de prueba:

```bash
python setup_test_data.py
```

**Resultado:**
- 3 organizaciones completas con eventos realistas
- Usuarios con diferentes roles
- Sistema de precios configurado
- Datos listos para demostración

### Configuración Rápida

Para una configuración mínima y rápida:

```bash
python quick_setup.py
```

**Resultado:**
- Configuración básica lista en segundos
- Ideal para desarrollo y pruebas rápidas

### Limpieza de Datos

Para limpiar datos existentes:

```bash
python cleanup_test_data.py
```

El script presenta un menú interactivo con opciones de limpieza.

## 🔑 Credenciales de Acceso

### Después de `setup_test_data.py`:

**Admin Global:**
- Usuario: `admin`
- Contraseña: `admin123`

**Admins por Tenant:**
- `admin_teatro` / `password123` (Teatro Nacional)
- `admin_ccc` / `password123` (Centro de Convenciones)
- `admin_poliedro` / `password123` (Poliedro)

**Operadores:**
- `operador_teatro` / `password123`
- `operador_ccc` / `password123`
- `operador_poliedro` / `password123`

### Después de `quick_setup.py`:

**Usuario Demo:**
- Usuario: `demo_admin`
- Contraseña: `demo123`

## 🌐 URLs de Acceso

### Multi-tenant (con subdominios):
- Teatro Nacional: `http://teatro-nacional.localhost:8000`
- Centro de Convenciones: `http://ccc-eventos.localhost:8000`
- Poliedro: `http://poliedro.localhost:8000`
- Demo: `http://demo.localhost:8000`

### Acceso directo:
- `http://localhost:8000` (detecta automáticamente el tenant)

## 📊 Datos Generados

### `setup_test_data.py` crea:

**Tenants y Usuarios:**
- 3 tenants con configuración completa
- 1 admin global + 6 usuarios (2 por tenant)

**Venues y Eventos:**
- 5 venues en diferentes ubicaciones
- 5 eventos con fechas futuras
- Configuración de eventos con pagos parciales

**Zonas y Precios:**
- Zonas numeradas y generales
- Precios diferenciados por zona
- Etapas de precios (Early Bird, Regular, etc.)
- Precios premium por fila

**Clientes:**
- 10 clientes distribuidos entre tenants
- Datos realistas con cédulas venezolanas
- Preferencias de comunicación configuradas

### `quick_setup.py` crea:

**Configuración Mínima:**
- 1 tenant demo
- 1 usuario admin
- 1 venue y evento
- 3 zonas básicas
- 3 clientes de prueba

## 🛠️ Personalización

### Modificar Datos de Prueba

Para personalizar los datos generados, edita los arrays de configuración en los scripts:

```python
# En setup_test_data.py
tenant_data = [
    {
        'name': 'Tu Organización',
        'slug': 'tu-org',
        # ... más configuración
    }
]
```

### Agregar Nuevos Tipos de Datos

Los scripts están estructurados en métodos separados para cada tipo de dato:
- `create_tenants()`
- `create_users()`
- `create_venues()`
- `create_events()`
- `create_zones_and_pricing()`
- `create_customers()`

Puedes agregar nuevos métodos siguiendo el mismo patrón.

## 🔍 Verificación de Datos

### Verificar Creación Exitosa

```bash
# Verificar tenants
python manage.py shell -c "from venezuelan_pos.apps.tenants.models import Tenant; print(f'Tenants: {Tenant.objects.count()}')"

# Verificar eventos
python manage.py shell -c "from venezuelan_pos.apps.events.models import Event; print(f'Eventos: {Event.objects.count()}')"

# Verificar zonas y asientos
python manage.py shell -c "from venezuelan_pos.apps.zones.models import Zone, Seat; print(f'Zonas: {Zone.objects.count()}, Asientos: {Seat.objects.count()}')"
```

### Acceder al Admin de Django

```bash
# Crear superusuario si no existe
python manage.py createsuperuser

# Acceder a http://localhost:8000/admin/
```

## ⚠️ Consideraciones Importantes

### Entorno de Desarrollo
- Estos scripts están diseñados para desarrollo y pruebas
- **NO ejecutar en producción**
- Los datos generados son ficticios

### Base de Datos
- Los scripts usan transacciones para garantizar consistencia
- Si hay un error, todos los cambios se revierten
- Siempre hacer backup antes de ejecutar en datos importantes

### Rendimiento
- `setup_test_data.py` puede tomar varios minutos en la primera ejecución
- La generación de asientos para zonas grandes puede ser lenta
- `quick_setup.py` es más rápido para pruebas básicas

## 🐛 Solución de Problemas

### Error de Migraciones
```bash
python manage.py migrate
```

### Error de Traducciones
```bash
python manage.py compilemessages
```

### Error de Permisos
```bash
chmod +x setup_test_data.py
chmod +x quick_setup.py
chmod +x cleanup_test_data.py
```

### Error de Dependencias
```bash
pip install -r requirements.txt
```

## 📝 Logs y Debugging

Los scripts incluyen logging detallado que muestra:
- ✅ Elementos creados exitosamente
- ⚠️ Elementos que ya existían
- ❌ Errores durante la creación

Para debugging adicional, puedes modificar los scripts para incluir más información de depuración.

---

**¿Necesitas ayuda?** Revisa los logs de salida de los scripts o consulta la documentación principal del proyecto.