# Venezuelan POS System

Sistema de punto de venta multi-tenant para eventos y venta de boletos desarrollado en Django.

## 🚀 Características Principales

- **Multi-tenant**: Soporte completo para múltiples organizaciones
- **Internacionalización**: Español e Inglés con selector de idioma funcional
- **Sistema de Precios Dinámico**: Precios por zona, fila y asiento
- **Gestión de Eventos**: Venues, zonas y mapas de asientos interactivos
- **Gestión de Clientes**: Con aislamiento por tenant
- **Sistema de Ventas**: Carrito de compras y proceso de checkout
- **API REST**: Endpoints completos con documentación Postman
- **Autenticación**: Sistema completo de usuarios y permisos

## 🛠️ Tecnologías

- **Backend**: Django 4.2, Django REST Framework
- **Base de Datos**: PostgreSQL (SQLite para desarrollo)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Containerización**: Docker & Docker Compose
- **Cache**: Redis (opcional)
- **Servidor Web**: Gunicorn + Nginx (producción)

## 📦 Instalación

### Desarrollo Local

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd TiquemaxPOS2
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar migraciones**
```bash
python manage.py migrate
```

6. **Crear superusuario**
```bash
python manage.py createsuperuser
```

7. **Compilar traducciones**
```bash
python manage.py compilemessages
```

8. **Ejecutar servidor de desarrollo**
```bash
python manage.py runserver
```

### Docker

```bash
# Desarrollo
docker-compose up --build

# Producción
docker-compose -f docker-compose.prod.yml up --build
```

## 🏗️ Arquitectura

### Aplicaciones Django

- **`tenants`**: Gestión multi-tenant
- **`authentication`**: Autenticación y autorización
- **`events`**: Gestión de eventos y venues
- **`zones`**: Zonas y mapas de asientos
- **`pricing`**: Sistema de precios dinámico
- **`customers`**: Gestión de clientes
- **`sales`**: Ventas y transacciones

### Estructura de Directorios

```
venezuelan_pos/
├── apps/                   # Aplicaciones Django
│   ├── tenants/           # Multi-tenancy
│   ├── authentication/    # Auth & permisos
│   ├── events/           # Eventos y venues
│   ├── zones/            # Zonas y asientos
│   ├── pricing/          # Sistema de precios
│   ├── customers/        # Gestión de clientes
│   └── sales/            # Ventas y checkout
├── settings.py           # Configuración Django
├── urls.py              # URLs principales
└── wsgi.py              # WSGI config
```

## 🌐 API Endpoints

### Autenticación
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/user/` - Usuario actual

### Eventos
- `GET /api/events/` - Listar eventos
- `POST /api/events/` - Crear evento
- `GET /api/events/{id}/` - Detalle evento

### Ventas
- `GET /api/sales/cart/` - Ver carrito
- `POST /api/sales/cart/add/` - Agregar al carrito
- `POST /api/sales/checkout/` - Procesar compra

Ver la colección completa de Postman en `/postman/`

## 🧪 Testing

```bash
# Ejecutar todos los tests
python manage.py test

# Tests específicos
python manage.py test venezuelan_pos.apps.sales
```

## 🌍 Internacionalización

El sistema soporta completamente español e inglés:

- Selector de idioma funcional en todas las páginas
- Traducciones completas en archivos `.po`
- Middleware de localización configurado
- URLs localizadas

### Actualizar traducciones

```bash
# Extraer strings para traducir
python manage.py makemessages -l es
python manage.py makemessages -l en

# Compilar traducciones
python manage.py compilemessages
```

## 🔧 Configuración

### Variables de Entorno

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
LANGUAGE_CODE=es
TIME_ZONE=America/Caracas
```

### Multi-tenant

El sistema utiliza subdominios para separar tenants:
- `tenant1.localhost:8000`
- `tenant2.localhost:8000`

## 📊 Características del Sistema

### Sistema de Precios
- Precios base por zona
- Multiplicadores por fila
- Precios específicos por asiento
- Historial de cambios de precios

### Gestión de Asientos
- Editor visual de mapas
- Selección interactiva de asientos
- Estados: disponible, reservado, vendido
- Configuración flexible de filas y asientos

### Carrito de Compras
- Agregar/quitar asientos
- Cálculo automático de precios
- Reserva temporal de asientos
- Proceso de checkout completo

## 🚀 Despliegue

### Producción con Docker

1. Configurar variables de entorno de producción
2. Usar `docker-compose.prod.yml`
3. Configurar proxy reverso (Nginx)
4. Configurar SSL/TLS
5. Configurar base de datos PostgreSQL

### Comandos de Gestión

```bash
# Crear usuario admin para tenant
python manage.py create_admin_user

# Limpiar caches
python manage.py clear_caches

# Estadísticas de cache
python manage.py cache_stats
```

## 📚 Documentación

- **Especificaciones**: `.kiro/specs/venezuelan-pos-system/`
- **API**: Colección Postman en `/postman/`

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit cambios (`git commit -am 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

**Estado del Proyecto**: ✅ Funcional y listo para producción

**Última Actualización**: Octubre 2024