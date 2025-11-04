#!/usr/bin/env python
"""
Script para verificar y solucionar problemas con el admin fiscal.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from django.contrib import admin
from django.contrib.auth import get_user_model
from venezuelan_pos.apps.fiscal.models import TaxConfiguration, FiscalSeries
from venezuelan_pos.apps.tenants.models import Tenant

def verificar_admin_fiscal():
    """Verificar que los modelos fiscales estén registrados en el admin."""
    
    print("🔍 Verificando configuración del admin fiscal...")
    
    # Verificar modelos registrados
    modelos_fiscales = [
        'TaxConfiguration',
        'FiscalSeries', 
        'FiscalSeriesCounter',
        'FiscalDay',
        'FiscalReport',
        'AuditLog',
        'TaxCalculationHistory'
    ]
    
    modelos_registrados = []
    for model_name in admin.site._registry:
        if hasattr(model_name, '_meta') and model_name._meta.app_label == 'fiscal':
            modelos_registrados.append(model_name.__name__)
    
    print(f"📋 Modelos fiscales registrados en admin: {modelos_registrados}")
    
    for modelo in modelos_fiscales:
        if modelo in modelos_registrados:
            print(f"✅ {modelo} - Registrado")
        else:
            print(f"❌ {modelo} - NO registrado")
    
    return len(modelos_registrados) > 0

def verificar_permisos_usuario():
    """Verificar permisos del usuario admin."""
    
    print("\n🔐 Verificando permisos de usuario...")
    
    User = get_user_model()
    
    try:
        # Buscar usuario admin
        admin_users = User.objects.filter(is_superuser=True)
        
        if not admin_users.exists():
            print("❌ No se encontraron usuarios superuser")
            return False
        
        for user in admin_users:
            print(f"✅ Usuario superuser encontrado: {user.username}")
            print(f"   - Email: {user.email}")
            print(f"   - Staff: {user.is_staff}")
            print(f"   - Superuser: {user.is_superuser}")
            print(f"   - Activo: {user.is_active}")
            print(f"   - Rol: {user.role}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando usuarios: {e}")
        return False

def crear_configuracion_impuesto_ejemplo():
    """Crear una configuración de impuesto de ejemplo."""
    
    print("\n💰 Creando configuración de impuesto de ejemplo...")
    
    try:
        # Obtener o crear tenant
        tenant = Tenant.objects.first()
        if not tenant:
            print("❌ No se encontró ningún tenant. Crear uno primero.")
            return False
        
        # Obtener usuario admin
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("❌ No se encontró usuario admin")
            return False
        
        # Crear configuración de IVA si no existe
        iva_config, created = TaxConfiguration.objects.get_or_create(
            tenant=tenant,
            name="IVA",
            scope="TENANT",
            defaults={
                'tax_type': 'PERCENTAGE',
                'rate': 0.16,  # 16%
                'effective_from': django.utils.timezone.now(),
                'is_active': True,
                'created_by': admin_user
            }
        )
        
        if created:
            print(f"✅ Configuración de IVA creada: {iva_config}")
        else:
            print(f"✅ Configuración de IVA ya existe: {iva_config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando configuración de impuesto: {e}")
        return False

def mostrar_urls_acceso():
    """Mostrar URLs de acceso al admin fiscal."""
    
    print("\n🌐 URLs de acceso al admin fiscal:")
    print("   📋 Admin principal: http://localhost:8000/admin/")
    print("   🧾 Tax Configurations: http://localhost:8000/admin/fiscal/taxconfiguration/")
    print("   📊 Fiscal Series: http://localhost:8000/admin/fiscal/fiscalseries/")
    print("   📈 Fiscal Reports: http://localhost:8000/admin/fiscal/fiscalreport/")
    print("   🔍 Audit Logs: http://localhost:8000/admin/fiscal/auditlog/")
    print("\n🌐 Interfaz web fiscal:")
    print("   💼 Dashboard fiscal: http://localhost:8000/fiscal/")
    print("   🧮 Calculadora de impuestos: http://localhost:8000/fiscal/tax-calculator/")

if __name__ == "__main__":
    print("🚀 Verificando configuración del admin fiscal...\n")
    
    # Verificar admin
    admin_ok = verificar_admin_fiscal()
    
    # Verificar permisos
    permisos_ok = verificar_permisos_usuario()
    
    # Crear ejemplo si todo está bien
    if admin_ok and permisos_ok:
        crear_configuracion_impuesto_ejemplo()
    
    # Mostrar URLs
    mostrar_urls_acceso()
    
    if admin_ok and permisos_ok:
        print("\n🎉 ¡Todo parece estar configurado correctamente!")
        print("\n📝 Próximos pasos:")
        print("1. Reinicia el servidor Django si está corriendo")
        print("2. Accede a http://localhost:8000/admin/")
        print("3. Busca la sección 'FISCAL' en el menú lateral")
        print("4. Si no aparece, verifica que estés logueado como superuser")
    else:
        print("\n❌ Hay problemas con la configuración. Revisar errores arriba.")