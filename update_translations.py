#!/usr/bin/env python
"""
Script to update all translations for the Venezuelan POS System
"""

import os
import re

def update_spanish_translations():
    """Update Spanish translations"""
    
    # Spanish translations mapping
    translations = {
        # Authentication
        '"Login"': '"Iniciar Sesión"',
        '"Venezuelan POS System"': '"Sistema POS Venezolano"',
        '"Event Management System"': '"Sistema de Gestión de Eventos"',
        '"Venue Management"': '"Gestión de Venues"',
        '"Event Administration"': '"Administración de Eventos"',
        '"Ticket Sales"': '"Venta de Tickets"',
        '"Reports and Analytics"': '"Reportes y Analytics"',
        '"Secure Multi-tenant"': '"Multi-tenant Seguro"',
        '"Access your administration panel"': '"Accede a tu panel de administración"',
        '"Username"': '"Usuario"',
        '"Password"': '"Contraseña"',
        '"Remember me"': '"Recordarme"',
        '"Test Credentials"': '"Credenciales de Prueba"',
        '"All rights reserved"': '"Todos los derechos reservados"',
        
        # Base template
        '"Profile"': '"Perfil"',
        '"Settings"': '"Configuración"',
        '"Logout"': '"Cerrar Sesión"',
        '"Dashboard"': '"Panel de Control"',
        '"Venues"': '"Venues"',
        '"Events"': '"Eventos"',
        '"Tickets"': '"Tickets"',
        '"Reports"': '"Reportes"',
        
        # Dashboard
        '"Venezuelan POS"': '"POS Venezolano"',
        '"Total Venues"': '"Total de Venues"',
        '"active"': '"activos"',
        '"Total Events"': '"Total de Eventos"',
        '"Upcoming Events"': '"Próximos Eventos"',
        '"This month"': '"Este mes"',
        '"Draft Events"': '"Eventos Borrador"',
        '"Pending"': '"Pendientes"',
        '"Recent Events"': '"Eventos Recientes"',
        '"View All"': '"Ver Todos"',
        '"Event"': '"Evento"',
        '"Venue"': '"Venue"',
        '"Date"': '"Fecha"',
        '"Status"': '"Estado"',
        '"Actions"': '"Acciones"',
        '"Active"': '"Activo"',
        '"Draft"': '"Borrador"',
        '"Closed"': '"Cerrado"',
        '"Cancelled"': '"Cancelado"',
        '"No recent events"': '"No hay eventos recientes"',
        '"Create First Event"': '"Crear Primer Evento"',
        '"Quick Actions"': '"Acciones Rápidas"',
        '"Create Event"': '"Crear Evento"',
        '"Add Venue"': '"Agregar Venue"',
        '"View Reports"': '"Ver Reportes"',
        '"Map Editor"': '"Editor de Mapas"',
        '"Visually organize your event zones with our interactive map editor."': '"Organiza visualmente las zonas de tus eventos con nuestro editor de mapas interactivo."',
        '"Map"': '"Mapa"',
        '"Create an event to use the map editor"': '"Crea un evento para usar el editor de mapas"',
        '"Top Venues"': '"Venues Principales"',
        '"events"': '"eventos"',
        '"No venues registered"': '"No hay venues registradas"',
        '"Recent Activity"': '"Actividad Reciente"',
        '"System initialized"': '"Sistema inicializado"',
        '"Welcome to Venezuelan POS System"': '"Bienvenido al Sistema POS Venezolano"',
        '"Today"': '"Hoy"',
    }
    
    # Read the Spanish .po file
    po_file_path = 'locale/es/LC_MESSAGES/django.po'
    
    if not os.path.exists(po_file_path):
        print(f"❌ File {po_file_path} not found")
        return
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update translations
    updated_count = 0
    for english, spanish in translations.items():
        # Pattern to match msgid and empty msgstr
        pattern = f'msgid {re.escape(english)}\\nmsgstr ""'
        replacement = f'msgid {english}\\nmsgstr {spanish}'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            updated_count += 1
            print(f"✅ Updated: {english} -> {spanish}")
    
    # Write back the updated content
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\\n📝 Updated {updated_count} translations in Spanish")

def update_english_translations():
    """Update English translations (keep original text)"""
    
    # Read the English .po file
    po_file_path = 'locale/en/LC_MESSAGES/django.po'
    
    if not os.path.exists(po_file_path):
        print(f"❌ File {po_file_path} not found")
        return
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find empty msgstr entries and fill them with the msgid
    pattern = r'msgid "(.*?)"\\nmsgstr ""'
    
    def replace_empty_msgstr(match):
        msgid_text = match.group(1)
        return f'msgid "{msgid_text}"\\nmsgstr "{msgid_text}"'
    
    updated_content = re.sub(pattern, replace_empty_msgstr, content)
    
    # Count updates
    updated_count = len(re.findall(r'msgstr ""', content))
    
    # Write back the updated content
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"📝 Updated {updated_count} translations in English")

def main():
    print("🌍 UPDATING TRANSLATIONS")
    print("=" * 50)
    
    print("\\n--- Updating Spanish translations ---")
    update_spanish_translations()
    
    print("\\n--- Updating English translations ---")
    update_english_translations()
    
    print("\\n--- Compiling translations ---")
    os.system("python manage.py compilemessages")
    
    print("\\n✅ Translation update completed!")
    print("\\n🌍 Available languages:")
    print("  - Español (es) - Spanish translations")
    print("  - English (en) - English translations")

if __name__ == "__main__":
    main()