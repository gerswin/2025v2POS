# 📦 Tiquemax POS - Docker/Podman Setup Summary

## 📋 Archivos Creados

### Configuración Principal

| Archivo | Descripción |
|---------|-------------|
| `docker-compose.prod.yml` | Configuración de producción con Podman/Docker |
| `Dockerfile.prod` | Dockerfile optimizado multi-stage |
| `.dockerignore` | Archivos a excluir del build |
| `.env.production.example` | Template de variables de entorno |

### Nginx

| Archivo | Descripción |
|---------|-------------|
| `docker/nginx/nginx.conf` | Configuración principal de Nginx |
| `docker/nginx/conf.d/tiquemax.conf` | Virtual host de Tiquemax |
| `docker/nginx/ssl/` | Directorio para certificados SSL |

### PostgreSQL

| Archivo | Descripción |
|---------|-------------|
| `docker/postgres/init.sql` | Script de inicialización de BD |

### Scripts de Deployment

| Archivo | Descripción |
|---------|-------------|
| `deployment/scripts/deploy.sh` | Script principal de deployment |
| `Makefile` | Comandos Make para gestión rápida |

### Documentación

| Archivo | Descripción |
|---------|-------------|
| `deployment/DEPLOYMENT_GUIDE.md` | Guía completa de deployment |
| `deployment/README.md` | Quick start guide |

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                      NGINX                              │
│              (Reverse Proxy + SSL)                      │
│                   Puerto 80/443                         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────┐
│                   DJANGO WEB                             │
│            (Gunicorn + Django 5.0)                       │
│                  Puerto 8000                             │
└──────────────┬────────────────────┬──────────────────────┘
               │                    │
               ↓                    ↓
    ┌──────────────────┐  ┌──────────────────┐
    │   PostgreSQL     │  │      Redis       │
    │  (Base de Datos) │  │ (Cache + Queue)  │
    │   Puerto 5432    │  │   Puerto 6379    │
    └──────────────────┘  └─────────┬────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ↓                             ↓
           ┌─────────────────┐          ┌─────────────────┐
           │ Celery Worker   │          │  Celery Beat    │
           │ (Async Tasks)   │          │  (Scheduler)    │
           └─────────────────┘          └─────────────────┘
                     │
                     ↓
           ┌─────────────────┐
           │     Flower      │
           │  (Monitoring)   │
           │   Puerto 5555   │
           └─────────────────┘
```

---

## 🐳 Servicios en Docker Compose

### 1. **db** (PostgreSQL 15)
- **Imagen**: `postgres:15-alpine`
- **Puerto**: 5432
- **Volumen**: `postgres_data`
- **Healthcheck**: `pg_isready`

### 2. **redis** (Redis 7)
- **Imagen**: `redis:7-alpine`
- **Puerto**: 6379
- **Volumen**: `redis_data`
- **Healthcheck**: `redis-cli ping`

### 3. **web** (Django Application)
- **Build**: `Dockerfile.prod`
- **Puerto**: 8000
- **Volúmenes**:
  - `static_volume` (archivos estáticos)
  - `media_volume` (archivos subidos)
  - `logs_volume` (logs de aplicación)
- **Healthcheck**: `curl /health/`

### 4. **celery_worker** (Procesamiento Asíncrono)
- **Imagen**: Comparte con `web`
- **Comando**: `celery worker`
- **Concurrency**: 4 workers

### 5. **celery_beat** (Tareas Programadas)
- **Imagen**: Comparte con `web`
- **Comando**: `celery beat`
- **Scheduler**: Django Database Scheduler

### 6. **flower** (Monitoreo de Celery)
- **Imagen**: Comparte con `web`
- **Puerto**: 5555
- **Auth**: Basic Auth configurado

### 7. **nginx** (Reverse Proxy)
- **Imagen**: `nginx:1.25-alpine`
- **Puertos**: 80 (HTTP), 443 (HTTPS)
- **Volúmenes**:
  - `static_volume` (servir estáticos)
  - `media_volume` (servir media)
  - Logs de nginx

---

## ⚙️ Configuración de Producción

### Variables de Entorno Críticas

```bash
# Seguridad
SECRET_KEY=<generar-nuevo>
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com

# Base de Datos
DB_NAME=tiquemax_pos
DB_USER=tiquemax
DB_PASSWORD=<contraseña-segura>

# Redis
REDIS_PASSWORD=<contraseña-segura>

# Email
EMAIL_HOST_USER=<tu-email>
EMAIL_HOST_PASSWORD=<contraseña-app>

# Flower
FLOWER_USER=admin
FLOWER_PASSWORD=<contraseña-segura>
```

### Optimizaciones Aplicadas

1. **Multi-stage Build**: Reduce tamaño de imagen final
2. **Non-root User**: Mayor seguridad
3. **Health Checks**: Monitoreo automático
4. **Volume Mounting**: Persistencia de datos
5. **Log Rotation**: Gestión de logs (max 10MB, 3 archivos)
6. **Connection Pooling**: Mejor rendimiento de BD
7. **Redis Cache**: Cache distribuido
8. **Rate Limiting**: Protección contra abuso

### Seguridad

- ✅ Contenedores rootless
- ✅ Variables sensibles en .env
- ✅ SSL/TLS ready
- ✅ Security headers en Nginx
- ✅ Rate limiting configurado
- ✅ Healthchecks automáticos
- ✅ Logs centralizados

---

## 🚀 Quick Start

### Requisitos

```bash
# Instalar Podman
sudo dnf install podman podman-compose  # Fedora/RHEL
sudo apt install podman podman-compose  # Ubuntu/Debian

# Verificar
podman --version
podman-compose --version
```

### Deployment en 3 Pasos

```bash
# 1. Configurar
cp .env.production.example .env.production
nano .env.production  # Editar variables

# 2. Desplegar
chmod +x deployment/scripts/deploy.sh
./deployment/scripts/deploy.sh start

# 3. Crear usuario admin
./deployment/scripts/deploy.sh shell
# En Django shell:
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('admin', 'admin@email.com', 'password')
```

### Con Makefile

```bash
# Desplegar por primera vez
make deploy-first-time

# Crear superusuario
make createsuperuser

# Ver logs
make logs

# Actualizar sistema
make deploy-update
```

---

## 📊 Comandos de Gestión

### Script de Deployment

```bash
./deployment/scripts/deploy.sh [comando]

# Comandos disponibles:
start       # Iniciar sistema
stop        # Detener sistema
restart     # Reiniciar sistema
update      # Actualizar sistema
status      # Ver estado
logs        # Ver logs
backup      # Crear backup
restore     # Restaurar backup
shell       # Django shell
dbshell     # PostgreSQL shell
```

### Makefile Commands

```bash
make help           # Ver todos los comandos
make start          # Iniciar
make stop           # Detener
make logs           # Ver logs
make migrate        # Ejecutar migraciones
make backup         # Backup de BD
make test           # Ejecutar tests
```

### Podman Compose Directo

```bash
# Iniciar servicios
podman-compose -f docker-compose.prod.yml up -d

# Ver logs
podman-compose -f docker-compose.prod.yml logs -f

# Detener servicios
podman-compose -f docker-compose.prod.yml down

# Ejecutar comando en contenedor
podman-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

---

## 💾 Backup y Recuperación

### Backup Automático

```bash
# Agregar a crontab
crontab -e

# Backup diario a las 2 AM
0 2 * * * cd /ruta/proyecto && ./deployment/scripts/deploy.sh backup
```

### Backup Manual

```bash
# Base de datos
./deployment/scripts/deploy.sh backup

# Media files
podman run --rm -v tiquemax_media_volume:/data \
  -v $(pwd)/backups:/backup alpine \
  tar czf /backup/media_$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
# Restaurar base de datos
./deployment/scripts/deploy.sh restore backups/tiquemax_backup_20231103.sql.gz

# Restaurar media files
podman run --rm -v tiquemax_media_volume:/data \
  -v $(pwd)/backups:/backup alpine \
  tar xzf /backup/media_20231103.tar.gz -C /data
```

---

## 📈 Monitoreo

### Health Checks

```bash
# Health endpoint
curl http://localhost/health/

# Servicios individuales
podman ps
podman healthcheck run tiquemax_web
```

### Logs

```bash
# Todos los servicios
make logs

# Servicio específico
make logs-web
make logs-celery
make logs-db

# Logs de nginx
podman exec tiquemax_nginx tail -f /var/log/nginx/access.log
```

### Flower (Celery Monitoring)

Accede a: http://localhost:5555

- Usuario: configurado en `FLOWER_USER`
- Password: configurado en `FLOWER_PASSWORD`

---

## 🔧 Troubleshooting

### Ver estado de contenedores

```bash
podman ps -a
```

### Reiniciar servicio específico

```bash
podman-compose -f docker-compose.prod.yml restart web
```

### Logs detallados

```bash
podman-compose -f docker-compose.prod.yml logs -f --tail=100 web
```

### Acceder a contenedor

```bash
podman exec -it tiquemax_web /bin/bash
```

### Verificar red

```bash
podman network inspect tiquemax_network
```

### Limpiar todo y empezar de nuevo

```bash
# CUIDADO: Elimina todos los datos
podman-compose -f docker-compose.prod.yml down -v
podman system prune -a
./deployment/scripts/deploy.sh start
```

---

## 🌐 URLs de Acceso

Una vez desplegado:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| App Principal | `http://localhost` | Aplicación web |
| Admin | `http://localhost/admin/` | Panel de administración |
| API | `http://localhost/api/` | API REST |
| API Docs | `http://localhost/api/docs/` | Documentación de API |
| Flower | `http://localhost:5555` | Monitoreo de Celery |
| Health Check | `http://localhost/health/` | Health check endpoint |

---

## 📚 Documentación Adicional

- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Guía completa de deployment
- [README.md](./README.md) - Quick start guide
- [Manual de Usuario](../manual/README.md) - Manual completo del sistema

---

## ✅ Checklist de Producción

Antes de deployment en producción:

- [ ] Configurar `.env.production` con valores reales
- [ ] Generar `SECRET_KEY` seguro
- [ ] Configurar contraseñas fuertes
- [ ] Configurar SSL/HTTPS
- [ ] Configurar `ALLOWED_HOSTS`
- [ ] Configurar backups automáticos
- [ ] Configurar firewall
- [ ] Configurar dominio y DNS
- [ ] Probar backup y restore
- [ ] Configurar monitoring/alerting
- [ ] Revisar logs de seguridad
- [ ] Documentar credenciales de forma segura

---

**Última actualización**: Noviembre 2025
**Versión**: 1.0
**Compatibilidad**: Podman 4.0+, Docker 20.10+
