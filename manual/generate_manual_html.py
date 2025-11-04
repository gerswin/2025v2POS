#!/usr/bin/env python3
"""
Script para generar HTML del Manual de Usuario que puede ser impreso a PDF
desde cualquier navegador
"""
import os
from pathlib import Path
import markdown2
from datetime import datetime

# Orden de los capítulos
CHAPTERS = [
    ('README.md', 'Índice General'),
    ('01-introduccion.md', '1. Introducción'),
    ('02-lugares.md', '2. Gestión de Lugares (Venues)'),
    ('03-eventos.md', '3. Eventos'),
    ('04-precios.md', '4. Precios'),
    ('05-etapas-precios.md', '5. Etapas de Precios'),
    ('06-ventas.md', '6. Ventas'),
    ('07-pagos-parciales.md', '7. Pagos Parciales y Planes de Pago'),
    ('08-clientes.md', '8. Gestión de Clientes'),
    ('09-reportes.md', '9. Reportes y Análisis'),
    ('10-tickets-digitales.md', '10. Tickets Digitales'),
    ('11-administracion.md', '11. Administración del Sistema'),
    ('12-troubleshooting.md', '12. Troubleshooting y Preguntas Frecuentes'),
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manual de Usuario - Sistema de Gestión de Eventos</title>
    <style>
        @media print {{
            @page {{
                size: letter;
                margin: 2cm 1.5cm;
            }}

            .no-print {{
                display: none;
            }}

            h1 {{
                page-break-before: always;
            }}

            h1:first-of-type {{
                page-break-before: avoid;
            }}

            .cover {{
                page-break-after: always;
            }}

            pre, code {{
                page-break-inside: avoid;
            }}

            img {{
                max-width: 100%;
                page-break-inside: avoid;
            }}

            table {{
                page-break-inside: avoid;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 0;
        }}

        .container {{
            max-width: 8.5in;
            margin: 0 auto;
            background: white;
            padding: 1in;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}

        /* Portada */
        .cover {{
            text-align: center;
            padding: 100px 0;
            min-height: 11in;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}

        .cover h1 {{
            font-size: 36pt;
            color: #0066CC;
            margin-bottom: 30px;
            border: none;
        }}

        .cover h2 {{
            font-size: 20pt;
            color: #666;
            margin-bottom: 60px;
            font-weight: normal;
            border: none;
        }}

        .cover .subtitle {{
            font-size: 16pt;
            color: #666;
            margin: 40px 0;
        }}

        .cover .info {{
            font-size: 12pt;
            color: #999;
            margin-top: 80px;
        }}

        /* Botón de impresión */
        .print-button {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #0066CC;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 5px;
            font-size: 14pt;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
        }}

        .print-button:hover {{
            background: #0052A3;
        }}

        /* Tipografía */
        h1 {{
            color: #0066CC;
            font-size: 28pt;
            margin: 40px 0 20px 0;
            border-bottom: 3px solid #0066CC;
            padding-bottom: 10px;
        }}

        h2 {{
            color: #0066CC;
            font-size: 20pt;
            margin: 30px 0 15px 0;
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
        }}

        h3 {{
            color: #333;
            font-size: 16pt;
            margin: 25px 0 12px 0;
        }}

        h4 {{
            color: #666;
            font-size: 14pt;
            margin: 20px 0 10px 0;
        }}

        p {{
            margin-bottom: 12px;
            text-align: justify;
        }}

        /* Listas */
        ul, ol {{
            margin-left: 30px;
            margin-bottom: 15px;
        }}

        li {{
            margin-bottom: 8px;
        }}

        /* Código */
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 10pt;
            color: #c7254e;
        }}

        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-left: 4px solid #0066CC;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }}

        pre code {{
            background: none;
            padding: 0;
            color: #333;
            font-size: 10pt;
        }}

        /* Tablas */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            border: 1px solid #ddd;
        }}

        th {{
            background-color: #0066CC;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}

        td {{
            border: 1px solid #ddd;
            padding: 10px;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        /* Blockquotes */
        blockquote {{
            border-left: 4px solid #0066CC;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
        }}

        /* Enlaces */
        a {{
            color: #0066CC;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        /* Separadores */
        hr {{
            border: none;
            border-top: 2px solid #eee;
            margin: 30px 0;
        }}

        /* Tabla de contenidos */
        .toc {{
            background: #f9f9f9;
            padding: 30px;
            border-radius: 8px;
            margin: 30px 0;
        }}

        .toc h2 {{
            margin-top: 0;
            border: none;
        }}

        .toc ul {{
            list-style: none;
            margin-left: 0;
        }}

        .toc li {{
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}

        .toc li:last-child {{
            border-bottom: none;
        }}

        .toc a {{
            font-size: 12pt;
            display: block;
        }}

        /* Capítulos */
        .chapter {{
            margin-top: 50px;
        }}

        .chapter:first-of-type {{
            margin-top: 0;
        }}

        /* Instrucciones de impresión */
        .instructions {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}

        .instructions h3 {{
            color: #856404;
            margin-top: 0;
        }}

        .instructions p {{
            color: #856404;
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">🖨️ Imprimir a PDF</button>

    <div class="container">
        <!-- Portada -->
        <div class="cover">
            <h1>Manual de Usuario</h1>
            <h2>Sistema de Gestión de Eventos<br>y Venta de Tickets</h2>

            <div class="subtitle">
                <p>Guía Completa para Usuarios Finales</p>
            </div>

            <div class="info">
                <p><strong>Versión 1.0</strong></p>
                <p>{date}</p>
            </div>
        </div>

        <!-- Instrucciones de impresión -->
        <div class="instructions no-print">
            <h3>📄 Cómo generar el PDF</h3>
            <p><strong>Opción 1: Usar el botón de arriba</strong></p>
            <ol>
                <li>Haz clic en el botón "🖨️ Imprimir a PDF" en la esquina superior derecha</li>
                <li>Selecciona tu impresora o "Guardar como PDF"</li>
                <li>Configura la orientación en "Vertical"</li>
                <li>Guarda el archivo</li>
            </ol>

            <p><strong>Opción 2: Menú del navegador</strong></p>
            <ul>
                <li><strong>Windows/Linux:</strong> Ctrl + P</li>
                <li><strong>Mac:</strong> Cmd + P</li>
            </ul>
            <p>Luego selecciona "Guardar como PDF" como destino.</p>
        </div>

        <!-- Tabla de contenidos -->
        <div class="toc">
            <h2>📑 Tabla de Contenidos</h2>
            <ul>
{toc}
            </ul>
        </div>

        <!-- Contenido de los capítulos -->
{content}
    </div>

    <script>
        // Función para suavizar el scroll
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth' }});
                }}
            }});
        }});
    </script>
</body>
</html>
"""

def read_markdown_file(filepath):
    """Lee un archivo markdown y retorna su contenido"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def create_anchor(text):
    """Crea un ancla URL-safe desde un texto"""
    return text.lower().replace(' ', '-').replace('.', '').replace('(', '').replace(')', '')

def main():
    """Función principal"""
    print("Generando Manual en HTML...")
    print("=" * 50)

    # Directorio base
    base_dir = Path(__file__).parent

    # Generar tabla de contenidos
    toc_html = ""
    for filename, title in CHAPTERS:
        if filename != 'README.md':  # Skip README in TOC
            anchor = create_anchor(title)
            toc_html += f'                <li><a href="#{anchor}">{title}</a></li>\n'

    # Procesar cada capítulo
    content_html = ""
    extras = ['fenced-code-blocks', 'tables', 'break-on-newline', 'cuddled-lists']

    for i, (filename, title) in enumerate(CHAPTERS):
        filepath = base_dir / filename

        if filepath.exists():
            print(f"✓ Procesando: {filename}")

            # Leer contenido markdown
            md_content = read_markdown_file(filepath)

            # Convertir a HTML
            html_content = markdown2.markdown(md_content, extras=extras)

            # Agregar el contenido con título de capítulo
            if filename != 'README.md':
                anchor = create_anchor(title)
                content_html += f'\n        <div class="chapter" id="{anchor}">\n'
                content_html += f'            <h1>{title}</h1>\n'
                content_html += html_content
                content_html += '\n        </div>\n'
            else:
                content_html += html_content

        else:
            print(f"✗ Advertencia: No se encontró {filename}")

    # Crear HTML completo
    today = datetime.now().strftime("%d de %B de %Y")
    complete_html = HTML_TEMPLATE.format(
        date=today,
        toc=toc_html,
        content=content_html
    )

    # Guardar HTML
    output_file = base_dir / "Manual_Usuario_Sistema_Eventos.html"
    print(f"\n✓ Generando HTML: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(complete_html)

    file_size = output_file.stat().st_size / 1024  # KB

    print(f"\n{'=' * 50}")
    print(f"✓ HTML generado exitosamente!")
    print(f"  Archivo: {output_file}")
    print(f"  Tamaño: {file_size:.2f} KB")
    print(f"\n📄 INSTRUCCIONES:")
    print(f"  1. Abre el archivo en tu navegador")
    print(f"  2. Haz clic en 'Imprimir a PDF' o Ctrl/Cmd + P")
    print(f"  3. Selecciona 'Guardar como PDF'")
    print(f"  4. ¡Listo!")
    print(f"{'=' * 50}")

    return 0

if __name__ == "__main__":
    exit(main())
