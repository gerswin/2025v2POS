# Tiquemax POS - Guía de Deployment con Podman

Esta guía te ayudará a desplegar el sistema Tiquemax POS usando Podman y Podman Compose.

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación de Podman](#instalación-de-podman)
3. [Configuración](#configuración)
4. [Deployment](#deployment)
5. [Gestión del Sistema](#gestión-del-sistema)
6. [Backup y Restore](#backup-y-restore)
7. [Troubleshooting](#troubleshooting)
8. [Producción](#producción)

---

## 🔧 Requisitos Previos

### Hardware Mínimo

- **CPU**: 2 cores
- **RAM**: 4GB (recomendado 8GB)
- **Disco**: 20GB de espacio libre
- **Sistema Operativo**: Linux (RHEL, Fedora, Ubuntu, Debian, etc.)

### Hardware Recomendado para Producción

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disco**: 50GB+ SSD
- **Red**: Conexión estable a internet

---

## 📦 Instalación de Podman

### RHEL/Fedora/CentOS

```bash
# Fedora
sudo dnf install podman podman-compose

# RHEL/CentOS 8+
sudo yum install podman podman-compose
```

### Ubuntu/Debian

```bash
# Ubuntu 20.10+
sudo apt-get update
sudo apt-get install podman podman-compose

# Ubuntu 20.04 (requiere repositorio adicional)
. /etc/os-release
echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
curl -L "https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/Release.key" | sudo apt-key add -
sudo apt-get update
sudo apt-get install podman podman-compose
```

### Verificar Instalación

```bash
podman --version
podman-compose --version
```

### Configurar Podman para Rootless (Recomendado)

```bash
# Configurar rangos de subuids y subgids
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER

# Habilitar linger (mantener servicios activos después del logout)
loginctl enable-linger $USER

# Verificar
podman system info
```

---

## ⚙️ Configuración

### 1. Clonar o Copiar el Proyecto

```bash
cd /opt
sudo git clone https://github.com/tu-usuario/tiquemax-pos.git
sudo chown -R $USER:$USER tiquemax-pos
cd tiquemax-pos
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.production.example .env.production

# Editar configuración
nano .env.production
```

#### Variables Críticas a Configurar:

```bash
# Django Secret Key (generar uno nuevo)
SECRET_KEY=tu-clave-super-secreta-aqui

# Hosts permitidos
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com,localhost

# Base de Datos
DB_NAME=tiquemax_pos
DB_USER=tiquemax
DB_PASSWORD=contraseña-segura-aqui

# Redis
REDIS_PASSWORD=contraseña-redis-aqui

# Email (Gmail ejemplo)
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-contraseña-de-aplicación

# Flower (monitoreo Celery)
FLOWER_USER=admin
FLOWER_PASSWORD=contraseña-flower-aqui
```

#### Generar Secret Key Seguro:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Generar Contraseñas Seguras:

```bash
openssl rand -base64 32
```

### 3. Crear Directorios Necesarios

```bash
mkdir -p backups
mkdir -p docker/nginx/ssl  # Para certificados SSL cuando los tengas
```

### 4. Configurar SSL (Opcional pero Recomendado)

Si tienes certificados SSL:

```bash
# Copiar certificados
cp tu-certificado.crt docker/nginx/ssl/cert.pem
cp tu-llave-privada.key docker/nginx/ssl/key.pem

# Descomentar configuración SSL en docker/nginx/conf.d/tiquemax.conf
```

---

## 🚀 Deployment

### Opción 1: Usar Script Automatizado (Recomendado)

```bash
# Hacer ejecutable el script
chmod +x deployment/scripts/deploy.sh

# Iniciar el sistema
./deployment/scripts/deploy.sh start
```

El script automáticamente:
- ✅ Verifica dependencias
- ✅ Construye las imágenes
- ✅ Inicia los servicios
- ✅ Ejecuta migraciones
- ✅ Recolecta archivos estáticos

### Opción 2: Manual con Podman Compose

```bash
# Construir imágenes
podman-compose -f docker-compose.prod.yml build

# Iniciar servicios
podman-compose -f docker-compose.prod.yml up -d

# Ejecutar migraciones
podman-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Recolectar archivos estáticos
podman-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Crear superusuario
podman-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### Verificar Deployment

```bash
# Ver estado de servicios
./deployment/scripts/deploy.sh status

# Ver logs
./deployment/scripts/deploy.sh logs

# Verificar salud de los servicios
podman ps
```

### Crear Superusuario

```bash
./deployment/scripts/deploy.sh shell

# En el shell de Django:
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('admin', 'admin@tiquemax.com', 'contraseña-segura')
exit()
```

---

## 🔧 Gestión del Sistema

### Comandos Disponibles

```bash
# Iniciar sistema
./deployment/scripts/deploy.sh start

# Detener sistema
./deployment/scripts/deploy.sh stop

# Reiniciar sistema
./deployment/scripts/deploy.sh restart

# Actualizar sistema (pull + rebuild + restart)
./deployment/scripts/deploy.sh update

# Ver estado
./deployment/scripts/deploy.sh status

# Ver logs (todos los servicios)
./deployment/scripts/deploy.sh logs

# Ver logs de un servicio específico
./deployment/scripts/deploy.sh logs web
./deployment/scripts/deploy.sh logs celery_worker

# Abrir shell de Django
./deployment/scripts/deploy.sh shell

# Abrir shell de base de datos
./deployment/scripts/deploy.sh dbshell

# Crear backup
./deployment/scripts/deploy.sh backup

# Restaurar backup
./deployment/scripts/deploy.sh restore backups/archivo.sql.gz
```

### Acceder a los Servicios

Una vez desplegado, puedes acceder a:

- **Aplicación Principal**: http://tu-servidor:80
- **Admin de Django**: http://tu-servidor/admin/
- **API**: http://tu-servidor/api/
- **Flower (Celery Monitoring)**: http://tu-servidor:5555

---

## 💾 Backup y Restore

### Backup Automático

El sistema puede configurarse para backups automáticos:

```bash
# Agregar a crontab
crontab -e

# Backup diario a las 2 AM
0 2 * * * cd /opt/tiquemax-pos && ./deployment/scripts/deploy.sh backup

# Backup cada 6 horas
0 */6 * * * cd /opt/tiquemax-pos && ./deployment/scripts/deploy.sh backup
```

### Backup Manual

```bash
# Crear backup
./deployment/scripts/deploy.sh backup

# El backup se guardará en:
# backups/tiquemax_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Restore desde Backup

```bash
# Listar backups disponibles
ls -lh backups/

# Restaurar backup específico
./deployment/scripts/deploy.sh restore backups/tiquemax_backup_20231103_120000.sql.gz
```

### Backup de Volúmenes

```bash
# Backup de media files
podman run --rm -v tiquemax_media_volume:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media_$(date +%Y%m%d).tar.gz -C /data .

# Backup de static files
podman run --rm -v tiquemax_static_volume:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/static_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 🔍 Troubleshooting

### Ver Logs Detallados

```bash
# Logs de todos los servicios
podman-compose -f docker-compose.prod.yml logs -f

# Logs de un servicio específico
podman-compose -f docker-compose.prod.yml logs -f web
podman-compose -f docker-compose.prod.yml logs -f db
podman-compose -f docker-compose.prod.yml logs -f redis
podman-compose -f docker-compose.prod.yml logs -f celery_worker
```

### Problemas Comunes

#### 1. Servicios no inician

```bash
# Verificar logs
./deployment/scripts/deploy.sh logs

# Verificar variables de entorno
cat .env.production

# Reconstruir imágenes
podman-compose -f docker-compose.prod.yml build --no-cache
```

#### 2. Error de conexión a base de datos

```bash
# Verificar que PostgreSQL esté corriendo
podman ps | grep tiquemax_db

# Verificar logs de PostgreSQL
podman-compose -f docker-compose.prod.yml logs db

# Probar conexión manual
podman-compose -f docker-compose.prod.yml exec db psql -U tiquemax -d tiquemax_pos
```

#### 3. Redis no conecta

```bash
# Verificar Redis
podman ps | grep tiquemax_redis

# Probar conexión
podman-compose -f docker-compose.prod.yml exec redis redis-cli -a tu-password-redis ping
```

#### 4. Permisos de archivos

```bash
# Verificar permisos de volúmenes
podman volume inspect tiquemax_postgres_data
podman volume inspect tiquemax_media_volume

# Si es necesario, recrear volúmenes
podman-compose -f docker-compose.prod.yml down -v
podman-compose -f docker-compose.prod.yml up -d
```

#### 5. Puerto ya en uso

```bash
# Verificar qué está usando el puerto
sudo lsof -i :80
sudo lsof -i :8000

# Cambiar puerto en .env.production
HTTP_PORT=8080
```

### Reinicio Completo

```bash
# Detener todo
podman-compose -f docker-compose.prod.yml down

# Limpiar volúmenes (CUIDADO: elimina datos)
podman-compose -f docker-compose.prod.yml down -v

# Eliminar imágenes
podman rmi tiquemax_web:latest

# Reconstruir desde cero
./deployment/scripts/deploy.sh start
```

---

## 🏭 Producción

### Checklist de Seguridad

Antes de poner en producción, verifica:

- [ ] `DEBUG=False` en `.env.production`
- [ ] Secret key único y seguro
- [ ] Contraseñas fuertes para DB y Redis
- [ ] SSL/HTTPS configurado
- [ ] `ALLOWED_HOSTS` correctamente configurado
- [ ] CSRF_TRUSTED_ORIGINS configurado
- [ ] Firewall configurado (solo puertos 80, 443 abiertos)
- [ ] Backups automáticos configurados
- [ ] Monitoring configurado (Sentry, etc.)
- [ ] Logs rotativos configurados

### Configurar Firewall

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Firewalld (RHEL/Fedora)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Habilitar Servicio Systemd (Autostart)

Crear servicio para que Podman inicie automáticamente:

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/tiquemax.service
```

Contenido:

```ini
[Unit]
Description=Tiquemax POS System
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/tiquemax-pos
ExecStart=/usr/bin/podman-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/podman-compose -f docker-compose.prod.yml down
User=tu-usuario
Group=tu-grupo

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tiquemax
sudo systemctl start tiquemax
sudo systemctl status tiquemax
```

### Monitoreo

#### Prometheus + Grafana (Opcional)

El sistema tiene soporte para Prometheus. Para habilitar:

1. Editar `.env.production`:
```bash
ENABLE_PROMETHEUS=True
```

2. Configurar Prometheus y Grafana (requiere configuración adicional)

#### Logs Centralizados

Configurar envío de logs a servicio externo:

```bash
# Ejemplo con syslog
podman-compose -f docker-compose.prod.yml logs -f | logger -t tiquemax
```

---

## 📚 Recursos Adicionales

### Documentación

- [Documentación de Podman](https://docs.podman.io/)
- [Documentación de Django](https://docs.djangoproject.com/)
- [Documentación de Celery](https://docs.celeryproject.org/)

### Soporte

Para obtener soporte:
- Email: soporte@tiquemax.com
- GitHub Issues: https://github.com/tu-usuario/tiquemax-pos/issues

---

## 📝 Notas Finales

### Diferencias entre Podman y Docker

Podman es compatible con Docker Compose en la mayoría de los casos, pero hay algunas diferencias:

1. **Rootless por defecto**: Podman puede correr sin permisos de root
2. **No hay daemon**: Podman no requiere un daemon corriendo
3. **Seguridad mejorada**: Mejor aislamiento de contenedores
4. **Compatible con systemd**: Fácil integración con systemd

### Migración desde Docker

Si ya tienes Docker Compose corriendo:

```bash
# La sintaxis es casi idéntica
docker-compose → podman-compose
docker → podman
```

### Contribuir

Contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

---

**Última actualización**: Noviembre 2025
**Versión del Sistema**: 1.0
**Mantenedor**: Equipo Tiquemax
