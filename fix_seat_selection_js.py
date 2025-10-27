#!/usr/bin/env python
"""
Script para corregir el JavaScript roto en seat_selection.html
"""

import os
import re

def fix_seat_selection_js():
    """Corregir el JavaScript roto en seat_selection.html"""
    
    print("🔧 CORRIGIENDO JAVASCRIPT EN SEAT_SELECTION.HTML")
    print("=" * 60)
    
    file_path = "venezuelan_pos/apps/sales/templates/sales/seat_selection.html"
    
    try:
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ Archivo leído correctamente")
        
        # Buscar la línea problemática
        if "textContent = '" in content and "</content>" in content:
            print("❌ Encontrado JavaScript corrupto")
            
            # Corregir la línea específica
            # Buscar el patrón problemático y reemplazarlo
            pattern = r"document\.getElementById\('cartTotal'\)\.textContent = '[^']*</content>[^']*\+ parseFloat\(data\.cart_total\)\.toFixed\(2\);"
            replacement = "document.getElementById('cartTotal').textContent = '$' + parseFloat(data.cart_total).toFixed(2);"
            
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            # También limpiar cualquier tag de issues
            content = re.sub(r'<issues>.*?</issues>', '', content, flags=re.DOTALL)
            
            # Escribir el archivo corregido
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ JavaScript corregido")
            
            # Verificar que la corrección funcionó
            with open(file_path, 'r', encoding='utf-8') as f:
                new_content = f.read()
            
            if "textContent = '$'" in new_content and "</content>" not in new_content:
                print("✅ Corrección verificada")
                return True
            else:
                print("❌ La corrección no funcionó completamente")
                return False
        
        else:
            print("✅ No se encontraron problemas en el JavaScript")
            return True
            
    except Exception as e:
        print(f"❌ Error al procesar el archivo: {e}")
        return False

def verify_fix():
    """Verificar que el fix funcionó"""
    
    print("\\n🔍 VERIFICANDO FIX:")
    print("-" * 30)
    
    file_path = "venezuelan_pos/apps/sales/templates/sales/seat_selection.html"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que no hay tags corruptos
        if "</content>" in content:
            print("❌ Todavía hay tags corruptos")
            return False
        
        # Verificar que la línea está correcta
        if "textContent = '$' + parseFloat(data.cart_total).toFixed(2);" in content:
            print("✅ Línea de JavaScript corregida")
        else:
            print("❌ Línea de JavaScript no encontrada")
            return False
        
        # Verificar que no hay issues tags
        if "<issues>" in content:
            print("❌ Todavía hay tags de issues")
            return False
        
        print("✅ Archivo completamente limpio")
        return True
        
    except Exception as e:
        print(f"❌ Error al verificar: {e}")
        return False

if __name__ == '__main__':
    success = fix_seat_selection_js()
    
    if success:
        verify_success = verify_fix()
        
        print("\\n📋 RESUMEN:")
        print("-" * 20)
        
        if verify_success:
            print("✅ JavaScript corregido completamente")
            print("✅ El error 'Cannot set properties of null' debería estar solucionado")
            print("\\n💡 PRÓXIMOS PASOS:")
            print("   1. Refresca la página de selección de asientos")
            print("   2. Abre la consola del navegador (F12)")
            print("   3. No deberías ver el error de textContent")
        else:
            print("❌ Hay problemas con la corrección")
    else:
        print("\\n❌ No se pudo corregir el archivo")
        print("\\n🔧 SOLUCIÓN MANUAL:")
        print("   1. Abre venezuelan_pos/apps/sales/templates/sales/seat_selection.html")
        print("   2. Busca la línea con 'textContent = ''")
        print("   3. Reemplázala por: textContent = '$' + parseFloat(data.cart_total).toFixed(2);")