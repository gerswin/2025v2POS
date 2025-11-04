# Solución al Error de Prometheus con Autoreloader

## 🐛 Problema Identificado

El error `AssertionError: The thread-based exporter can't be safely used when django's autoreloader is active` ocurre porque django-prometheus intenta iniciar un servidor HTTP automático que entra en conflicto con el autoreloader de Django en modo desarrollo.

## ✅ Solución Aplicada

### 1. **Deshabilitar Prometheus en Desarrollo**

**Modificación en `settings.py`:**

```python
# THIRD_PARTY_APPS - Prometheus solo en producción
THIRD_PARTY_APPS = [
    # ... otras apps ...
    "health_check",
    "health_check.db",
    "health_check.cache",
    # django_prometheus removido de aquí
]

# Add Prometheus only in production to avoid autoreloader conflicts
if not DEBUG:
    THIRD_PARTY_APPS.append("django_prometheus")
```

### 2. **Middleware Condicional**

```python
MIDDLEWARE = [
    # ... middleware básico ...
    # Prometheus middleware removido de la lista principal
]

# Add Prometheus middleware only in production
if not DEBUG:
    MIDDLEWARE.insert(0, "django_prometheus.middleware.PrometheusBeforeMiddleware")
    MIDDLEWARE.append("django_prometheus.middleware.PrometheusAfterMiddleware")
```

### 3. **Configuración de Variables de Entorno**

Se agregaron al archivo `.env`:
```env
# Prometheus configuration for development
PROMETHEUS_METRICS_EXPORT_PORT=
PROMETHEUS_METRICS_EXPORT_ADDRESS=
PROMETHEUS_DISABLE_CREATED_SERIES=True
```

## 🚀 Cómo Probar la Solución

### 1. Reiniciar el Servidor Django
```bash
# Si el servidor está corriendo, detenerlo (Ctrl+C)
# Luego reiniciar:
python manage.py runserver
```

### 2. Verificar que Inicia Sin Errores
El servidor debería iniciar normalmente sin el error de Prometheus:
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Django version 5.0.14, using settings 'venezuelan_pos.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### 3. Probar el Dashboard de Pricing
```
URL: http://localhost:8000/pricing/
```

Ahora debería cargar sin el error `FieldError` que corregimos anteriormente.

## 📊 Monitoreo en Desarrollo

### Alternativas para Monitoreo en Desarrollo:

1. **Django Silk** (ya configurado):
   ```
   URL: http://localhost:8000/silk/
   ```

2. **Debug Toolbar** (ya configurado):
   - Visible automáticamente en páginas web

3. **Health Checks**:
   ```
   URL: http://localhost:8000/health/
   ```

4. **Logs Estructurados**:
   ```bash
   tail -f logs/django.log
   tail -f logs/performance.log
   ```

## 🏭 Prometheus en Producción

En producción (cuando `DEBUG=False`), Prometheus estará completamente habilitado:

- ✅ Middleware de Prometheus activo
- ✅ Métricas exportadas en puerto 8001
- ✅ Endpoint `/metrics/` disponible
- ✅ Métricas de negocio personalizadas

### Configuración de Producción:
```env
DEBUG=False
PROMETHEUS_METRICS_EXPORT_PORT=8001
PROMETHEUS_METRICS_EXPORT_ADDRESS=0.0.0.0
```

## 🔧 Comandos de Desarrollo Alternativos

Si necesitas usar Prometheus en desarrollo:

### Opción 1: Usar --noreload
```bash
python manage.py runserver --noreload
```

### Opción 2: Habilitar Prometheus temporalmente
```python
# En settings.py, cambiar temporalmente:
DEBUG = False  # Solo para pruebas
```

### Opción 3: Variables de entorno específicas
```bash
export DEBUG=False
python manage.py runserver
```

## 📋 Verificación de la Solución

### 1. Verificar Configuración:
```python
# En Django shell:
python manage.py shell

from django.conf import settings
print("DEBUG:", settings.DEBUG)
print("Prometheus en INSTALLED_APPS:", 'django_prometheus' in settings.INSTALLED_APPS)
print("Prometheus middleware:", any('prometheus' in m.lower() for m in settings.MIDDLEWARE))
```

### 2. Verificar Servidor:
```bash
# El servidor debería iniciar sin errores
python manage.py runserver
```

### 3. Verificar Funcionalidad:
- ✅ Dashboard de pricing: `http://localhost:8000/pricing/`
- ✅ Admin de Django: `http://localhost:8000/admin/`
- ✅ Health checks: `http://localhost:8000/health/`

## 🎯 Resultado Esperado

Después de aplicar esta solución:

1. ✅ El servidor Django inicia sin errores de Prometheus
2. ✅ El dashboard de pricing funciona correctamente
3. ✅ Todas las funcionalidades están disponibles en desarrollo
4. ✅ Prometheus estará disponible en producción
5. ✅ Herramientas de desarrollo (Silk, Debug Toolbar) siguen funcionando

## 🚨 Si Persisten Problemas

1. **Verificar archivo .env**: Asegurar que las variables estén configuradas
2. **Limpiar cache**: `python manage.py clear_caches` (si existe)
3. **Verificar puerto**: Asegurar que el puerto 8000 esté libre
4. **Revisar logs**: Buscar otros errores en la consola

## 📝 Archivos Modificados

- ✅ `venezuelan_pos/settings.py` - Configuración condicional de Prometheus
- ✅ `.env` - Variables de entorno para desarrollo

Esta solución mantiene todas las funcionalidades de monitoreo en producción mientras evita conflictos en desarrollo.