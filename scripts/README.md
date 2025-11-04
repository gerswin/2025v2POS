# Scripts de Utilidad

Esta carpeta contiene scripts de utilidad para el mantenimiento y configuración del sistema.

## Scripts Disponibles

### Gestión de Datos de Prueba
- `setup_test_data.py` - Configura datos de prueba en el sistema
- `cleanup_test_data.py` - Limpia los datos de prueba del sistema
- `quick_setup.py` - Configuración rápida del entorno

### Verificación y Monitoreo
- `verificar_fiscal_admin.py` - Verifica la configuración fiscal y admin
- `test_monitoring_integration.py` - Prueba la integración de monitoreo

## Uso

Ejecuta los scripts desde el directorio raíz del proyecto:

```bash
# Configurar datos de prueba
python scripts/setup_test_data.py

# Limpiar datos de prueba
python scripts/cleanup_test_data.py

# Configuración rápida
python scripts/quick_setup.py

# Verificar configuración fiscal
python scripts/verificar_fiscal_admin.py
```

**Nota:** Asegúrate de tener el entorno virtual activado antes de ejecutar los scripts.