# Tiquemax POS - Quick Deployment

## 🚀 Quick Start

### 1. Preparación

```bash
# Copiar y configurar variables de entorno
cp .env.production.example .env.production
nano .env.production  # Editar configuración
```

### 2. Deployment

```bash
# Opción 1: Script automatizado (recomendado)
chmod +x deployment/scripts/deploy.sh
./deployment/scripts/deploy.sh start

# Opción 2: Podman Compose directo
podman-compose -f docker-compose.prod.yml up -d
```

### 3. Crear Superusuario

```bash
./deployment/scripts/deploy.sh shell
# En el shell de Django:
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('admin', 'admin@email.com', 'password')
```

## 📝 Comandos Disponibles

```bash
./deployment/scripts/deploy.sh [comando]

Comandos:
  start       - Iniciar el sistema
  stop        - Detener el sistema
  restart     - Reiniciar el sistema
  update      - Actualizar y reiniciar
  status      - Ver estado de servicios
  logs        - Ver logs
  backup      - Crear backup de BD
  restore     - Restaurar backup
  shell       - Shell de Django
  dbshell     - Shell de PostgreSQL
  help        - Mostrar ayuda
```

## 🌐 Acceso

Después del deployment:

- **App**: http://localhost
- **Admin**: http://localhost/admin/
- **API**: http://localhost/api/
- **Flower**: http://localhost:5555

## 📚 Documentación Completa

Ver [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) para documentación completa.

## ⚡ Troubleshooting Rápido

### Ver logs
```bash
./deployment/scripts/deploy.sh logs
```

### Reiniciar servicio específico
```bash
podman-compose -f docker-compose.prod.yml restart web
```

### Verificar salud
```bash
podman ps
curl http://localhost/health/
```

### Acceder a contenedor
```bash
podman exec -it tiquemax_web /bin/bash
```

## 🔄 Actualización

```bash
# Pull nuevo código
git pull

# Actualizar sistema
./deployment/scripts/deploy.sh update
```

## 💾 Backup

```bash
# Backup manual
./deployment/scripts/deploy.sh backup

# Backup automático (crontab)
0 2 * * * cd /ruta/proyecto && ./deployment/scripts/deploy.sh backup
```

## 🛠️ Stack Tecnológico

- **Web Server**: Nginx
- **Application**: Django + Gunicorn
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery
- **Container Engine**: Podman

## 📦 Servicios Incluidos

- `db` - PostgreSQL
- `redis` - Redis Cache
- `web` - Django Application
- `celery_worker` - Celery Worker
- `celery_beat` - Celery Scheduler
- `flower` - Celery Monitoring
- `nginx` - Reverse Proxy

## 🔐 Seguridad

Variables críticas a configurar en `.env.production`:

- `SECRET_KEY` - Django secret key
- `DB_PASSWORD` - PostgreSQL password
- `REDIS_PASSWORD` - Redis password
- `FLOWER_PASSWORD` - Flower admin password

## 📞 Soporte

- GitHub Issues: [Reportar problema](https://github.com/tu-usuario/tiquemax-pos/issues)
- Email: soporte@tiquemax.com
