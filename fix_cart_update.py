#!/usr/bin/env python
"""
Script para corregir la función updateCartDisplay y hacer que el carrito se actualice automáticamente.
"""

import os
import re

def fix_cart_update():
    """Corregir la función updateCartDisplay."""
    
    print("🛒 CORRIGIENDO ACTUALIZACIÓN AUTOMÁTICA DEL CARRITO")
    print("=" * 60)
    
    file_path = "venezuelan_pos/apps/sales/templates/sales/seat_selection.html"
    
    try:
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ Archivo leído correctamente")
        
        # Buscar y reemplazar la función updateCartDisplay problemática
        # Patrón para encontrar la función completa
        pattern = r'function updateCartDisplay\(\) \{[^}]*fetch\([^}]*\}[^}]*\}[^}]*\}'
        
        # Nueva función corregida
        new_function = '''function updateCartDisplay() {
    console.log('🔄 Updating cart display...');
    
    fetch('{% url "sales:ajax_cart_update" %}')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Cart data received:', data);
                
                // Update cart count
                const cartCountElement = document.getElementById('cartCount');
                if (cartCountElement) {
                    cartCountElement.textContent = data.cart_count;
                }
                
                // Update cart total
                const cartTotalElement = document.getElementById('cartTotal');
                if (cartTotalElement) {
                    cartTotalElement.textContent = '$' + parseFloat(data.cart_total).toFixed(2);
                }
                
                // Update cart content dynamically
                const cartContent = document.getElementById('cartContent');
                if (cartContent) {
                    if (data.cart_count === 0) {
                        // Empty cart
                        cartContent.innerHTML = `
                            <div class="text-center text-muted py-4">
                                <i class="bi bi-cart display-4"></i>
                                <p class="mt-2">Your cart is empty</p>
                                <small>Select seats or zones to add tickets</small>
                            </div>
                        `;
                    } else {
                        // Cart has items - build the HTML dynamically
                        let cartHTML = '';
                        
                        if (data.cart_items && data.cart_items.length > 0) {
                            data.cart_items.forEach(item => {
                                cartHTML += `
                                    <div class="cart-item" data-item-key="${item.item_key}">
                                        <div class="d-flex justify-content-between align-items-start">
                                            <div class="flex-grow-1">
                                                <h6 class="mb-1">${item.zone_name}</h6>
                                                ${item.seat_label ? 
                                                    `<small class="text-muted">${item.seat_label}</small>` : 
                                                    `<small class="text-muted">${item.quantity} tickets</small>`
                                                }
                                            </div>
                                            <div class="text-end">
                                                <div class="fw-bold">$${parseFloat(item.total_price).toFixed(2)}</div>
                                                <button class="btn btn-sm btn-outline-danger" 
                                                        onclick="removeFromCart('${item.item_key}')">
                                                    <i class="bi bi-trash"></i>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        
                        // Add total and checkout buttons
                        cartHTML += `
                            <hr>
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <strong>Total:</strong>
                                <strong class="fs-5">$${parseFloat(data.cart_total).toFixed(2)}</strong>
                            </div>
                            
                            <div class="d-grid gap-2">
                                <a href="{% url 'sales:checkout' %}" class="btn btn-primary">
                                    <i class="bi bi-credit-card"></i> Proceed to Checkout
                                </a>
                                <button class="btn btn-outline-secondary" onclick="clearCart()">
                                    <i class="bi bi-trash"></i> Clear Cart
                                </button>
                            </div>
                        `;
                        
                        cartContent.innerHTML = cartHTML;
                    }
                }
                
                console.log('✅ Cart display updated successfully');
            } else {
                console.error('❌ Cart update failed:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error updating cart display:', error);
        });
}'''
        
        # Buscar la función problemática y reemplazarla
        if 'function updateCartDisplay()' in content:
            print("✅ Función updateCartDisplay encontrada")
            
            # Método más agresivo: buscar desde function hasta el final de la función
            start_pattern = r'function updateCartDisplay\(\) \{'
            
            # Encontrar el inicio
            start_match = re.search(start_pattern, content)
            if start_match:
                start_pos = start_match.start()
                
                # Encontrar el final de la función contando llaves
                pos = start_match.end()
                brace_count = 1
                
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1
                
                if brace_count == 0:
                    # Reemplazar la función completa
                    old_function = content[start_pos:pos]
                    content = content[:start_pos] + new_function + content[pos:]
                    
                    print("✅ Función updateCartDisplay reemplazada")
                else:
                    print("❌ No se pudo encontrar el final de la función")
                    return False
            else:
                print("❌ No se pudo encontrar el inicio de la función")
                return False
        else:
            print("❌ Función updateCartDisplay no encontrada")
            return False
        
        # Limpiar cualquier contenido corrupto
        content = re.sub(r'</content>.*?</file>', '', content, flags=re.DOTALL)
        content = re.sub(r'<issues>.*?</issues>', '', content, flags=re.DOTALL)
        
        # Escribir el archivo corregido
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Archivo corregido y guardado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al procesar el archivo: {e}")
        return False

def verify_fix():
    """Verificar que el fix funcionó."""
    
    print("\\n🔍 VERIFICANDO FIX:")
    print("-" * 30)
    
    file_path = "venezuelan_pos/apps/sales/templates/sales/seat_selection.html"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que no hay contenido corrupto
        if '</content>' in content or '<issues>' in content:
            print("❌ Todavía hay contenido corrupto")
            return False
        
        # Verificar que la nueva función está presente
        if 'console.log(\'🔄 Updating cart display...\')' in content:
            print("✅ Nueva función updateCartDisplay encontrada")
        else:
            print("❌ Nueva función updateCartDisplay no encontrada")
            return False
        
        # Verificar que no hay location.reload()
        if 'location.reload()' in content:
            print("❌ Todavía hay location.reload() en el código")
            return False
        else:
            print("✅ location.reload() removido")
        
        # Verificar que hay actualización dinámica
        if 'cartContent.innerHTML = cartHTML' in content:
            print("✅ Actualización dinámica del carrito implementada")
        else:
            print("❌ Actualización dinámica no encontrada")
            return False
        
        print("✅ Todos los checks pasaron")
        return True
        
    except Exception as e:
        print(f"❌ Error al verificar: {e}")
        return False

if __name__ == '__main__':
    success = fix_cart_update()
    
    if success:
        verify_success = verify_fix()
        
        print("\\n📋 RESUMEN:")
        print("-" * 20)
        
        if verify_success:
            print("✅ Carrito se actualizará automáticamente")
            print("✅ No más location.reload()")
            print("✅ Actualización dinámica implementada")
            print("\\n💡 PRÓXIMOS PASOS:")
            print("   1. Refresca la página de selección de asientos")
            print("   2. Agrega asientos al carrito")
            print("   3. El carrito debería actualizarse automáticamente")
            print("   4. No deberías necesitar refrescar la página")
        else:
            print("❌ Hay problemas con la corrección")
    else:
        print("\\n❌ No se pudo corregir el archivo")
        print("\\n🔧 SOLUCIÓN MANUAL:")
        print("   1. Abre venezuelan_pos/apps/sales/templates/sales/seat_selection.html")
        print("   2. Busca la función updateCartDisplay")
        print("   3. Reemplaza location.reload() por actualización dinámica del HTML")