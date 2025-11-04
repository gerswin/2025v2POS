# 5. Gestión de Etapas de Precios

## Introducción

Las **etapas de precios** permiten que los precios cambien automáticamente según el tiempo o eventos específicos. Es la herramienta más poderosa para maximizar ingresos y crear urgencia en los compradores.

---

## 🎯 ¿Qué es una Etapa de Precios?

Una etapa es un **período de tiempo** con **precios específicos** que se aplican automáticamente.

### Ejemplo Visual

```
  LÍNEA DE TIEMPO DEL EVENTO
═══════════════════════════════════════════════════

├──────────┼──────────┼──────────┼──────────┤
│          │          │          │          │
90 días    60 días    30 días    7 días   EVENTO

│◄────────►│◄────────►│◄────────►│◄────────►│
 Super Early  Early    Regular  Last Minute

$80 (-20%)  $100 base  $120(+20%)  $150(+50%)
```

### Componentes de una Etapa

1. **Nombre**: Identificador (ej: "Early Bird")
2. **Fecha Inicio**: Cuándo activa
3. **Fecha Fin**: Cuándo termina
4. **Modificadores**: % de descuento o incremento
5. **Zonas**: Qué áreas aplican
6. **Transiciones**: Cómo cambiar a siguiente etapa

---

## ✅ Crear una Etapa de Precios

### Paso 1: Acceder al Módulo

1. Vaya a **Precios** → **Etapas de Precios**
2. Haga clic en **+ Nueva Etapa**
3. Seleccione el **Venue** correspondiente

### Paso 2: Información Básica

**Nombre de la Etapa**
```
Ejemplo: Early Bird - Concierto Rock 2025
```
💡 Use nombres descriptivos que incluyan el evento

**Descripción**
```
Ejemplo: Descuento especial para compradores tempranos.
Válido solo para los primeros 1000 tickets.
```

**Prioridad**
```
Valor: 1-10 (1 = máxima prioridad)
```
- Útil cuando múltiples etapas pueden aplicar
- La de mayor prioridad gana

### Paso 3: Vigencia

**Fecha y Hora de Inicio**
```
Ejemplo: 01/12/2024 00:00
```

**Fecha y Hora de Finalización**
```
Ejemplo: 31/01/2025 23:59
```

💡 **Consejo**: Configure con anticipación y el sistema activará automáticamente.

### Paso 4: Tipo de Etapa

Seleccione el tipo:

#### Tipo A: Descuento Porcentual 📉

**Ejemplo**:
```
Descuento: 20%
Precio Base VIP: $150
Precio con Descuento: $120
```

Útil para: Early birds, promociones

#### Tipo B: Incremento Porcentual 📈

**Ejemplo**:
```
Incremento: 30%
Precio Base VIP: $150
Precio con Incremento: $195
```

Útil para: Last minute, alta demanda

#### Tipo C: Precio Fijo 💵

**Ejemplo**:
```
Precio Especial: $99
(Independiente del precio base)
```

Útil para: Promociones especiales, lanzamientos

#### Tipo D: Modificadores Múltiples 🎚️

**Ejemplo**:
```
Por Zona:
- VIP: -15%
- General: -20%
- Terrazas: -25%
```

Útil para: Estrategias complejas

### Paso 5: Configurar Modificadores

#### Para Descuento/Incremento Porcentual:

**Modificador General**
```
Todas las zonas: -20%
```

**O Modificadores por Zona**:
```
VIP:      -15%
General:  -20%
Balcón:   -25%
Terrazas: -30%
```

#### Para Precio Fijo:

**Por Zona**:
```
VIP:      $99
General:  $79
Balcón:   $59
Terrazas: $39
```

### Paso 6: Condiciones Adicionales

**Límite de Tickets**
```
Ejemplo: 1000 tickets
```
- La etapa termina al venderse X tickets
- Aunque no haya expirado por fecha

**Zonas Aplicables**
```
☑ Platea VIP
☑ Platea General
☐ Balcón (excluido)
☑ Terrazas
```

**Días Mínimos Antes del Evento**
```
Ejemplo: 7 días
```
- La etapa no aplica si faltan menos de X días

### Paso 7: Guardar y Activar

1. Revise toda la configuración
2. Seleccione el estado:
   - **🟡 Programada**: Activará automáticamente
   - **🟢 Activa**: Inicia inmediatamente
   - **⚪ Inactiva**: No se aplica

3. Haga clic en **Guardar Etapa**

---

## 🔄 Transiciones Automáticas

Las transiciones determinan cómo una etapa cambia a la siguiente.

### Tipos de Transición

#### 1. Por Fecha y Hora ⏰

**Más Común**
```
Early Bird finaliza: 31/01/2025 23:59
Regular inicia:      01/02/2025 00:00
```

El sistema cambia automáticamente a medianoche.

#### 2. Por Cantidad Vendida 📊

```
Early Bird: Primeros 500 tickets
Regular: Siguientes 800 tickets
Last Minute: Últimos 200 tickets
```

Cambia cuando se alcanza el límite.

#### 3. Por Disponibilidad Restante 📉

```
Más de 50% disponible: Early Bird
25-50% disponible: Regular
Menos de 25%: Last Minute
```

Se basa en % de ocupación.

#### 4. Manual 👤

```
Un administrador activa la siguiente etapa
```

Útil para eventos especiales.

### Configurar Transiciones

1. En la etapa, vaya a **Transiciones**
2. Haga clic en **+ Nueva Transición**

**Condición**:
```
Opciones:
- Al finalizar fecha
- Al vender X tickets
- Al alcanzar Y% ocupación
- Manualmente
```

**Etapa Siguiente**:
```
Seleccione: Regular
```

**Notificar**:
```
☑ Enviar email a administradores
☑ Mostrar alerta en dashboard
☑ Publicar en redes (si está conectado)
```

---

## 📊 Monitoreo de Etapas

### Dashboard de Etapas

En tiempo real puede ver:

```
┌─────────────────────────────────────────────┐
│ MONITOR DE ETAPAS                           │
├─────────────────────────────────────────────┤
│                                              │
│ Etapa Activa: EARLY BIRD                    │
│ ━━━━━━━━━━━━━━░░░░░░░░░░  60%              │
│                                              │
│ Tiempo Restante: 12 días 5 horas            │
│ Tickets Vendidos: 450 / 1000                │
│                                              │
│ Próxima Etapa: REGULAR                      │
│ Inicia: 01/02/2025 00:00                    │
│ Precios suben aprox: +25%                   │
│                                              │
│ Ingresos Esta Etapa: $54,000                │
│ Proyección: $90,000                         │
│                                              │
└─────────────────────────────────────────────┘
```

### Alertas Automáticas

El sistema notifica:

⏰ **24 horas antes** de cambio de etapa
```
"Early Bird termina mañana. Comunique a clientes"
```

📈 **90% de cupo** vendido en etapa
```
"Early Bird casi agotado. Considere extensión"
```

⚠️ **Ventas muy lentas**
```
"Solo 20% vendido. Considere descuento adicional"
```

---

## 🎨 Personalización Avanzada

### Etapas con Múltiples Triggers

Combine tiempo + disponibilidad:

```
EARLY BIRD
├── Inicia: 01/12/2024
├── Finaliza: 31/01/2025 O al vender 1000 tickets
└── Lo que ocurra primero

Si se venden 1000 tickets el 15/01:
→ Etapa termina 15/01 (no espera hasta 31/01)
```

### Etapas Superpuestas

Para casos especiales:

```
Etapa A: Flash Sale Viernes
  └ Vigencia: Solo viernes -30%
  └ Prioridad: 1 (máxima)

Etapa B: Early Bird
  └ Vigencia: Diciembre-Enero -20%
  └ Prioridad: 5 (normal)

Resultado: Viernes aplica -30%, otros días -20%
```

### Etapas por Código

Requiere código promocional:

```
Etapa: VIP ACCESS
  └ Código Requerido: VIP2025
  └ Descuento: 40%
  └ Límite: 50 usos
```

Solo quienes tengan el código acceden al precio.

---

## 📈 Estrategias de Etapas

### Estrategia 1: Escalera Clásica

**4 Etapas Lineales**

```
1. Super Early (90+ días): -30%
   └ Meta: 20% de capacidad

2. Early Bird (60-89 días): -20%
   └ Meta: 40% de capacidad (acumulado 60%)

3. Regular (30-59 días): Precio base
   └ Meta: 30% de capacidad (acumulado 90%)

4. Last Minute (0-29 días): +20%
   └ Meta: Llenar el restante 10%
```

**Ventajas**:
- Simple de entender
- Crea urgencia clara
- Predecible

**Desventajas**:
- Poco flexible
- No reacciona a demanda

### Estrategia 2: Dinámica Pura

**Basada en Disponibilidad**

```
100-75% disponible: Base (100%)
74-50% disponible: +10%
49-25% disponible: +25%
24-0% disponible: +50%
```

**Ventajas**:
- Maximiza cada momento
- Responde a demanda real
- No pierde oportunidades

**Desventajas**:
- Impredecible para clientes
- Puede generar quejas

### Estrategia 3: Híbrida Inteligente

**Combina Tiempo + Demanda**

```
Fase 1 (90-60 días):
  └ Si < 30% vendido: -25%
  └ Si 30-60% vendido: -20%
  └ Si > 60% vendido: -10%

Fase 2 (59-30 días):
  └ Si < 50% vendido: -10%
  └ Si 50-75% vendido: Base
  └ Si > 75% vendido: +15%

Fase 3 (29-0 días):
  └ Si < 70% vendido: Base
  └ Si 70-90% vendido: +20%
  └ Si > 90% vendido: +40%
```

**Ventajas**:
- Muy flexible
- Óptima para maximizar
- Adaptable

**Desventajas**:
- Compleja de configurar
- Requiere monitoreo

### Estrategia 4: Flash Sales

**Descuentos Sorpresa**

```
Lunes: Regular
Martes: Flash 24h (-35%)
Miércoles: Regular
Jueves: Regular
Viernes: Flash 48h (-25%)
Fin de Semana: Regular
```

**Ventajas**:
- Genera expectativa
- Reactiva ventas lentas
- Viralizable en redes

**Desventajas**:
- Puede molestar a compradores regulares
- Entrena a esperar descuentos

---

## 🎯 Ejemplo Práctico Completo

### Caso: Festival de Música Electrónica

**Evento**: Electroshock Festival 2025
**Fecha**: 20/03/2025
**Capacidad**: 15,000 personas
**Anuncio**: 01/09/2024

#### Configuración de Etapas

**Etapa 1: SUPER EARLY BIRD**
```
Vigencia: 01/09/2024 - 31/10/2024 (60 días)
Modificador: -35%
Límite: 2,000 tickets
Condición: Finaliza al vender 2,000 o llegar a fecha

Precios:
- GA: $65 (base $100)
- VIP: $97 (base $150)
- Premium: $162 (base $250)

Transición: Automática a Early Bird
```

**Etapa 2: EARLY BIRD**
```
Vigencia: 01/11/2024 - 31/12/2024 (60 días)
Modificador: -25%
Límite: 5,000 tickets (acumulado 7,000)
Condición: Finaliza al vender cuota o llegar a fecha

Precios:
- GA: $75 (base $100)
- VIP: $112 (base $150)
- Premium: $187 (base $250)

Transición: Automática a Advance
```

**Etapa 3: ADVANCE**
```
Vigencia: 01/01/2025 - 28/02/2025 (59 días)
Modificador: -10%
Límite: 6,000 tickets (acumulado 13,000)

Precios:
- GA: $90 (base $100)
- VIP: $135 (base $150)
- Premium: $225 (base $250)

Transición: Automática a Regular
```

**Etapa 4: REGULAR**
```
Vigencia: 01/03/2025 - 15/03/2025 (15 días)
Modificador: 0% (precio base)
Límite: Hasta 95% de capacidad

Precios:
- GA: $100
- VIP: $150
- Premium: $250

Transición: Automática a Last Minute
```

**Etapa 5: LAST MINUTE**
```
Vigencia: 16/03/2025 - 20/03/2025 (hasta evento)
Modificador: +30%
Límite: Hasta agotarse

Precios:
- GA: $130 (base $100)
- VIP: $195 (base $150)
- Premium: $325 (base $250)

Transición: Finaliza con el evento
```

#### Resultados Proyectados

```
Etapa            | Tickets | Precio Prom | Ingresos
──────────────────────────────────────────────────
Super Early      | 2,000   | $108        | $216,000
Early Bird       | 5,000   | $125        | $625,000
Advance          | 6,000   | $150        | $900,000
Regular          | 1,500   | $167        | $250,000
Last Minute      | 500     | $217        | $108,000
──────────────────────────────────────────────────
TOTAL            | 15,000  | $133 prom   | $2,099,000
```

#### Comunicación por Etapa

**Super Early**:
```
"¡Aprovecha! Tickets 35% OFF solo por tiempo limitado"
Redes: Post diario contando tickets restantes
```

**Early Bird**:
```
"Última oportunidad de ahorro. 25% OFF termina pronto"
Email: A lista de espera y compradores anteriores
```

**Advance**:
```
"Pre-venta con 10% descuento. Los precios suben en marzo"
Push: Notificación móvil 7 días antes de terminar
```

**Regular**:
```
"Precios regulares. Última etapa antes de Last Minute"
Presencia: Activar campañas pagas
```

**Last Minute**:
```
"¡Faltan 5 días! Últimos tickets disponibles"
Urgencia máxima en todos los canales
```

---

## 💡 Mejores Prácticas

### ✅ Hacer

1. **Comunicar Claramente**
   - Muestre un countdown: "Suben en 3 días"
   - Explique por qué vale comprar ahora
   - Sea transparente sobre siguiente etapa

2. **Test A/B**
   - Pruebe diferentes duraciones
   - Compare descuentos 20% vs 30%
   - Analice qué etapa vende mejor

3. **Crear Urgencia Real**
   - Use límites de tickets
   - Countdowns visibles
   - Notificaciones "Últimas horas"

4. **Flexibilidad**
   - Esté listo para ajustar
   - Si vende muy rápido, considere nueva etapa
   - Si es muy lento, ofrezca descuentos flash

5. **Documentar**
   - Registre qué funcionó
   - Compare con eventos pasados
   - Compile "receta" de éxito

### ❌ Evitar

1. **Demasiadas Etapas**
   - Más de 5 confunde
   - Dificulta gestión
   - Reduce urgencia

2. **Cambios Sin Aviso**
   - Extender etapas sin anunciar
   - Cambiar precios radicalmente
   - Desactivar etapas antes de tiempo

3. **Descuentos Excesivos**
   - -50% devalúa el evento
   - Entrena a esperar ofertas
   - Reduce percepc ión de calidad

4. **Ignorar Métricas**
   - No monitorear ventas diarias
   - No reaccionar a tendencias
   - Mantener estrategia que no funciona

---

## 🛠️ Gestión Operativa

### Modificar Etapa Activa

Puede hacer ajustes en vivo:

1. **Extender Duración**
   ```
   Early Bird original: hasta 31/12
   Extendido: hasta 15/01
   ```
   ⚠️ Comunique el cambio

2. **Cambiar Modificador**
   ```
   De -20% a -25%
   ```
   ⚠️ Solo aplica para nuevas ventas

3. **Aumentar Límite**
   ```
   De 1,000 a 1,500 tickets
   ```

### Desactivar Etapa

Para pausar una etapa:

1. Vaya a la etapa
2. Cambie estado a **Inactiva**
3. El sistema vuelve a precios base o etapa anterior

### Clonar Etapa

Para reutilizar configuración:

1. Seleccione la etapa
2. Haga clic en **Duplicar**
3. Ajuste fechas y detalles
4. Guarde como nueva etapa

---

## ❓ Preguntas Frecuentes

### ¿Puedo tener múltiples etapas activas simultáneamente?

Sí, pero solo una aplica por venta. El sistema usa la de mayor prioridad.

### ¿Qué pasa si dos etapas tienen la misma prioridad?

El sistema usa la que tenga menor precio para el cliente.

### ¿Puedo cambiar etapas manualmente?

Sí, puede forzar el cambio desde el panel de control.

### ¿Se notifica a los clientes cuando suben los precios?

No automáticamente, pero puede configurar emails de aviso.

### ¿Puedo tener etapas diferentes por zona?

Sí, cada zona puede tener sus propias etapas independientes.

---

[← Anterior: Precios](04-precios.md) | [Volver al Índice](README.md) | [Siguiente: Ventas →](06-ventas.md)
