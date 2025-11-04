#!/usr/bin/env python3
"""
Script para generar PDF del Manual de Usuario
"""
import os
from pathlib import Path
import markdown
from weasyprint import HTML, CSS
from datetime import datetime

# Orden de los capítulos
CHAPTERS = [
    'README.md',
    '01-introduccion.md',
    '02-lugares.md',
    '03-eventos.md',
    '04-precios.md',
    '05-etapas-precios.md',
    '06-ventas.md',
    '07-pagos-parciales.md',
    '08-clientes.md',
    '09-reportes.md',
    '10-tickets-digitales.md',
    '11-administracion.md',
    '12-troubleshooting.md',
]

# CSS para el PDF
PDF_CSS = """
@page {
    size: letter;
    margin: 2cm 1.5cm;

    @top-center {
        content: "Manual de Usuario - Sistema de Gestión de Eventos";
        font-size: 9pt;
        color: #666;
        font-family: Arial, sans-serif;
    }

    @bottom-right {
        content: "Página " counter(page);
        font-size: 9pt;
        color: #666;
        font-family: Arial, sans-serif;
    }
}

@page :first {
    @top-center { content: none; }
    @bottom-right { content: none; }
}

body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #333;
}

h1 {
    color: #0066CC;
    font-size: 24pt;
    margin-top: 20pt;
    margin-bottom: 12pt;
    page-break-before: always;
    border-bottom: 2px solid #0066CC;
    padding-bottom: 8pt;
}

h1:first-of-type {
    page-break-before: avoid;
}

h2 {
    color: #0066CC;
    font-size: 18pt;
    margin-top: 16pt;
    margin-bottom: 10pt;
    border-bottom: 1px solid #ccc;
    padding-bottom: 4pt;
}

h3 {
    color: #333;
    font-size: 14pt;
    margin-top: 12pt;
    margin-bottom: 8pt;
}

h4 {
    color: #666;
    font-size: 12pt;
    margin-top: 10pt;
    margin-bottom: 6pt;
}

p {
    margin-bottom: 8pt;
    text-align: justify;
}

code {
    background-color: #f4f4f4;
    padding: 2pt 4pt;
    border-radius: 3pt;
    font-family: "Courier New", monospace;
    font-size: 9pt;
}

pre {
    background-color: #f4f4f4;
    padding: 10pt;
    border-left: 3pt solid #0066CC;
    border-radius: 3pt;
    overflow-x: auto;
    font-family: "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.4;
    margin: 10pt 0;
}

pre code {
    background-color: transparent;
    padding: 0;
}

ul, ol {
    margin-left: 20pt;
    margin-bottom: 10pt;
}

li {
    margin-bottom: 4pt;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
}

th {
    background-color: #0066CC;
    color: white;
    padding: 8pt;
    text-align: left;
    font-weight: bold;
}

td {
    border: 1px solid #ddd;
    padding: 8pt;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

blockquote {
    border-left: 4pt solid #0066CC;
    padding-left: 12pt;
    margin-left: 0;
    color: #666;
    font-style: italic;
}

a {
    color: #0066CC;
    text-decoration: none;
}

.page-break {
    page-break-before: always;
}

.cover {
    text-align: center;
    padding-top: 100pt;
}

.cover h1 {
    font-size: 32pt;
    color: #0066CC;
    margin-bottom: 20pt;
    border: none;
    page-break-before: avoid;
}

.cover h2 {
    font-size: 18pt;
    color: #666;
    border: none;
    margin-bottom: 40pt;
}

.cover .info {
    font-size: 12pt;
    color: #999;
    margin-top: 60pt;
}

hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 20pt 0;
}
"""

def read_markdown_file(filepath):
    """Lee un archivo markdown y retorna su contenido"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def generate_cover_page():
    """Genera la página de portada"""
    today = datetime.now().strftime("%d de %B de %Y")

    return f"""
<div class="cover">
    <h1>Manual de Usuario</h1>
    <h2>Sistema de Gestión de Eventos y Venta de Tickets</h2>

    <div style="margin-top: 80pt;">
        <p style="font-size: 14pt; color: #666;">
            Guía Completa para Usuarios Finales
        </p>
    </div>

    <div class="info">
        <p>Versión 1.0</p>
        <p>{today}</p>
    </div>
</div>
"""

def generate_toc(chapters_content):
    """Genera tabla de contenidos"""
    toc = """
<div class="page-break">
    <h1>Tabla de Contenidos</h1>
    <ul style="list-style: none; line-height: 2;">
"""

    chapter_titles = [
        "Índice General",
        "1. Introducción",
        "2. Gestión de Lugares (Venues)",
        "3. Eventos",
        "4. Precios",
        "5. Etapas de Precios",
        "6. Ventas",
        "7. Pagos Parciales y Planes de Pago",
        "8. Gestión de Clientes",
        "9. Reportes y Análisis",
        "10. Tickets Digitales",
        "11. Administración del Sistema",
        "12. Troubleshooting y Preguntas Frecuentes"
    ]

    for i, title in enumerate(chapter_titles):
        if i == 0:
            continue  # Skip README in TOC
        toc += f'        <li style="margin-bottom: 8pt;"><strong>{title}</strong></li>\n'

    toc += """    </ul>
</div>
"""
    return toc

def main():
    """Función principal"""
    print("Generando Manual en PDF...")
    print("=" * 50)

    # Directorio base
    base_dir = Path(__file__).parent

    # Combinar todo el contenido
    full_html = ""

    # Agregar portada
    print("✓ Generando portada...")
    full_html += generate_cover_page()

    # Procesar cada capítulo
    chapters_content = []
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables', 'fenced_code'])

    for chapter in CHAPTERS:
        filepath = base_dir / chapter
        if filepath.exists():
            print(f"✓ Procesando: {chapter}")
            content = read_markdown_file(filepath)

            # Convertir a HTML
            html_content = md.convert(content)
            md.reset()  # Reset para el siguiente archivo

            chapters_content.append(html_content)
        else:
            print(f"✗ Advertencia: No se encontró {chapter}")

    # Agregar tabla de contenidos
    print("✓ Generando tabla de contenidos...")
    full_html += generate_toc(chapters_content)

    # Agregar todos los capítulos
    for i, content in enumerate(chapters_content):
        if i > 0:  # Skip README content
            full_html += '<div class="page-break"></div>'
        full_html += content

    # Crear HTML completo
    complete_html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manual de Usuario - Sistema de Gestión de Eventos</title>
</head>
<body>
    {full_html}
</body>
</html>
"""

    # Generar PDF
    output_file = base_dir / "Manual_Usuario_Sistema_Eventos.pdf"
    print(f"\n✓ Generando PDF: {output_file}")

    try:
        HTML(string=complete_html).write_pdf(
            output_file,
            stylesheets=[CSS(string=PDF_CSS)]
        )

        file_size = output_file.stat().st_size / (1024 * 1024)  # MB
        print(f"\n{'=' * 50}")
        print(f"✓ PDF generado exitosamente!")
        print(f"  Archivo: {output_file}")
        print(f"  Tamaño: {file_size:.2f} MB")
        print(f"{'=' * 50}")

    except Exception as e:
        print(f"\n✗ Error generando PDF: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
