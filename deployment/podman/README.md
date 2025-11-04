# Tiquemax POS - Podman Pod Deployment

Esta guía te ayudará a desplegar el sistema Tiquemax POS usando Podman Pods nativos, que es más eficiente y aprovecha mejor las características específicas de Podman comparado con docker-compose.

## 📋 Tabla de Contenidos

1. [¿Qué es un Podman Pod?](#qué-es-un-podman-pod)
2. [Ventajas vs Docker Compose](#ventajas-vs-docker-compose)
3. [Requisitos](#requisitos)
4. [Quick Start](#quick-start)
5. [Gestión del Pod](#gestión-del-pod)
6. [Auto-inicio con Systemd](#auto-inicio-con-systemd)
7. [Troubleshooting](#troubleshooting)

---

## 🔍 ¿Qué es un Podman Pod?

Un **Podman Pod** es un grupo de uno o más contenedores que:
- Comparten el mismo namespace de red (localhost entre ellos)
- Comparten el mismo namespace de IPC
- Se gestionan como una unidad lógica
- Son similares a los Pods de Kubernetes

**Arquitectura del Pod Tiquemax:**

```
┌─────────────────────────────────────────────────────┐
│                 TIQUEMAX-POS POD                    │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Nginx   │  │  Django  │  │PostgreSQL│         │
│  │  :80/443 │→ │  :8000   │→ │  :5432   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                     ↓                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Flower  │  │  Celery  │  │  Redis   │         │
│  │  :5555   │  │  Worker  │  │  :6379   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
│  Todos los contenedores comparten localhost        │
│  DB_HOST=localhost, REDIS_HOST=localhost           │
└─────────────────────────────────────────────────────┘
         ↓ Puertos expuestos
    80, 443, 5555
```

---

## ⚡ Ventajas vs Docker Compose

### Podman Pods Nativos

✅ **Más ligero**: Sin daemon, menos overhead
✅ **Mejor rendimiento**: Comunicación directa via localhost
✅ **Seguridad mejorada**: Rootless por defecto
✅ **Compatible con Kubernetes**: Puede generar YAML de Kubernetes
✅ **Gestión unificada**: Un solo pod en vez de múltiples contenedores
✅ **Systemd integration**: Fácil auto-inicio

### Docker Compose

- Requiere daemon corriendo
- Red bridge entre contenedores
- Más complejo para rootless
- No genera manifiesto Kubernetes

---

## 🔧 Requisitos

### Software

```bash
# Fedora/RHEL
sudo dnf install podman

# Ubuntu/Debian
sudo apt install podman

# Verificar versión (requiere 4.0+)
podman --version
```

### Hardware Mínimo

- **CPU**: 2 cores
- **RAM**: 4GB (recomendado 8GB)
- **Disco**: 20GB libres

---

## 🚀 Quick Start

### 1. Preparación

```bash
# Navegar al directorio del proyecto
cd /ruta/a/TiquemaxPOS2

# Configurar variables de entorno
cp .env.production.example .env.production
nano .env.production  # Editar configuración
```

**Variables críticas**:
```bash
SECRET_KEY=tu-clave-secreta-aqui
DB_PASSWORD=contraseña-segura-db
REDIS_PASSWORD=contraseña-segura-redis
FLOWER_PASSWORD=contraseña-segura-flower
ALLOWED_HOSTS=tu-dominio.com,localhost
```

### 2. Crear el Pod

```bash
cd deployment/podman
chmod +x create-pod.sh manage-pod.sh
./create-pod.sh
```

El script automáticamente:
- ✅ Crea el pod `tiquemax-pos`
- ✅ Crea todos los volúmenes necesarios
- ✅ Construye la imagen de la aplicación
- ✅ Inicia todos los contenedores
- ✅ Ejecuta migraciones
- ✅ Recolecta archivos estáticos

### 3. Crear Superusuario

```bash
./manage-pod.sh createsuperuser
```

### 4. Acceder al Sistema

- **Aplicación**: http://localhost
- **Admin**: http://localhost/admin/
- **API**: http://localhost/api/
- **Flower**: http://localhost:5555

---

## 🛠️ Gestión del Pod

El script `manage-pod.sh` proporciona todos los comandos necesarios:

### Comandos Básicos

```bash
# Iniciar el pod
./manage-pod.sh start

# Detener el pod
./manage-pod.sh stop

# Reiniciar el pod
./manage-pod.sh restart

# Ver estado
./manage-pod.sh status

# Ver logs
./manage-pod.sh logs           # Todos los contenedores
./manage-pod.sh logs web       # Solo Django
./manage-pod.sh logs db        # Solo PostgreSQL
./manage-pod.sh logs celery-worker  # Solo Celery
```

### Gestión de Base de Datos

```bash
# Ejecutar migraciones
./manage-pod.sh migrate

# Abrir shell de Django
./manage-pod.sh shell

# Abrir shell de PostgreSQL
./manage-pod.sh dbshell
```

### Backup y Restore

```bash
# Crear backup
./manage-pod.sh backup

# Restaurar backup
./manage-pod.sh restore backups/tiquemax_pod_backup_20231103_120000.sql.gz
```

### Actualización del Sistema

```bash
# Actualizar (pull código + rebuild + migrate)
./manage-pod.sh update
```

### Utilidades

```bash
# Recolectar archivos estáticos
./manage-pod.sh collectstatic

# Crear superusuario
./manage-pod.sh createsuperuser

# Ejecutar comando en contenedor
./manage-pod.sh exec web python manage.py check
./manage-pod.sh exec db psql -U tiquemax -d tiquemax_pos

# Health check de todos los servicios
./manage-pod.sh healthcheck
```

### Comandos Avanzados

```bash
# Remover pod (mantiene volúmenes)
./manage-pod.sh remove

# Limpiar todo (ELIMINA DATOS)
./manage-pod.sh clean

# Ver ayuda completa
./manage-pod.sh help
```

---

## 🔄 Auto-inicio con Systemd

Para que el pod inicie automáticamente al arrancar el sistema:

### Instalación

```bash
cd deployment/podman/systemd
chmod +x install-service.sh
./install-service.sh
```

El script configura:
- ✅ Servicio systemd para el pod
- ✅ Auto-inicio en boot
- ✅ Reinicio automático en fallo
- ✅ Linger habilitado (servicio persiste después de logout)

### Gestión del Servicio

```bash
# Iniciar servicio
systemctl --user start tiquemax-pod

# Detener servicio
systemctl --user stop tiquemax-pod

# Reiniciar servicio
systemctl --user restart tiquemax-pod

# Ver estado
systemctl --user status tiquemax-pod

# Ver logs
journalctl --user -u tiquemax-pod -f

# Deshabilitar auto-inicio
systemctl --user disable tiquemax-pod

# Habilitar auto-inicio
systemctl --user enable tiquemax-pod
```

---

## 🔍 Troubleshooting

### Ver Estado del Pod

```bash
# Estado general
podman pod ps

# Estado de contenedores en el pod
podman ps --filter pod=tiquemax-pos

# Inspeccionar pod
podman pod inspect tiquemax-pos
```

### Ver Logs Detallados

```bash
# Logs de un contenedor específico
podman logs -f tiquemax-pos-web
podman logs -f tiquemax-pos-db
podman logs -f tiquemax-pos-celery-worker

# Últimas 100 líneas
podman logs --tail 100 tiquemax-pos-web
```

### Problemas Comunes

#### 1. Pod no inicia

```bash
# Verificar que el pod existe
podman pod exists tiquemax-pos && echo "Existe" || echo "No existe"

# Si no existe, crearlo
cd deployment/podman
./create-pod.sh
```

#### 2. Base de datos no conecta

```bash
# Verificar que PostgreSQL está corriendo
podman ps --filter name=tiquemax-pos-db

# Ver logs de PostgreSQL
podman logs tiquemax-pos-db

# Probar conexión manual
podman exec -it tiquemax-pos-db psql -U tiquemax -d tiquemax_pos
```

#### 3. Redis no conecta

```bash
# Verificar Redis
podman ps --filter name=tiquemax-pos-redis

# Probar conexión (si tienes contraseña)
podman exec -it tiquemax-pos-redis redis-cli -a tu-password ping

# Sin contraseña
podman exec -it tiquemax-pos-redis redis-cli ping
```

#### 4. Contenedor en estado unhealthy

```bash
# Ver healthcheck
podman healthcheck run tiquemax-pos-web

# Ver logs del contenedor
./manage-pod.sh logs web
```

#### 5. Puerto ya en uso

```bash
# Ver qué usa el puerto 80
sudo lsof -i :80

# Detener proceso o cambiar puerto en .env.production
HTTP_PORT=8080
```

### Reinicio Completo

```bash
# Detener y remover pod
./manage-pod.sh stop
./manage-pod.sh remove

# Recrear pod
./create-pod.sh
```

### Limpiar Todo (CUIDADO: Elimina datos)

```bash
# Esto elimina pod, contenedores y volúmenes
./manage-pod.sh clean

# Recrear desde cero
./create-pod.sh
```

---

## 📊 Comandos Nativos de Podman

### Gestión de Pods

```bash
# Listar pods
podman pod ps

# Listar todos los pods (incluso detenidos)
podman pod ps -a

# Inspeccionar pod
podman pod inspect tiquemax-pos

# Ver estadísticas de uso
podman pod stats tiquemax-pos

# Pausar pod
podman pod pause tiquemax-pos

# Reanudar pod
podman pod unpause tiquemax-pos
```

### Gestión de Contenedores en el Pod

```bash
# Listar contenedores del pod
podman ps --filter pod=tiquemax-pos

# Ver estadísticas de contenedores
podman stats --filter pod=tiquemax-pos

# Top de procesos
podman top tiquemax-pos-web
```

### Gestión de Volúmenes

```bash
# Listar volúmenes
podman volume ls

# Inspeccionar volumen
podman volume inspect tiquemax-postgres-data

# Ver uso de espacio
podman system df
```

---

## 🔐 Seguridad

### Rootless vs Rootful

Este sistema soporta ambos modos:

**Rootless (Recomendado)**:
```bash
# Los contenedores corren con tu usuario
podman pod ps  # Sin sudo
```

**Rootful**:
```bash
# Los contenedores corren como root
sudo podman pod ps
```

### Configurar Rootless

```bash
# Configurar rangos de subuids y subgids
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER

# Habilitar linger
loginctl enable-linger $USER

# Reiniciar sesión
logout
```

---

## 🌐 Generar Manifiesto de Kubernetes

Podman puede generar YAML compatible con Kubernetes:

```bash
# Generar manifiesto del pod
podman generate kube tiquemax-pos > tiquemax-k8s.yaml

# Desplegar en Kubernetes
kubectl apply -f tiquemax-k8s.yaml
```

---

## 📝 Diferencias vs docker-compose.prod.yml

| Característica | Podman Pod | Docker Compose |
|----------------|------------|----------------|
| Daemon | No requiere | Requiere dockerd |
| Comunicación | localhost directo | Red bridge |
| Rootless | Nativo | Complejo |
| Performance | Más rápido | Más lento |
| Kubernetes | Genera YAML | No |
| Systemd | Integración nativa | Requiere wrapper |
| Gestión | Un solo pod | Múltiples contenedores |

---

## 📚 Recursos Adicionales

- [Documentación de Podman Pods](https://docs.podman.io/en/latest/markdown/podman-pod.1.html)
- [Guía de Rootless Podman](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md)
- [Podman vs Docker](https://docs.podman.io/en/latest/Tutorials.html)

---

## 💡 Tips y Mejores Prácticas

1. **Usa rootless cuando sea posible**: Mayor seguridad
2. **Habilita auto-inicio con systemd**: Sistema más robusto
3. **Backups automáticos**: Usa cron para backups diarios
4. **Monitoreo**: Revisa logs regularmente con `./manage-pod.sh logs`
5. **Health checks**: Ejecuta `./manage-pod.sh healthcheck` periódicamente
6. **Actualización**: Mantén Podman actualizado: `sudo dnf upgrade podman`

---

## 🆘 Soporte

Para obtener ayuda:
- GitHub Issues: https://github.com/gerswin/2025v2POS/issues
- Documentación Podman: https://docs.podman.io

---

**Última actualización**: Noviembre 2025
**Versión**: 1.0
**Compatibilidad**: Podman 4.0+
