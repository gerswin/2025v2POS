# 12. Troubleshooting y Preguntas Frecuentes

## Introducción

Esta guía le ayudará a resolver los problemas más comunes que puede encontrar al usar la plataforma. Si no encuentra la solución aquí, contacte a soporte técnico.

---

## 🔧 Problemas Comunes y Soluciones

### Problemas de Acceso

#### No puedo iniciar sesión

**Síntomas:**
- Mensaje de "Usuario o contraseña incorrectos"
- Página no carga después de login

**Soluciones:**

**1. Verifique sus credenciales:**
```
✓ Usuario o email correcto
✓ Contraseña sin espacios adicionales
✓ Mayúsculas/minúsculas correctas
✓ Teclado en idioma correcto
```

**2. ¿Olvidó su contraseña?**
```
1. Click en "Olvidé mi contraseña"
2. Ingrese su email
3. Revise su bandeja de entrada
4. Siga el enlace (válido 1 hora)
5. Cree nueva contraseña
```

**3. Cuenta bloqueada:**
```
Si intentó login 5 veces sin éxito:
├── Espere 30 minutos
├── O contacte a un administrador
└── O use "Olvidé mi contraseña"
```

**4. Limpie caché del navegador:**
```
Chrome/Edge:
Ctrl + Shift + Delete → Limpiar caché

Firefox:
Ctrl + Shift + Delete → Limpiar datos

Safari:
Cmd + Option + E → Vaciar caché
```

#### La sesión se cierra constantemente

**Causas posibles:**
- Timeout por inactividad (30 min)
- Cookies bloqueadas
- Navegador en modo incógnito

**Soluciones:**
```
1. Habilite cookies en su navegador
2. No use modo incógnito
3. Actualice su navegador
4. Contacte a admin para extender timeout
```

---

### Problemas con Ventas

#### No puedo completar una venta

**Error: "Asientos no disponibles"**
```
Causa: Asientos reservados por otro usuario

Solución:
1. Seleccione otros asientos
2. O espere 15 minutos (expiración automática)
3. O contacte al admin para liberar asientos
```

**Error: "Error procesando pago"**
```
Posibles causas:
├── Tarjeta rechazada
├── Fondos insuficientes
├── Problema con pasarela de pago
└── Timeout de conexión

Soluciones:
1. Verifique datos de tarjeta
2. Intente con otro método de pago
3. Verifique su conexión a internet
4. Contacte a su banco
```

**Error: "El evento ya no está disponible"**
```
Causa: Evento agotado o cerrado

Solución:
1. Verifique disponibilidad actual
2. Seleccione otra zona
3. Únase a lista de espera
```

#### El carrito se vacía solo

**Causa:**
- Timeout de reserva (15 minutos)
- Sesión expirada
- Asientos tomados por otro

**Solución:**
```
Prevención:
├── Complete compra rápidamente
├── No deje la página inactiva
└── Use "Guardar para después"

Si sucede:
├── Vuelva a agregar al carrito
└── Complete pago inmediatamente
```

---

### Problemas con Tickets

#### No recibí mis tickets por email

**Verificar primero:**
```
1. Revise carpeta de spam/correo no deseado
2. Verifique que el pago se procesó
3. Confirme email correcto en el pedido
4. Espere 5 minutos (procesamiento)
```

**Si aún no aparecen:**
```
1. Acceda a su cuenta en la plataforma
2. Vaya a "Mis Tickets"
3. Descargue directamente
4. O use "Reenviar tickets por email"
5. O contacte a soporte con # de transacción
```

#### El código QR no escanea

**Problemas comunes:**
```
Calidad de impresión baja:
└─ Imprima nuevamente en mayor calidad

Pantalla del móvil sucia/dañada:
└─ Limpie la pantalla

Brillo muy bajo:
└─ Aumente el brillo al máximo

Ticket muy pequeño en pantalla:
└─ Amplíe el QR (zoom)
```

**Solución alternativa:**
```
1. Muestre el número de ticket
2. Personal puede buscar manualmente
3. Verificar con documento de identidad
4. O use código de barras de respaldo
```

#### Dice "Ticket ya usado" pero no he entrado

**Posibles causas:**
```
1. Ticket duplicado/fraudulento
2. Error del sistema
3. Alguien más usó su ticket
```

**Solución inmediata:**
```
1. Llame al supervisor de puerta
2. Muestre su confirmación de compra
3. Presente identificación
4. Verificación manual en sistema
5. Se le otorgará acceso si es legítimo
```

---

### Problemas con Pagos

#### Mi pago fue rechazado

**Tarjeta de Crédito rechazada:**
```
Razones comunes:
├── Fondos insuficientes
├── Límite de crédito alcanzado
├── Restricción geográfica
├── Tarjeta vencida
├── Datos incorrectos
└── Bloqueo por seguridad bancaria

Soluciones:
1. Verifique saldo/límite
2. Contacte a su banco
3. Verifique fecha de vencimiento
4. Verifique CVV correcto
5. Intente con otra tarjeta
```

**Transferencia no se refleja:**
```
1. Los pagos por transferencia requieren
   confirmación manual

2. Envíe comprobante a:
   ├── Email de soporte
   ├── Con # de referencia
   └── Foto clara del comprobante

3. Procesamiento: 1-4 horas hábiles

4. Recibirá confirmación por email
```

#### No puedo hacer un plan de pago

**Error: "Plan de pago no disponible"**
```
Causas:
├── Evento muy próximo (<7 días)
├── Precio muy bajo
├── Función deshabilitada para este evento
└── Cupo de planes agotado

Solución:
└── Pague el total o seleccione otro evento
```

**Error: "Pago inicial insuficiente"**
```
Causa: Monto menor al mínimo requerido

Solución:
1. Verifique monto mínimo (ej: 20%)
2. Aumente el pago inicial
3. O reduzca cantidad de tickets
```

---

### Problemas con el Sistema

#### La página carga muy lento

**Optimizaciones:**
```
1. Limpie caché del navegador
2. Cierre pestañas innecesarias
3. Desactive extensiones
4. Verifique su conexión a internet
5. Intente en otro navegador
6. Evite horarios pico (inicio de ventas)
```

**Verifique velocidad de internet:**
```
Mínimo recomendado: 5 Mbps
Ideal: 10+ Mbps

Test de velocidad:
└── speedtest.net
```

#### Veo errores 404 o 500

**Error 404 - Página no encontrada:**
```
Causas:
├── URL incorrecta
├── Página eliminada
└── Link desactualizado

Solución:
1. Verifique la URL
2. Regrese al inicio
3. Use el menú de navegación
4. Reporte el link roto a soporte
```

**Error 500 - Error del servidor:**
```
Causas:
├── Problema temporal del servidor
├── Mantenimiento programado
└── Alto tráfico

Solución:
1. Espere 5 minutos
2. Recargue la página (F5)
3. Intente más tarde
4. Si persiste, contacte a soporte
```

#### No veo las imágenes

**Soluciones:**
```
1. Verifique su conexión a internet
2. Desactive bloqueadores de anuncios
3. Habilite JavaScript
4. Limpie caché del navegador
5. Actualice la página (Ctrl+F5)
```

---

### Problemas con Reportes

#### Los reportes no muestran datos

**Verifique filtros:**
```
Común: Filtros muy restrictivos

Solución:
1. Amplíe rango de fechas
2. Seleccione "Todos" en filtros
3. Reinicie filtros a valores por defecto
```

#### No puedo exportar reportes

**Formatos bloqueados:**
```
Causa: Bloqueador de pop-ups activo

Solución:
1. Permita pop-ups para este sitio
2. O descargue desde notificaciones
3. O use click derecho → "Guardar como"
```

---

## ❓ Preguntas Frecuentes Generales

### Ventas y Tickets

**¿Hasta cuándo puedo comprar tickets?**
```
Ventas cierran:
├── 2 horas antes del evento (default)
├── Cuando se agoten
└── O según configuración del organizador
```

**¿Puedo cambiar mis tickets?**
```
Depende de la política del evento:

Cambio de asiento:
├── Sujeto a disponibilidad
├── Puede haber diferencia de precio
└── Contacte a organizador

Cambio de fecha:
└── Solo si hay función alternativa
```

**¿Puedo cancelar mi compra?**
```
Política estándar de reembolso:
├── >60 días antes: 100% reembolso
├── 30-60 días:     75% reembolso
├── 15-30 días:     50% reembolso
├── 7-15 días:      25% reembolso
└── <7 días:        No reembolso

Nota: Varía según evento
```

**¿Los tickets son transferibles?**
```
Depende de configuración del evento:

Si es transferible:
├── Requiere solicitud
├── Verificación de identidad
└── Proceso toma 24-48 horas

Si no es transferible:
└── Solo válido para comprador original
```

**¿Necesito imprimir mis tickets?**
```
No necesariamente:

Opciones válidas:
✓ Mostrar en móvil (PDF o Wallet)
✓ Imprimir en casa
✓ Screenshot del QR
✓ Cualquier formato donde el QR sea visible
```

**¿Qué documento necesito presentar?**
```
En la entrada:
✓ Ticket (digital o impreso)
✓ Documento de identidad válido
✓ Que coincida con nombre de compra
```

### Pagos

**¿Qué métodos de pago aceptan?**
```
Típicamente:
✓ Tarjetas de crédito/débito
✓ Transferencia bancaria
✓ Pago móvil
✓ Efectivo (puntos autorizados)
✓ PayPal (si está habilitado)
```

**¿Es seguro pagar con tarjeta?**
```
Sí, completamente seguro:
✓ Encriptación SSL/TLS
✓ Certificación PCI-DSS
✓ No guardamos datos completos
✓ Procesadores certificados (Stripe)
✓ Protección antifraude
```

**¿Cuándo se cobra mi tarjeta?**
```
Inmediatamente:
├── Al completar la compra
└── Aparece en su estado de cuenta

En planes de pago:
├── Primera cuota: Inmediato
├── Siguientes cuotas: Según calendario
└── Notificación 3 días antes
```

**¿Recibo factura?**
```
Sí:
✓ Factura digital por email
✓ Incluye todos los detalles
✓ Válida para contabilidad
✓ Puede solicitar factura fiscal
```

### Planes de Pago

**¿Qué pasa si no pago una cuota a tiempo?**
```
Proceso escalonado:
├── Día 0:   Recordatorio amistoso
├── Día +1:  Alerta de vencimiento
├── Día +3:  Recargo por mora (si aplica)
├── Día +7:  Advertencia de cancelación
└── Día +10: Cancelación automática
```

**¿Puedo pagar todo antes de tiempo?**
```
Sí:
✓ Puede saldar en cualquier momento
✓ Sin penalización
✓ Tickets se emiten inmediatamente
✓ Puede haber descuento por pronto pago
```

**¿Qué pasa si cancelo un plan de pago?**
```
Reembolso según cuánto haya pagado:
├── Se aplica política de reembolso estándar
├── Sobre el monto ya pagado
├── Procesa en 7-10 días hábiles
└── Tickets/asientos se liberan
```

### Eventos

**¿Puedo comprar para menores de edad?**
```
Depende del evento:
├── Eventos familiares: Sí
├── Eventos para adultos: No
├── Algunos requieren acompañante
└── Verificar restricción en descripción
```

**¿Qué pasa si el evento se cancela?**
```
En caso de cancelación:
✓ Notificación inmediata por email
✓ 100% de reembolso automático
✓ Procesa en 7-10 días hábiles
✓ O válido para evento reprogramado
```

**¿Qué pasa si llego tarde?**
```
Política común:
├── Acceso permitido hasta 30 min después
├── Solo en pausas/intermedios
├── Puede perderse inicio
└── Varía según evento
```

**¿Puedo entrar y salir del evento?**
```
Depende de configuración:
├── Mayoría: No permite reentrada
├── Algunos eventos VIP: Sí
├── Con validación especial
└── Verificar política en ticket
```

### Cuenta de Usuario

**¿Necesito crear una cuenta?**
```
No obligatorio:
├── Puede comprar como invitado
├── Pero cuenta tiene beneficios:
│   ✓ Historial de compras
│   ✓ Reenvío fácil de tickets
│   ✓ Ofertas exclusivas
│   └─ Proceso más rápido
```

**¿Cómo cambio mi contraseña?**
```
1. Login → Mi Cuenta
2. Sección "Seguridad"
3. "Cambiar Contraseña"
4. Ingrese contraseña actual
5. Ingrese nueva contraseña
6. Confirme nueva contraseña
7. Guarde cambios
```

**¿Cómo actualizo mis datos?**
```
1. Login → Mi Cuenta
2. Sección "Información Personal"
3. Edite los campos necesarios
4. Guarde cambios
5. Confirme por email (si cambió email)
```

**¿Puedo eliminar mi cuenta?**
```
Sí, pero considere:
├── Se pierden tickets futuros
├── Se pierde historial
├── Proceso irreversible

Para eliminar:
1. Contacte a soporte
2. Confirme identidad
3. Procesa en 30 días
4. Datos se anonimizan
```

---

## 🆘 Cuándo Contactar a Soporte

### Contacte a soporte si:

```
✓ Pagó pero no recibió confirmación (después de 1 hora)
✓ Error al escanear ticket válido
✓ Problemas técnicos persistentes
✓ Necesita modificar una compra
✓ Sospecha de fraude
✓ No puede acceder a su cuenta
✓ Requiere factura fiscal
✓ Preguntas sobre reembolsos
```

### Información a tener lista:

```
Cuando contacte a soporte, tenga:
├── Número de transacción
├── Email de compra
├── Capturas de pantalla del error
├── Navegador y versión
├── Descripción clara del problema
└── Pasos para reproducir el error
```

---

## 📞 Canales de Soporte

### Email
```
soporte@plataforma.com
├── Respuesta: 24-48 horas
├── Para: Consultas generales
└── Incluya toda la información necesaria
```

### Teléfono
```
+58 212-555-1234
├── Lunes a Viernes: 9:00 AM - 6:00 PM
├── Sábados: 10:00 AM - 2:00 PM
└── Para: Urgencias y soporte inmediato
```

### WhatsApp
```
+58 414-555-1234
├── Disponible 24/7 (respuesta en horario laboral)
├── Para: Consultas rápidas
└── Envíe capturas y detalles
```

### Chat en Vivo
```
Disponible en la plataforma
├── Lunes a Viernes: 9:00 AM - 8:00 PM
├── Sábados: 10:00 AM - 4:00 PM
└── Para: Soporte en tiempo real
```

---

## 🔍 Diagnóstico Rápido

### Checklist antes de reportar un problema:

```
☐ Reinicié el navegador
☐ Limpié caché y cookies
☐ Probé en modo incógnito
☐ Probé en otro navegador
☐ Verifiqué mi conexión a internet
☐ Revisé que no esté en mantenimiento
☐ Tomé capturas del error
☐ Anoté pasos para reproducir
☐ Verifiqué preguntas frecuentes
☐ Preparé información de contacto
```

---

## 💡 Tips para Mejor Experiencia

### Navegadores Recomendados

```
✓ Google Chrome (versión más reciente)
✓ Mozilla Firefox (versión más reciente)
✓ Microsoft Edge (versión más reciente)
✓ Safari (macOS/iOS más reciente)

Evitar:
✗ Internet Explorer
✗ Versiones antiguas de navegadores
```

### Configuración Óptima

```
Habilite:
✓ JavaScript
✓ Cookies
✓ Pop-ups (para este sitio)
✓ Notificaciones (opcional)

Desactive temporalmente:
✗ Bloqueadores de anuncios
✗ VPN (si causa problemas)
✗ Extensiones conflictivas
```

### Compras Exitosas

```
Mejores prácticas:
✓ Compre con tiempo antes del evento
✓ Tenga datos de pago listos
✓ Use conexión estable
✓ Complete compra en una sesión
✓ Guarde confirmación inmediatamente
✓ Descargue tickets apenas los reciba
✓ Llegue temprano al evento
```

---

## 📱 Compatibilidad Móvil

### Aplicaciones

**Navegadores móviles compatibles:**
```
iOS:
✓ Safari
✓ Chrome
✓ Firefox

Android:
✓ Chrome
✓ Firefox
✓ Samsung Internet
```

**Wallets compatibles:**
```
✓ Apple Wallet (iOS)
✓ Google Wallet (Android)
✓ Samsung Pay
```

### Problemas comunes móviles:

**Ticket no se ve bien en móvil:**
```
Solución:
1. Gire pantalla (horizontal)
2. Amplíe con zoom
3. Descargue PDF
4. Agregue a Wallet
```

**No puedo agregar a Wallet:**
```
Solución:
1. Actualice sistema operativo
2. Verifique espacio disponible
3. Use archivo .pkpass (iOS)
4. Descargue directamente del email
```

---

## 🎯 Solución Rápida por Síntoma

### "No puedo..."

```
...iniciar sesión
└─→ Ver "Problemas de Acceso" arriba

...completar el pago
└─→ Ver "Problemas con Pagos" arriba

...ver mis tickets
└─→ Revise email/spam o descargue desde cuenta

...escanear el QR
└─→ Ver "El código QR no escanea" arriba

...cambiar mi compra
└─→ Contacte a soporte con # transacción

...encontrar mi confirmación
└─→ Busque email o acceda a "Mis Compras"
```

### "¿Por qué...?"

```
...no recibí confirmación?
└─→ Espere 5 min, revise spam, verifique email

...se cerró mi sesión?
└─→ Timeout 30 min o cookies bloqueadas

...desapareció mi carrito?
└─→ Timeout 15 min o asientos tomados

...dice ticket inválido?
└─→ Ya usado, duplicado, o evento pasado

...no puedo hacer plan de pago?
└─→ Evento muy próximo o monto muy bajo
```

### "Aparece error..."

```
..."Asientos no disponibles"
└─→ Reservados o vendidos, seleccione otros

..."Pago rechazado"
└─→ Verifique datos/fondos o use otro método

..."Sesión expirada"
└─→ Inicie sesión nuevamente

..."Error 404"
└─→ URL incorrecta, use menú de navegación

..."Error 500"
└─→ Problema temporal, espere e intente después
```

---

## 📚 Recursos Adicionales

### Documentación

```
Manual de Usuario Completo:
└─→ Este documento

Guías Rápidas:
├─→ Cómo comprar tickets
├─→ Cómo usar planes de pago
└─→ Cómo descargar tickets

Videos Tutoriales:
└─→ [URL de canal de YouTube]
```

### Actualizaciones

```
Siga nuestras actualizaciones:
├─→ Blog de la plataforma
├─→ Redes sociales
└─→ Newsletter mensual
```

---

## ✅ Checklist Final

### Antes del Evento

```
☐ Tickets descargados
☐ Guardados en móvil y email
☐ Agregados a Wallet (opcional)
☐ Impreso respaldo (opcional)
☐ Documento de identidad
☐ Dirección del venue anotada
☐ Hora de llegada planificada
☐ Política del evento revisada
```

### Si Algo Sale Mal

```
☐ Mantenga la calma
☐ Revise esta guía primero
☐ Intente soluciones básicas
☐ Contacte a soporte si persiste
☐ Tenga información lista
☐ Sea específico en su consulta
```

---

**¿No encontró lo que buscaba?**

Contáctenos:
- 📧 Email: soporte@plataforma.com
- 📞 Teléfono: +58 212-555-1234
- 💬 WhatsApp: +58 414-555-1234
- 🌐 Chat en vivo: www.plataforma.com

**Horario de Atención:**
- Lunes a Viernes: 9:00 AM - 6:00 PM
- Sábados: 10:00 AM - 2:00 PM
- Emergencias 24/7: WhatsApp

---

[← Anterior: Administración](11-administracion.md) | [Volver al Índice](README.md)
