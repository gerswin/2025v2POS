# Cómo Generar el PDF del Manual

## 📄 Método Recomendado (Desde el Navegador)

El archivo `Manual_Usuario_Sistema_Eventos.html` ya está listo para ser convertido a PDF.

### Pasos:

1. **Abrir el HTML**
   - El archivo ya debería estar abierto en tu navegador
   - Si no, haz doble clic en `Manual_Usuario_Sistema_Eventos.html`

2. **Imprimir a PDF**

   **En macOS:**
   - Presiona `Cmd + P` (⌘P)
   - O haz clic en el botón azul "🖨️ Imprimir a PDF" en la esquina superior derecha
   - En el diálogo de impresión, selecciona "Guardar como PDF"
   - Guarda el archivo donde desees

   **En Windows:**
   - Presiona `Ctrl + P`
   - En "Destino", selecciona "Guardar como PDF"
   - Haz clic en "Guardar"

   **En Linux:**
   - Presiona `Ctrl + P`
   - Selecciona "Imprimir en archivo" o "Print to File"
   - Formato: PDF
   - Guarda el archivo

3. **Configuración Recomendada**
   - Orientación: Vertical (Portrait)
   - Márgenes: Predeterminados
   - Tamaño: Carta/Letter (8.5" x 11")
   - Escala: 100%
   - Incluir fondos: Sí (para mejor apariencia)

## 📋 Resultado

El PDF generado incluirá:
- ✅ Portada profesional con fecha actual
- ✅ Tabla de contenidos interactiva
- ✅ 12 capítulos completos
- ✅ Formato profesional con colores y estilos
- ✅ Código y ejemplos bien formateados
- ✅ Aproximadamente 100-150 páginas

## 🔄 Regenerar el HTML

Si necesitas actualizar el manual después de modificar los archivos markdown:

```bash
cd manual
python generate_manual_html.py
```

Esto regenerará el archivo HTML con los cambios más recientes.

## 🛠️ Método Alternativo (Línea de Comandos)

Si prefieres generar el PDF directamente desde la terminal (requiere instalar herramientas adicionales):

### Opción 1: Usando Chrome/Chromium (headless)

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless \
  --disable-gpu \
  --print-to-pdf="Manual_Usuario.pdf" \
  Manual_Usuario_Sistema_Eventos.html

# Linux
google-chrome \
  --headless \
  --disable-gpu \
  --print-to-pdf="Manual_Usuario.pdf" \
  Manual_Usuario_Sistema_Eventos.html

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --headless ^
  --disable-gpu ^
  --print-to-pdf="Manual_Usuario.pdf" ^
  Manual_Usuario_Sistema_Eventos.html
```

### Opción 2: Usando wkhtmltopdf

Primero instala wkhtmltopdf:

```bash
# macOS
brew install wkhtmltopdf

# Ubuntu/Debian
sudo apt-get install wkhtmltopdf

# Windows
# Descarga desde: https://wkhtmltopdf.org/downloads.html
```

Luego genera el PDF:

```bash
wkhtmltopdf \
  --page-size Letter \
  --margin-top 20mm \
  --margin-bottom 20mm \
  --margin-left 15mm \
  --margin-right 15mm \
  Manual_Usuario_Sistema_Eventos.html \
  Manual_Usuario.pdf
```

## 📁 Archivos Incluidos

- `README.md` - Índice principal del manual
- `01-introduccion.md` a `12-troubleshooting.md` - Capítulos individuales
- `generate_manual_html.py` - Script para generar el HTML
- `Manual_Usuario_Sistema_Eventos.html` - HTML listo para imprimir
- `COMO_GENERAR_PDF.md` - Este archivo

## ❓ Preguntas Frecuentes

### El PDF se ve diferente al HTML

Esto es normal. Los navegadores pueden renderizar de forma ligeramente diferente al imprimir. Si encuentras problemas:
1. Intenta con otro navegador (Chrome suele dar mejores resultados)
2. Ajusta la escala de impresión (prueba 90% o 95%)
3. Verifica que "Imprimir fondos" esté habilitado

### El PDF es muy grande

El archivo HTML incluye todo el contenido del manual. Si necesitas un PDF más pequeño:
1. Imprime solo las páginas que necesitas
2. Usa compresión PDF (hay herramientas online gratuitas)
3. Reduce la calidad de impresión si tu navegador lo permite

### Necesito actualizar el contenido

1. Edita los archivos `.md` que necesites
2. Ejecuta `python generate_manual_html.py`
3. Regenera el PDF desde el HTML actualizado

## 📞 Soporte

Si tienes problemas generando el PDF, contacta al equipo de desarrollo o abre un issue en el repositorio del proyecto.
