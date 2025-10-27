#!/usr/bin/env python
"""
Script para limpiar duplicados en archivo .po
"""

def clean_po_file():
    """Limpiar duplicados en el archivo .po"""
    
    po_file_path = 'locale/es/LC_MESSAGES/django.po'
    
    # Leer archivo
    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Procesar líneas para eliminar duplicados
    seen_msgids = set()
    clean_lines = []
    skip_next = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if skip_next:
            skip_next = False
            i += 1
            continue
            
        if line.startswith('msgid '):
            msgid = line
            
            # Verificar si ya hemos visto este msgid
            if msgid in seen_msgids:
                # Saltar este msgid y su msgstr
                print(f"Eliminando duplicado: {msgid}")
                i += 1  # Saltar msgid
                while i < len(lines) and not lines[i].strip().startswith('msgstr '):
                    i += 1
                if i < len(lines):
                    i += 1  # Saltar msgstr
                # Saltar líneas vacías después
                while i < len(lines) and lines[i].strip() == '':
                    i += 1
                continue
            else:
                seen_msgids.add(msgid)
        
        clean_lines.append(lines[i])
        i += 1
    
    # Escribir archivo limpio
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.writelines(clean_lines)
    
    print(f"✅ Archivo {po_file_path} limpiado")

if __name__ == '__main__':
    clean_po_file()