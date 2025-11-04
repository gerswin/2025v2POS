# 3. Gestión de Eventos

## Introducción

Los **eventos** son la razón de ser del sistema. Después de configurar sus lugares, puede crear eventos que utilizarán esos espacios para la venta de tickets.

---

## 🎯 ¿Qué es un Evento?

Un evento es una actividad programada que se realizará en un lugar específico. Ejemplos:
- Conciertos
- Obras de teatro
- Conferencias
- Eventos deportivos
- Festivales
- Presentaciones

Cada evento incluye:
- Información básica (nombre, fecha, descripción)
- Lugar asociado
- Zonas disponibles para venta
- Configuración de precios
- Métodos de pago aceptados
- Opciones de venta (planes de pago, reservas)

---

## ✅ Crear un Nuevo Evento

### Paso 1: Acceder al Módulo

1. En el menú principal, haga clic en **Eventos**
2. Verá la lista de eventos existentes
3. Haga clic en **+ Nuevo Evento**

### Paso 2: Información Básica

#### Datos Principales ✅

**Nombre del Evento**
```
Ejemplo: Concierto Rock Sinfónico 2025
```
- Use nombres descriptivos y atractivos
- Incluya el año si es relevante
- Máximo 200 caracteres

**Seleccionar Lugar**
```
Desplegable: Seleccione de la lista de venues configurados
```
⚠️ **Importante**: El venue debe estar creado previamente

**Fecha y Hora de Inicio**
```
Ejemplo: 15/03/2025  20:00
```
- Use el selector de calendario
- Incluya la hora exacta de inicio
- Considere zona horaria

**Fecha y Hora de Finalización**
```
Ejemplo: 15/03/2025  23:00
```
- Debe ser posterior a la fecha de inicio
- Para eventos de varios días, use la fecha final

#### Descripción del Evento

```
Ejemplo:
Vive una experiencia única donde la potencia del rock se fusiona
con la elegancia de una orquesta sinfónica. Las mejores canciones
del rock clásico interpretadas por músicos de talla mundial.

Incluye:
- 2 horas de espectáculo
- Efectos visuales impresionantes
- Meet & greet con los artistas (solo VIP)
```

💡 **Consejo**: Una buena descripción aumenta las ventas. Incluya:
- Qué esperar del evento
- Artistas o conferencistas
- Duración aproximada
- Beneficios especiales

#### Categoría del Evento

```
Opciones:
- 🎵 Música (Concierto, recital)
- 🎭 Teatro (Obra, stand-up)
- 🏀 Deportes (Partido, competencia)
- 📚 Conferencia (Charla, seminario)
- 🎪 Familiar (Circo, shows infantiles)
- 🎉 Festival (Multi-artistas, feria)
- 🎬 Cine (Estreno, pre-estreno)
- 📅 Otro (Eventos especiales)
```

#### Imagen del Evento

Suba una imagen promocional:
- **Formato**: JPG, PNG
- **Tamaño recomendado**: 1920x1080 px
- **Peso máximo**: 5 MB
- **Proporción**: 16:9 (horizontal)

### Paso 3: Configuración de Zonas

Seleccione qué zonas del venue estarán disponibles:

```
☐ Platea VIP
☐ Platea General
☐ Balcón
☑ Terrazas
```

💡 **Consejo**: No todas las zonas deben estar disponibles. Puede reservar algunas para uso especial.

#### Capacidad por Zona

El sistema muestra automáticamente:
```
Platea VIP:     200 asientos
Platea General: 300 asientos
Terrazas:       100 personas
─────────────────────────────────
Total:          600 tickets
```

---

## 🎫 Configuración de Venta

### Estado del Evento

**Borrador** 🟡
- Evento en preparación
- No visible para clientes
- Permite configuración sin presión
- Use para probar configuraciones

**Activo** 🟢
- Evento publicado
- Visible para venta
- Los clientes pueden comprar tickets
- Monitoreo activo de ventas

**Finalizado** ⚪
- Evento ya realizado
- No se pueden vender más tickets
- Datos históricos disponibles
- Útil para reportes

**Cancelado** 🔴
- Evento cancelado
- Notificación a compradores
- Procesamiento de reembolsos

### Configuración de Ventas

#### Inicio de Ventas

**Fecha de Inicio de Ventas**
```
Ejemplo: 01/12/2024  00:00
```
- Cuándo se habilita la compra
- Puede ser antes de publicar el evento
- Útil para preventas

#### Límites de Compra

**Tickets Máximos por Transacción**
```
Recomendado: 10 tickets
```
- Previene acaparamiento
- Distribuye mejor las ventas
- Facilita el control

**Tickets Mínimos por Transacción**
```
Por defecto: 1 ticket
```
- Use valores mayores para eventos grupales

### Métodos de Pago

Seleccione los métodos aceptados:

```
☑ Efectivo
☑ Transferencia Bancaria
☑ Tarjeta de Débito
☑ Tarjeta de Crédito
☑ Pago Móvil
☑ Zelle
☐ Criptomonedas
```

⚠️ **Importante**: Debe configurar los métodos de pago en **Administración** primero.

---

## 💰 Configuración de Precios

### Vincular Etapas de Precios

Los precios se configuran por separado (ver capítulo 4 y 5), pero aquí los vinculas al evento:

1. Haga clic en **Configurar Precios**
2. Verá las etapas disponibles para el venue
3. Seleccione las etapas a utilizar:

```
Etapa       | Desde      | Hasta      | Estado
──────────────────────────────────────────────
Early Bird  | 01/12/2024 | 31/01/2025 | 🟢 Activa
Regular     | 01/02/2025 | 28/02/2025 | ⏳ Programada
Last Minute | 01/03/2025 | 15/03/2025 | ⏳ Programada
```

### Vista Previa de Precios

El sistema muestra una vista previa:

```
PRECIOS POR ZONA (Early Bird - Hasta 31/01/2025)
══════════════════════════════════════════════
Platea VIP:      $150.00
Platea General:  $100.00
Terrazas:        $ 50.00
```

---

## 🎁 Configuración Avanzada

### Opciones de Pago Parcial

#### Habilitar Planes de Pago

```
☑ Permitir planes de pago
```

Cuando está habilitado:
- Clientes pueden pagar en cuotas
- Se generan reservas automáticas
- Control de vencimientos

#### Depósito Mínimo

```
Ejemplo: 30%
```
- Porcentaje mínimo que el cliente debe pagar inicialmente
- El saldo se puede completar después
```
VIP $150 × 30% = $45 inicial
Saldo restante: $105
```

#### Planes de Cuotas

**Habilitar Cuotas**
```
☑ Permitir plan de cuotas
```

**Número Máximo de Cuotas**
```
Ejemplo: 3 cuotas
```

**Ejemplo Práctico**:
```
Ticket VIP: $150.00
Plan: 3 cuotas

Cuota 1 (Inicial): $50.00
Cuota 2:          $50.00
Cuota 3:          $50.00
```

#### Tiempo de Expiración

**Días para Completar el Pago**
```
Recomendado: 7 días
```
- Tiempo que el cliente tiene para pagar
- Después expira la reserva
- Los asientos se liberan automáticamente

### Códigos Promocionales

#### Crear Código de Descuento

1. Haga clic en **Promociones**
2. Haga clic en **+ Nuevo Código**

**Código**
```
Ejemplo: EARLY2025
```
- Use códigos memorables
- Solo letras y números
- Sin espacios

**Tipo de Descuento**
```
Opciones:
- Porcentaje: 20% de descuento
- Monto Fijo: $10 de descuento
```

**Valor**
```
Ejemplo: 15% o $20.00
```

**Vigencia**
```
Desde: 01/12/2024
Hasta: 15/12/2024
```

**Límite de Uso**
```
Ejemplo: 50 usos
```
- Cuántas veces se puede usar el código
- Vacío = ilimitado

**Zonas Aplicables**
```
☑ Platea VIP
☑ Platea General
☐ Terrazas (excluida)
```

### Configuración Fiscal

**Serie Fiscal**
```
Ejemplo: EV-2025-
```
- Prefijo para la numeración fiscal
- Se completa automáticamente: EV-2025-0001

**Requiere Datos Fiscales**
```
☑ Solicitar RIF/CI del cliente
```
- Para facturación fiscal
- Requerido por ley en Venezuela

---

## 🚀 Publicar el Evento

### Checklist Pre-Publicación

Antes de activar el evento, verifique:

```
☐ Información básica completa
☐ Fechas y horarios correctos
☐ Lugar seleccionado correctamente
☐ Zonas habilitadas
☐ Precios configurados
☐ Métodos de pago activos
☐ Imagen promocional cargada
☐ Descripción atractiva y completa
☐ Límites de compra definidos
☐ Opciones de pago parcial configuradas (si aplica)
☐ Serie fiscal configurada
```

### Activar el Evento

1. Revise toda la configuración
2. Cambie el estado a **Activo**
3. Haga clic en **Guardar y Publicar**

🎉 **¡Listo!** Su evento está ahora disponible para venta.

---

## 📊 Monitoreo del Evento

### Dashboard del Evento

Desde la lista de eventos, haga clic en el nombre para ver:

**Estadísticas en Tiempo Real**
```
┌─────────────────────────────────────────┐
│ CONCIERTO ROCK SINFÓNICO 2025           │
├─────────────────────────────────────────┤
│                                          │
│ 📊 Ocupación: 67%                        │
│                                          │
│ 🎫 Vendidos: 402 / 600                  │
│                                          │
│ 💰 Ingresos: $45,350.00                 │
│                                          │
│ 📅 Días para el evento: 45              │
│                                          │
└─────────────────────────────────────────┘
```

**Ventas por Zona**
```
Platea VIP:     168/200 (84%) 🟢
Platea General: 234/300 (78%) 🟢
Terrazas:       0/100   (0%)  🔴
```

**Últimas Transacciones**
- Lista de ventas recientes
- Estado de pagos
- Planes activos

### Alertas Automáticas

El sistema notifica cuando:
- ⚠️ Se alcanza el 90% de ocupación
- 🎯 Se cumple una meta de ventas
- 📉 Ventas están por debajo de proyección
- ⏰ El evento está por iniciar

---

## ✏️ Editar un Evento

### Qué se Puede Editar

✅ **Siempre**:
- Descripción
- Imagen
- Estado
- Opciones de venta futuras

⚠️ **Con Precaución** (si hay ventas):
- Fecha del evento
- Límites de compra
- Métodos de pago

❌ **No Recomendado** (con ventas activas):
- Lugar del evento
- Zonas habilitadas
- Precios base

### Hacer Cambios

1. Vaya a **Eventos**
2. Haga clic en el nombre del evento
3. Haga clic en **Editar**
4. Modifique los campos necesarios
5. **Guardar Cambios**

⚠️ **El sistema le advertirá si el cambio afecta ventas existentes**

---

## 📧 Comunicación con Compradores

### Enviar Anuncio

Para notificar a todos los compradores:

1. Vaya al detalle del evento
2. Haga clic en **Comunicaciones**
3. Haga clic en **Nuevo Anuncio**

**Asunto**
```
Ejemplo: Cambio de horario - Concierto Rock Sinfónico
```

**Mensaje**
```
Estimado cliente,

Les informamos que el evento "Concierto Rock Sinfónico 2025"
ha cambiado su horario de inicio:

Fecha original: 15/03/2025 a las 20:00
Nueva fecha:    15/03/2025 a las 19:00

Sus tickets siguen siendo válidos. Disculpen las molestias.

Atentamente,
El equipo de producción
```

4. Haga clic en **Enviar a Todos los Compradores**

💡 El sistema envía el mensaje a todos los emails registrados.

---

## 🎯 Duplicar un Evento

Para crear un evento similar:

1. Vaya a la lista de eventos
2. Busque el evento a duplicar
3. Haga clic en **⋮** → **Duplicar**
4. El sistema crea una copia con:
   - Misma configuración
   - Nuevo nombre (+ "Copia")
   - Estado: Borrador
5. Edite fechas y detalles específicos
6. Guarde y publique

💡 **Útil para**: Eventos recurrentes o series de presentaciones.

---

## 🔄 Estados del Evento (Ciclo de Vida)

```
┌──────────┐
│ Borrador │ (Configuración inicial)
└────┬─────┘
     │
     ▼
┌──────────┐
│  Activo  │ (Venta abierta)
└────┬─────┘
     │
     ├────────┐
     │        │
     ▼        ▼
┌──────────┐ ┌───────────┐
│Finalizado│ │Cancelado  │
└──────────┘ └───────────┘
```

---

## 💡 Mejores Prácticas

### ✅ Recomendaciones

1. **Planificación Anticipada**
   - Cree eventos con mínimo 30 días de anticipación
   - Configure precios antes de publicar
   - Pruebe el flujo de compra

2. **Información Completa**
   - Use descripciones detalladas
   - Incluya horarios exactos
   - Especifique qué incluye/no incluye

3. **Imágenes de Calidad**
   - Use imágenes profesionales
   - Optimice el tamaño (no muy pesadas)
   - Mantenga coherencia visual

4. **Precios Escalonados**
   - Use early bird para incentivar compra temprana
   - Aumente precios cerca de la fecha
   - Considere last-minute para llenar espacios

5. **Comunicación Proactiva**
   - Notifique cambios inmediatamente
   - Envíe recordatorios cercanos a la fecha
   - Proporcione información de acceso/parqueo

### ❌ Errores Comunes

1. **Publicar sin Probar**
   - Problema: Errores en producción
   - Solución: Hacer venta de prueba antes de activar

2. **Cambios de Última Hora**
   - Problema: Confusión en compradores
   - Solución: Evitar cambios 48h antes del evento

3. **Sobreventa**
   - Problema: Más tickets que capacidad
   - Solución: Verificar límites de zona

4. **Información Incompleta**
   - Problema: Clientes confundidos
   - Solución: Incluir todo lo necesario desde el inicio

---

## 📝 Ejemplo Práctico Completo

### Caso: Obra de Teatro

**Información Básica:**
- Nombre: "El Avaro" de Molière
- Lugar: Teatro Municipal
- Fecha: 20/02/2025 19:30
- Duración: 2 horas
- Categoría: Teatro

**Descripción:**
```
Una hilarante comedia sobre la avaricia y el amor.
Director: Carlos Méndez
Elenco: 12 actores en escena
Música original en vivo
Vestuario de época
```

**Zonas Habilitadas:**
- Platea Alta (150 asientos)
- Platea Baja (300 asientos)
- Balcones (320 asientos)

**Precios (Early Bird):**
- Platea Alta: $60
- Platea Baja: $40
- Balcones: $25

**Configuración de Venta:**
- Inicio de ventas: 01/12/2024
- Tickets máximos: 8 por compra
- Métodos: Todos excepto criptomonedas
- Planes de pago: Habilitado
- Depósito mínimo: 40%
- Tiempo de pago: 10 días

**Promociones:**
- Código "TEATRO20": 20% descuento
- Válido: Primeros 100 tickets
- Solo Platea Baja y Balcones

---

## ❓ Preguntas Frecuentes

### ¿Puedo tener varios eventos el mismo día en el mismo lugar?

Sí, siempre que los horarios no se superpongan y respete tiempos de limpieza/preparación.

### ¿Qué pasa si cancelo un evento con ventas?

El sistema le guiará en el proceso de reembolso. Debe procesar devoluciones manualmente para cada transacción.

### ¿Puedo cambiar los precios después de publicar?

Sí, pero solo para ventas futuras. Los tickets ya vendidos mantienen su precio original.

### ¿Cuántos eventos puedo tener activos simultáneamente?

No hay límite. Puede gestionar tantos eventos como necesite.

### ¿Puedo restringir la venta a ciertos clientes?

Sí, usando códigos promocionales privados o invitaciones específicas.

---

[← Anterior: Lugares](02-lugares.md) | [Volver al Índice](README.md) | [Siguiente: Precios →](04-precios.md)
