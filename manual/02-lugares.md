# 2. Gestión de Lugares (Venues)

## Introducción

Los **lugares** o **venues** son los espacios físicos donde se realizan los eventos. Antes de crear un evento, debe configurar el lugar con todas sus zonas y asientos.

---

## 📍 ¿Qué es un Lugar?

Un lugar es la representación digital de un espacio físico como:
- Teatros
- Estadios
- Arenas
- Centros de convenciones
- Salas de conciertos
- Espacios al aire libre

Cada lugar contiene:
- **Información básica**: Nombre, dirección, capacidad
- **Zonas**: Áreas diferenciadas (VIP, General, Palcos)
- **Asientos**: Butacas numeradas o entrada general
- **Mapa visual**: Representación gráfica del espacio

---

## ✅ Crear un Nuevo Lugar

### Paso 1: Acceder al Módulo

1. En el menú principal, haga clic en **Lugares**
2. Verá la lista de lugares existentes
3. Haga clic en el botón **+ Nuevo Lugar**

### Paso 2: Información Básica

Complete los siguientes campos:

#### Campos Obligatorios ✅

**Nombre del Lugar**
```
Ejemplo: Teatro Nacional
```
- Use un nombre descriptivo y único
- Evite caracteres especiales
- Máximo 100 caracteres

**Dirección**
```
Ejemplo: Av. Principal, Centro Comercial Plaza, Piso 3
```
- Dirección completa y clara
- Incluya puntos de referencia si es necesario

**Ciudad**
```
Ejemplo: Caracas
```

**Capacidad Total**
```
Ejemplo: 500
```
- Número máximo de personas que puede albergar
- Incluye todas las zonas

#### Campos Opcionales

**Descripción**
```
Ejemplo: Teatro moderno con excelente acústica y visibilidad
desde todos los asientos. Cuenta con aire acondicionado y
facilidades para personas con movilidad reducida.
```

**Teléfono de Contacto**
```
Ejemplo: +58 212-555-1234
```

**Email del Venue**
```
Ejemplo: info@teatronacional.com
```

**Sitio Web**
```
Ejemplo: https://www.teatronacional.com
```

### Paso 3: Guardar

1. Revise toda la información
2. Haga clic en **Guardar**
3. El sistema confirmará la creación

⚠️ **Importante**: No puede eliminar un lugar que tenga eventos asociados.

---

## 🎨 Configurar Zonas

Las **zonas** son las áreas diferenciadas de su venue. Cada zona puede tener:
- Tipo diferente (Numerada o General)
- Capacidad propia
- Precios diferentes
- Color en el mapa

### Tipos de Zonas

#### 1. Zona Numerada 🪑
- Cada asiento tiene un número específico
- Los clientes seleccionan asientos individuales
- Ideal para: Teatros, cines, auditorios

**Ejemplo**: Platea, Palcos, Balcón

#### 2. Zona de Entrada General 👥
- Sin asientos asignados
- Se vende por cantidad
- Ideal para: Conciertos, eventos de pie

**Ejemplo**: Pista, Zona de Pie, Terrazas

### Crear una Zona

1. Desde la lista de lugares, haga clic en el nombre del venue
2. Vaya a la pestaña **Zonas**
3. Haga clic en **+ Nueva Zona**

#### Configuración de Zona Numerada

**Nombre de la Zona**
```
Ejemplo: Platea VIP
```

**Tipo**
- Seleccione: **Numerada**

**Capacidad**
```
Ejemplo: 200 asientos
```

**Número de Filas**
```
Ejemplo: 10 filas
```

**Asientos por Fila**
```
Ejemplo: 20 asientos por fila
```

**Formato de Numeración**
```
Opciones:
- Fila [A-Z] + Número [1-N]: A1, A2, B1, B2...
- Fila [1-N] + Letra [A-Z]: 1A, 1B, 2A, 2B...
- Número Consecutivo: 001, 002, 003...
```

**Color en el Mapa**
- Seleccione un color que distinga esta zona
```
Recomendación:
- VIP: Dorado (#FFD700)
- Premium: Azul (#0066CC)
- General: Verde (#00CC66)
```

#### Configuración de Zona General

**Nombre de la Zona**
```
Ejemplo: Pista General
```

**Tipo**
- Seleccione: **General**

**Capacidad**
```
Ejemplo: 500 personas
```

**Color en el Mapa**
- Seleccione un color identificador

### Ejemplo Completo: Teatro

```
TEATRO NACIONAL
Capacidad Total: 800 personas

Zonas:
├── Platea VIP (Numerada)
│   ├── Filas: A-J (10 filas)
│   ├── Asientos por fila: 20
│   ├── Capacidad: 200
│   └── Color: Dorado
│
├── Platea General (Numerada)
│   ├── Filas: K-T (10 filas)
│   ├── Asientos por fila: 30
│   ├── Capacidad: 300
│   └── Color: Azul
│
├── Balcón (Numerada)
│   ├── Filas: 1-5
│   ├── Asientos por fila: 40
│   ├── Capacidad: 200
│   └── Color: Verde
│
└── Terrazas (General)
    ├── Sin asientos asignados
    ├── Capacidad: 100
    └── Color: Gris
```

---

## 🪑 Gestión de Asientos Numerados

### Ver Mapa de Asientos

1. Vaya a **Lugares** → Seleccione el venue
2. Seleccione la zona numerada
3. Haga clic en **Ver Mapa de Asientos**

Verá una representación visual como:

```
PLATEA VIP
════════════════════════════════════
    ESCENARIO
════════════════════════════════════

Fila A: [A1][A2][A3][A4][A5]...[A20]
Fila B: [B1][B2][B3][B4][B5]...[B20]
Fila C: [C1][C2][C3][C4][C5]...[C20]
...
Fila J: [J1][J2][J3][J4][J5]...[J20]

Leyenda:
🟦 Disponible
🟨 Reservado
🟥 Vendido
⬜ Bloqueado
```

### Bloquear Asientos

Puede bloquear asientos que no estén disponibles para venta:

1. En el mapa de asientos, haga clic en **Gestionar Asientos**
2. Seleccione los asientos a bloquear
3. Haga clic en **Bloquear Seleccionados**
4. Indique el motivo:
   ```
   Ejemplos:
   - Asiento dañado
   - Visibilidad obstruida
   - Reservado para producción
   - Uso técnico
   ```

### Desbloquear Asientos

1. Vaya al mapa de asientos
2. Haga clic en **Ver Bloqueados**
3. Seleccione los asientos a liberar
4. Haga clic en **Desbloquear**

---

## 👥 Gestión de Entrada General

### Configurar Capacidad

Para zonas de entrada general:

**Capacidad Máxima**
- Número total de tickets disponibles
```
Ejemplo: 500 personas
```

**Límite por Transacción**
- Máximo de tickets por compra
```
Recomendado: 10 tickets
```

**Advertencia de Capacidad**
- Notificar cuando queden pocos tickets
```
Ejemplo: Alertar al 90% de ocupación
```

### Control de Sobreventa

⚠️ **El sistema previene automáticamente la sobreventa**

- Verifica disponibilidad en tiempo real
- Bloquea temporalmente durante la compra
- Libera si no se completa la transacción

---

## 🗺️ Editor de Mapas (Avanzado)

### Personalizar Diseño

Para venues complejos, puede usar el editor visual:

1. Vaya a **Lugares** → Seleccione venue
2. Haga clic en **Editor de Mapa**
3. Use las herramientas de diseño:

**Herramientas Disponibles:**
- ➕ Agregar zona
- ✏️ Editar forma
- 🎨 Cambiar color
- 📐 Ajustar tamaño
- 🔄 Rotar
- 📝 Etiquetar

### Plantillas Predefinidas

Seleccione una plantilla base:

```
📋 Plantillas Disponibles:

🎭 Teatro Tradicional
   - Platea
   - Balcón
   - Palcos laterales

🏟️ Estadio
   - Gradas numeradas
   - Zonas VIP
   - Palcos

🎪 Arena Circular
   - Pista central
   - Gradas 360°
   - Zonas premium

🎵 Sala de Conciertos
   - Pista (entrada general)
   - Gradas laterales
   - Zona VIP elevada
```

---

## 📊 Reportes de Lugares

### Información Útil

Desde la vista del venue puede ver:

**Estadísticas Generales**
- Total de zonas configuradas
- Capacidad total
- Eventos realizados
- Tasa de ocupación promedio

**Por Zona**
- Asientos totales
- Asientos vendidos
- Asientos disponibles
- Asientos bloqueados
- Revenue generado

---

## 💡 Mejores Prácticas

### ✅ Recomendaciones

1. **Nombres Claros**
   - Use nombres descriptivos
   - Evite abreviaciones confusas
   - Sea consistente

2. **Colores Distintivos**
   - Use colores que contrasten
   - Mantenga jerarquía visual (VIP más llamativo)
   - Use el mismo código de colores en todos sus venues

3. **Capacidades Realistas**
   - Configure la capacidad real del espacio
   - Considere regulaciones de seguridad
   - Deje margen para áreas técnicas

4. **Documentación**
   - Mantenga planos del venue actualizados
   - Documente asientos bloqueados y motivos
   - Registre cambios en la configuración

### ❌ Errores Comunes

1. **Sobrestimar Capacidad**
   - Problema: Vender más tickets de los permitidos
   - Solución: Verificar aforo legal

2. **Numeración Inconsistente**
   - Problema: Confusión en el ingreso
   - Solución: Usar sistemas estándar de numeración

3. **No Bloquear Asientos Problemáticos**
   - Problema: Vender asientos con mala visibilidad
   - Solución: Bloquear antes de publicar evento

---

## 🔧 Mantenimiento de Lugares

### Actualizar Información

Puede actualizar la información en cualquier momento:

1. Vaya a **Lugares**
2. Haga clic en el nombre del venue
3. Haga clic en **Editar**
4. Modifique los campos necesarios
5. Haga clic en **Guardar**

⚠️ **Advertencia**: Cambios en la configuración de zonas afectan eventos futuros, no eventos activos.

### Duplicar Venue

Para crear un venue similar:

1. Seleccione el venue a duplicar
2. Haga clic en **Acciones** → **Duplicar**
3. Modifique el nombre y detalles específicos
4. Guarde el nuevo venue

---

## 🎯 Checklist de Configuración

Antes de crear un evento, verifique:

```
☐ Información básica completa
☐ Dirección correcta
☐ Todas las zonas creadas
☐ Asientos numerados configurados
☐ Capacidades correctas
☐ Asientos problemáticos bloqueados
☐ Colores asignados a cada zona
☐ Mapa visual revisado
☐ Prueba de visualización en ventas
```

---

## 📝 Ejemplo Práctico Completo

### Caso: Teatro Municipal

**Información Básica:**
- Nombre: Teatro Municipal de Caracas
- Dirección: Av. Lecuna, Parroquia Catedral
- Ciudad: Caracas
- Capacidad: 850 personas

**Zonas:**

1. **Platea Alta (Numerada)**
   - Filas: A-F (6 filas)
   - Asientos: 25 por fila
   - Total: 150 asientos
   - Color: #FFD700 (Dorado)

2. **Platea Baja (Numerada)**
   - Filas: G-P (10 filas)
   - Asientos: 30 por fila
   - Total: 300 asientos
   - Color: #4169E1 (Azul Real)

3. **Balcón Derecho (Numerada)**
   - Filas: 1-8
   - Asientos: 20 por fila
   - Total: 160 asientos
   - Color: #32CD32 (Verde)

4. **Balcón Izquierdo (Numerada)**
   - Filas: 1-8
   - Asientos: 20 por fila
   - Total: 160 asientos
   - Color: #32CD32 (Verde)

5. **Tertulia (General)**
   - Entrada general de pie
   - Total: 80 personas
   - Color: #A9A9A9 (Gris)

**Asientos Bloqueados:**
- A1, A25 (columnas)
- F15-F17 (cabina técnica)
- P28-P30 (salida de emergencia)

---

## ❓ Preguntas Frecuentes

### ¿Puedo cambiar la numeración después de crear las zonas?

Sí, pero solo si no hay eventos activos con ventas. El sistema le advertirá si hay conflictos.

### ¿Cuántos lugares puedo crear?

No hay límite en la cantidad de venues que puede configurar.

### ¿Puedo tener el mismo venue con diferentes configuraciones?

Sí. Puede crear variaciones del mismo espacio físico con diferentes configuraciones de zonas.

### ¿Qué pasa si vendo más tickets de la capacidad?

El sistema previene automáticamente la sobreventa. No podrá vender más allá de la capacidad configurada.

### ¿Puedo importar la configuración de otro lugar?

Sí, use la función "Duplicar" y modifique según necesite.

---

[← Anterior: Introducción](01-introduccion.md) | [Volver al Índice](README.md) | [Siguiente: Eventos →](03-eventos.md)
