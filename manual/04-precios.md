# 4. Sistema de Precios

## Introducción

El sistema de precios de Tiquemax POS es flexible y potente, permitiéndole configurar precios diferentes por zona, por fila, y precios que cambian automáticamente basándose en el tiempo o la disponibilidad.

---

## 🎯 Tipos de Precios

### 1. Precios por Zona 🏷️

Cada zona del venue puede tener un precio base diferente:

```
Platea VIP:     $150.00
Platea General: $100.00
Balcón:         $ 75.00
Terrazas:       $ 50.00
```

**Cuándo usar**:
- Diferentes niveles de experiencia
- Visibilidad variable
- Comodidades distintas

### 2. Precios por Fila 📊

Dentro de una zona numerada, cada fila puede tener precio distinto:

```
PLATEA VIP
├── Filas A-C: $200.00 (Mejores asientos)
├── Filas D-F: $175.00
└── Filas G-J: $150.00
```

**Cuándo usar**:
- Teatros con diferente visual

idad por fila
- Zonas VIP con niveles premium
- Optimizar ingresos por ubicación

### 3. Precios Dinámicos ⚡

Los precios cambian automáticamente según:

#### Por Tiempo (Etapas)
```
Early Bird:    $100 (60 días antes)
Regular:       $150 (30 días antes)
Last Minute:   $200 (última semana)
```

#### Por Disponibilidad
```
100% - 75% disponible: $100
74% - 50% disponible:  $125
49% - 25% disponible:  $150
24% - 0% disponible:   $200
```

---

## ✅ Configurar Precios Base por Zona

### Paso 1: Acceder al Módulo

1. Vaya a **Precios** en el menú principal
2. Seleccione el **Venue** correspondiente
3. Haga clic en **Configurar Precios Base**

### Paso 2: Definir Precios

Para cada zona configurada:

**Zona: Platea VIP**
```
Precio Base: $150.00
Moneda: USD
```

**Zona: Platea General**
```
Precio Base: $100.00
Moneda: USD
```

💡 **Consejo**: Establezca precios "regulares" como base. Los early bird y last minute se configuran como etapas.

### Paso 3: Guardar Configuración

1. Revise todos los precios
2. Haga clic en **Guardar Precios Base**
3. El sistema confirmará los cambios

---

## 🎭 Configurar Precios por Fila

Para zonas numeradas con precios diferenciados por ubicación:

### Paso 1: Acceder a la Zona

1. Vaya a **Precios** → Seleccione el venue
2. Haga clic en la zona numerada (ej: "Platea VIP")
3. Haga clic en **Precios por Fila**

### Paso 2: Definir Grupos de Filas

**Grupo 1: Filas Premium**
```
Filas: A, B, C
Precio: $200.00
Nombre: Premium Front
```

**Grupo 2: Filas VIP**
```
Filas: D, E, F, G
Precio: $175.00
Nombre: VIP Central
```

**Grupo 3: Filas Estándar**
```
Filas: H, I, J
Precio: $150.00
Nombre: VIP Regular
```

### Paso 3: Vista Previa

El sistema muestra el mapa con colores:

```
PLATEA VIP - MAPA DE PRECIOS
════════════════════════════════════
         ESCENARIO
════════════════════════════════════

Fila A: [🟥][🟥][🟥]... $200 Premium
Fila B: [🟥][🟥][🟥]... $200 Premium
Fila C: [🟥][🟥][🟥]... $200 Premium
Fila D: [🟦][🟦][🟦]... $175 VIP
Fila E: [🟦][🟦][🟦]... $175 VIP
Fila F: [🟦][🟦][🟦]... $175 VIP
Fila G: [🟦][🟦][🟦]... $175 VIP
Fila H: [🟩][🟩][🟩]... $150 Regular
Fila I: [🟩][🟩][🟩]... $150 Regular
Fila J: [🟩][🟩][🟩]... $150 Regular

🟥 $200  🟦 $175  🟩 $150
```

### Paso 4: Aplicar Precios

1. Revise la configuración
2. Haga clic en **Aplicar Precios por Fila**
3. Confirme los cambios

---

## 🔄 Sistema Híbrido

El sistema **híbrido** combina lo mejor de ambos mundos:

### ¿Qué es el Sistema Híbrido?

```
Sistema Híbrido = Precios Base + Etapas + Triggers
```

**Ejemplo Práctico**:
```
Platea VIP
├── Precio Base por Fila:
│   ├── Filas A-C: $150
│   └── Filas D-J: $120
│
├── Modificador de Etapa (Early Bird): -20%
│   ├── Filas A-C: $120 ($150 - 20%)
│   └── Filas D-J: $96  ($120 - 20%)
│
└── Trigger de Disponibilidad (75% vendido): +15%
    ├── Filas A-C: $138 ($120 + 15%)
    └── Filas D-J: $110 ($96 + 15%)
```

### Orden de Aplicación

1. **Precio Base** (por zona o por fila)
2. **Modificador de Etapa** (descuento/incremento %)
3. **Trigger de Disponibilidad** (incremento adicional)

### Configurar Sistema Híbrido

1. Configure **precios base** (por zona o fila)
2. Cree **etapas de precios** (capítulo 5)
3. Active **triggers de disponibilidad**

---

## 📈 Triggers de Disponibilidad

Los triggers aumentan los precios automáticamente cuando quedan pocos asientos.

### Configurar Triggers

1. Vaya a **Precios** → **Triggers**
2. Haga clic en **+ Nuevo Trigger**

**Nombre del Trigger**
```
Ejemplo: Incremento 75%
```

**Umbral de Disponibilidad**
```
Cuando queda: 75% vendido
(25% disponible)
```

**Incremento**
```
Aumentar: 15%
```

**Zonas Aplicables**
```
☑ Platea VIP
☑ Platea General
☐ Terrazas (excluida)
```

### Ejemplo de Múltiples Triggers

```
┌─────────────────────────────────────────────┐
│ CONFIGURACIÓN DE TRIGGERS                   │
├─────────────────────────────────────────────┤
│                                              │
│ 50% vendido → +10%                          │
│ 75% vendido → +15%                          │
│ 90% vendido → +25%                          │
│                                              │
│ Precio inicial VIP: $100                    │
│                                              │
│ Al 50%: $110 ($100 + 10%)                   │
│ Al 75%: $125 ($110 + 15% adicional)         │
│ Al 90%: $156 ($125 + 25% adicional)         │
│                                              │
└─────────────────────────────────────────────┘
```

⚠️ **Los triggers son acumulativos**

### Desactivar Triggers

Puede pausar temporalmente:

1. Vaya a **Precios** → **Triggers**
2. Seleccione el trigger
3. Cambie el estado a **Inactivo**

---

## 💰 Cálculo de Precios

### Ejemplo Completo

**Configuración**:
```
Venue: Teatro Nacional
Zona: Platea VIP
Fila: A (Front Row)

Precio Base por Fila: $150.00
Etapa Activa: Early Bird (-20%)
Trigger 75%: +15%
Disponibilidad: 80% vendido (trigger activo)
```

**Cálculo**:
```
1. Precio Base:           $150.00
2. Early Bird (-20%):     $150 × 0.80 = $120.00
3. Trigger 75% (+15%):    $120 × 1.15 = $138.00

Precio Final: $138.00
```

### Fórmula General

```
Precio Final = Precio Base × (1 + % Etapa) × (1 + % Triggers)
```

💡 Los porcentajes negativos (descuentos) usan valores < 1:
- -20% = × 0.80
- +15% = × 1.15

---

## 🎨 Visualización de Precios

### Mapa de Calor

El sistema genera un mapa visual:

```
TEATRO NACIONAL - HEATMAP DE PRECIOS
═══════════════════════════════════════

         [ESCENARIO]

Platea VIP
▓▓▓▓▓▓  $200 (más caro)
▓▓▓▓▒▒  $175
▒▒▒▒░░  $150
░░░░░░  $125 (más barato)

Leyenda:
▓ $200  ▓ $175  ▒ $150  ░ $125
```

### Dashboard de Precios

Ver en tiempo real:

```
┌─────────────────────────────────────┐
│ MONITOR DE PRECIOS EN VIVO          │
├─────────────────────────────────────┤
│                                      │
│ Etapa Activa: Early Bird            │
│ Vigencia: 15 días restantes          │
│                                      │
│ Triggers Activos:                   │
│ ☑ 75% vendido (+15%)                │
│   └ Zonas afectadas: VIP, General   │
│                                      │
│ Próximo Cambio:                     │
│ Etapa Regular en 15 días            │
│ Precios suben aprox. 25%            │
│                                      │
└─────────────────────────────────────┘
```

---

## 🛠️ Gestión de Precios Activos

### Modificar Precios Durante Venta

⚠️ **Con precaución**: Cambios afectan solo ventas futuras

**Lo que puede hacer**:
1. Cambiar a una nueva etapa
2. Ajustar triggers
3. Crear promociones temporales

**Lo que NO debe hacer**:
1. Reducir precios sin comunicar
2. Cambios drásticos sin aviso
3. Modificar precios 48h antes del evento

### Promociones Temporales

Para descuentos especiales:

1. Vaya a **Precios** → **Promociones**
2. Haga clic en **+ Nueva Promoción**

**Nombre**
```
Ejemplo: Flash Sale Viernes
```

**Tipo**
```
Opciones:
- Descuento Porcentual: 25% off
- Descuento Fijo: $20 menos
- Precio Especial: $99 fijo
```

**Vigencia**
```
Desde: 01/12/2024 00:00
Hasta: 01/12/2024 23:59
```

**Límite**
```
Primeros: 50 tickets
```

---

## 📊 Estrategias de Precios

### Estrategia 1: Early Bird Agresivo

**Objetivo**: Ventas tempranas masivas

```
60+ días: -30% (Early Bird Super)
45-59 días: -20% (Early Bird)
30-44 días: -10% (Pre-venta)
0-29 días: Precio Regular
Última semana: +20%
```

**Ventajas**:
- Cash flow temprano
- Reducir riesgo
- Crear urgencia

**Desventajas**:
- Menor ingreso por ticket
- Depende de marketing anticipado

### Estrategia 2: Precios Escalonados Conservadores

**Objetivo**: Maximizar ingresos

```
60+ días: Precio Base
30-59 días: +10%
15-29 días: +20%
0-14 días: +30%
```

**Ventajas**:
- Mayores ingresos
- No devalúa el evento

**Desventajas**:
- Ventas más lentas
- Mayor riesgo de no llenar

### Estrategia 3: Dinámica por Demanda

**Objetivo**: Precio óptimo siempre

```
Baja demanda (0-40% vendido):
  → Mantener precios o descontar

Media demanda (40-70% vendido):
  → Precios regulares

Alta demanda (70-100% vendido):
  → Incrementos agresivos (+25% por trigger)
```

**Ventajas**:
- Adaptable al mercado
- Maximiza cada momento

**Desventajas**:
- Requiere monitoreo constante
- Puede confundir a clientes

### Estrategia 4: Last Minute Deals

**Objetivo**: Llenar espacios vacíos

```
7+ días: Precios regulares
48h-7 días: -15% (Last Minute)
Último día: -30% (Ultra Last Minute)
```

**Ventajas**:
- Vender inventario muerto
- Atraer compradores impulsivos

**Desventajas**:
- Canibaliza ventas tempranas
- Crea expectativa de descuentos

---

## 💡 Mejores Prácticas

### ✅ Recomendaciones

1. **Simplicidad**
   - No más de 4-5 etapas
   - Diferencias claras entre niveles
   - Fácil de explicar

2. **Transparencia**
   - Muestre cuándo suben los precios
   - Sea claro sobre triggers
   - Justifique incrementos

3. **Testing**
   - Pruebe estrategias en eventos pequeños
   - Compare resultados
   - Ajuste según aprenda

4. **Comunicación**
   - Anuncie cambios de etapa
   - Cree urgencia ("Suben en 3 días")
   - Use countdowns

5. **Análisis**
   - Monitoree qué funciona
   - Compare con eventos similares
   - Documente lecciones aprendidas

### ❌ Errores Comunes

1. **Demasiadas Etapas**
   - Confunden al cliente
   - Dificultan gestión
   - Generan quejas

2. **Triggers Muy Agresivos**
   - Precio final muy alto
   - Clientes esperan descuentos
   - Percepción negativa

3. **No Comunicar Cambios**
   - Sorpresas desagradables
   - Quejas en redes sociales
   - Pérdida de confianza

4. **Precios Inconsistentes**
   - Platea barata más cara que VIP
   - Descuentos que no tienen sentido
   - Falta de lógica

---

## 📝 Ejemplo Práctico Completo

### Caso: Concierto Gran Artista

**Venue**: Estadio Nacional (20,000 personas)

**Zonas y Precios Base**:
```
Pista: $250 (5,000 personas)
Gradas Bajas: $180 (8,000 personas)
Gradas Altas: $120 (7,000 personas)
```

**Etapas de Precios**:
```
1. Super Early (90+ días): -30%
   └ Pista $175, Bajas $126, Altas $84

2. Early Bird (60-89 días): -20%
   └ Pista $200, Bajas $144, Altas $96

3. Pre-venta (30-59 días): -10%
   └ Pista $225, Bajas $162, Altas $108

4. Regular (0-29 días): Precio Base
   └ Pista $250, Bajas $180, Altas $120

5. Last Week (última semana): +20%
   └ Pista $300, Bajas $216, Altas $144
```

**Triggers**:
```
70% vendido: +10%
85% vendido: +15%
95% vendido: +25%
```

**Resultado**:
- 12,000 tickets vendidos en Super Early/Early
- 5,000 tickets en Pre-venta
- 2,500 tickets Regular
- 500 tickets Last Week con trigger 95%

**Ingresos**:
```
Super Early: 8,000 × $125 prom = $1,000,000
Early Bird: 4,000 × $150 prom = $600,000
Pre-venta: 5,000 × $175 prom = $875,000
Regular: 2,500 × $200 prom = $500,000
Last Week: 500 × $300 prom = $150,000

Total: $3,125,000
```

---

## ❓ Preguntas Frecuentes

### ¿Los precios incluyen IVA?

Depende de su configuración. Puede mostrar precios con o sin IVA. Recomendamos incluirlo para evitar sorpresas.

### ¿Puedo tener precios diferentes por método de pago?

Sí, puede agregar recargos por método (ej: +3% con tarjeta de crédito).

### ¿Qué pasa si un cliente compró barato y ahora están más caros?

El cliente pagó el precio vigente en su momento. Los nuevos compradores pagan el precio actual.

### ¿Puedo cambiar de estrategia a mitad de evento?

Sí, pero comuníquelo claramente. Los clientes que ya compraron mantienen su precio.

### ¿Los triggers se desactivan si bajo de ese umbral?

No, los triggers solo se activan cuando se alcanza el umbral, no se revierten si bajan las ventas.

---

[← Anterior: Eventos](03-eventos.md) | [Volver al Índice](README.md) | [Siguiente: Etapas de Precios →](05-etapas-precios.md)
