#!/usr/bin/env python
"""
Script para agregar las traducciones faltantes
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

def add_missing_translations():
    """Agregar traducciones faltantes al archivo .po"""
    
    # Traducciones faltantes
    missing_translations = {
        'Sales': 'Ventas',
        'Customers': 'Clientes', 
        'Cancel': 'Cancelar',
        'Edit': 'Editar',
        'Create': 'Crear',
        'Price': 'Precio',
        'Quantity': 'Cantidad',
        'Available': 'Disponible',
        'Reserved': 'Reservado',
        'Sold': 'Vendido',
        'Settings': 'Configuración',
        'Recent Events': 'Eventos Recientes',
        'Quick Actions': 'Acciones Rápidas',
        'Map Editor': 'Editor de Mapas',
        'Venues': 'Locales',
        'Profile': 'Perfil',
    }
    
    po_file_path = 'locale/es/LC_MESSAGES/django.po'
    
    # Leer archivo actual
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Agregar traducciones faltantes
    additions = []
    for english, spanish in missing_translations.items():
        # Verificar si ya existe la traducción
        if f'msgid "{english}"' not in content:
            additions.append(f'\\nmsgid "{english}"\\nmsgstr "{spanish}"\\n')
        else:
            # Verificar si está vacía y actualizarla
            import re
            pattern = f'msgid "{re.escape(english)}"\\s*\\nmsgstr ""'
            if re.search(pattern, content):
                content = re.sub(pattern, f'msgid "{english}"\\nmsgstr "{spanish}"', content)
                print(f"✅ Actualizada traducción: {english} -> {spanish}")
    
    # Agregar nuevas traducciones al final
    if additions:
        content += '\\n'.join(additions)
        print(f"✅ Agregadas {len(additions)} nuevas traducciones")
    
    # Escribir archivo actualizado
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Archivo {po_file_path} actualizado")

if __name__ == '__main__':
    print("🔧 AGREGANDO TRADUCCIONES FALTANTES")
    print("=" * 50)
    
    add_missing_translations()
    
    print("\\n🚀 Compilando mensajes...")
    os.system("python manage.py compilemessages")
    
    print("\\n✅ Traducciones actualizadas y compiladas")