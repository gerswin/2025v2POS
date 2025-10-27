#!/usr/bin/env python
"""
Complete Spanish translations for Venezuelan POS System
"""

import re

def complete_spanish_translations():
    """Complete Spanish translations"""
    
    # Read the Spanish .po file
    po_file_path = 'locale/es/LC_MESSAGES/django.po'
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define translations that need to be completed
    translations_to_add = [
        ('msgid "Test Credentials"\\nmsgstr ""', 'msgid "Test Credentials"\\nmsgstr "Credenciales de Prueba"'),
        ('msgid "All rights reserved"\\nmsgstr ""', 'msgid "All rights reserved"\\nmsgstr "Todos los derechos reservados"'),
        ('msgid "Profile"\\nmsgstr ""', 'msgid "Profile"\\nmsgstr "Perfil"'),
        ('msgid "Settings"\\nmsgstr ""', 'msgid "Settings"\\nmsgstr "Configuración"'),
        ('msgid "Logout"\\nmsgstr ""', 'msgid "Logout"\\nmsgstr "Cerrar Sesión"'),
        ('msgid "Dashboard"\\nmsgstr ""', 'msgid "Dashboard"\\nmsgstr "Panel de Control"'),
        ('msgid "Venues"\\nmsgstr ""', 'msgid "Venues"\\nmsgstr "Venues"'),
        ('msgid "Events"\\nmsgstr ""', 'msgid "Events"\\nmsgstr "Eventos"'),
        ('msgid "Tickets"\\nmsgstr ""', 'msgid "Tickets"\\nmsgstr "Tickets"'),
        ('msgid "Reports"\\nmsgstr ""', 'msgid "Reports"\\nmsgstr "Reportes"'),
        ('msgid "Total Venues"\\nmsgstr ""', 'msgid "Total Venues"\\nmsgstr "Total de Venues"'),
        ('msgid "active"\\nmsgstr ""', 'msgid "active"\\nmsgstr "activos"'),
        ('msgid "Total Events"\\nmsgstr ""', 'msgid "Total Events"\\nmsgstr "Total de Eventos"'),
        ('msgid "Upcoming Events"\\nmsgstr ""', 'msgid "Upcoming Events"\\nmsgstr "Próximos Eventos"'),
        ('msgid "This month"\\nmsgstr ""', 'msgid "This month"\\nmsgstr "Este mes"'),
        ('msgid "Draft Events"\\nmsgstr ""', 'msgid "Draft Events"\\nmsgstr "Eventos Borrador"'),
        ('msgid "Pending"\\nmsgstr ""', 'msgid "Pending"\\nmsgstr "Pendientes"'),
        ('msgid "Recent Events"\\nmsgstr ""', 'msgid "Recent Events"\\nmsgstr "Eventos Recientes"'),
        ('msgid "View All"\\nmsgstr ""', 'msgid "View All"\\nmsgstr "Ver Todos"'),
        ('msgid "Event"\\nmsgstr ""', 'msgid "Event"\\nmsgstr "Evento"'),
        ('msgid "Venue"\\nmsgstr ""', 'msgid "Venue"\\nmsgstr "Venue"'),
        ('msgid "Date"\\nmsgstr ""', 'msgid "Date"\\nmsgstr "Fecha"'),
        ('msgid "Status"\\nmsgstr ""', 'msgid "Status"\\nmsgstr "Estado"'),
        ('msgid "Actions"\\nmsgstr ""', 'msgid "Actions"\\nmsgstr "Acciones"'),
        ('msgid "Active"\\nmsgstr ""', 'msgid "Active"\\nmsgstr "Activo"'),
        ('msgid "Draft"\\nmsgstr ""', 'msgid "Draft"\\nmsgstr "Borrador"'),
        ('msgid "Closed"\\nmsgstr ""', 'msgid "Closed"\\nmsgstr "Cerrado"'),
        ('msgid "Cancelled"\\nmsgstr ""', 'msgid "Cancelled"\\nmsgstr "Cancelado"'),
        ('msgid "No recent events"\\nmsgstr ""', 'msgid "No recent events"\\nmsgstr "No hay eventos recientes"'),
        ('msgid "Create First Event"\\nmsgstr ""', 'msgid "Create First Event"\\nmsgstr "Crear Primer Evento"'),
        ('msgid "Quick Actions"\\nmsgstr ""', 'msgid "Quick Actions"\\nmsgstr "Acciones Rápidas"'),
        ('msgid "Create Event"\\nmsgstr ""', 'msgid "Create Event"\\nmsgstr "Crear Evento"'),
        ('msgid "Add Venue"\\nmsgstr ""', 'msgid "Add Venue"\\nmsgstr "Agregar Venue"'),
        ('msgid "View Reports"\\nmsgstr ""', 'msgid "View Reports"\\nmsgstr "Ver Reportes"'),
        ('msgid "Map Editor"\\nmsgstr ""', 'msgid "Map Editor"\\nmsgstr "Editor de Mapas"'),
        ('msgid "Visually organize your event zones with our interactive map editor."\\nmsgstr ""', 'msgid "Visually organize your event zones with our interactive map editor."\\nmsgstr "Organiza visualmente las zonas de tus eventos con nuestro editor de mapas interactivo."'),
        ('msgid "Map"\\nmsgstr ""', 'msgid "Map"\\nmsgstr "Mapa"'),
        ('msgid "Create an event to use the map editor"\\nmsgstr ""', 'msgid "Create an event to use the map editor"\\nmsgstr "Crea un evento para usar el editor de mapas"'),
        ('msgid "Top Venues"\\nmsgstr ""', 'msgid "Top Venues"\\nmsgstr "Venues Principales"'),
        ('msgid "events"\\nmsgstr ""', 'msgid "events"\\nmsgstr "eventos"'),
        ('msgid "No venues registered"\\nmsgstr ""', 'msgid "No venues registered"\\nmsgstr "No hay venues registradas"'),
        ('msgid "Recent Activity"\\nmsgstr ""', 'msgid "Recent Activity"\\nmsgstr "Actividad Reciente"'),
        ('msgid "System initialized"\\nmsgstr ""', 'msgid "System initialized"\\nmsgstr "Sistema inicializado"'),
        ('msgid "Welcome to Venezuelan POS System"\\nmsgstr ""', 'msgid "Welcome to Venezuelan POS System"\\nmsgstr "Bienvenido al Sistema POS Venezolano"'),
        ('msgid "Today"\\nmsgstr ""', 'msgid "Today"\\nmsgstr "Hoy"'),
    ]
    
    # Apply translations
    updated_count = 0
    for pattern, replacement in translations_to_add:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            updated_count += 1
            print(f"✅ Updated translation")
    
    # Write back the updated content
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\\n📝 Updated {updated_count} Spanish translations")

def complete_english_translations():
    """Complete English translations (same as original text)"""
    
    # Read the English .po file
    po_file_path = 'locale/en/LC_MESSAGES/django.po'
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find empty msgstr entries and fill them with the msgid
    pattern = r'msgid "(.*?)"\\nmsgstr ""'
    
    def replace_empty_msgstr(match):
        msgid_text = match.group(1)
        return f'msgid "{msgid_text}"\\nmsgstr "{msgid_text}"'
    
    updated_content = re.sub(pattern, replace_empty_msgstr, content)
    
    # Count updates
    empty_count = len(re.findall(r'msgstr ""', content))
    
    # Write back the updated content
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"📝 Updated {empty_count} English translations")

def main():
    print("🌍 COMPLETING TRANSLATIONS")
    print("=" * 50)
    
    print("\\n--- Completing Spanish translations ---")
    complete_spanish_translations()
    
    print("\\n--- Completing English translations ---")
    complete_english_translations()
    
    print("\\n--- Compiling translations ---")
    import os
    os.system("python manage.py compilemessages")
    
    print("\\n✅ Translation completion finished!")

if __name__ == "__main__":
    main()