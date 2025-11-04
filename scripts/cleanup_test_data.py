#!/usr/bin/env python
"""
Script para limpiar datos de prueba del sistema.
Permite eliminar todos los datos o solo datos específicos.
"""

import os
import sys
import django
from django.db import transaction

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

# Importar modelos
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Venue, Event, EventConfiguration
from venezuelan_pos.apps.zones.models import Zone, Seat, Table, TableSeat
from venezuelan_pos.apps.pricing.models import PriceStage, RowPricing, PriceHistory
from venezuelan_pos.apps.customers.models import Customer, CustomerPreferences


def cleanup_all_data():
    """Limpiar todos los datos de prueba."""
    print("🧹 Limpiando todos los datos de prueba...")
    
    with transaction.atomic():
        # Eliminar en orden para respetar las relaciones de foreign key
        print("  🗑️  Eliminando historial de precios...")
        PriceHistory.objects.all().delete()
        
        print("  🗑️  Eliminando configuraciones de precios...")
        RowPricing.objects.all().delete()
        PriceStage.objects.all().delete()
        
        print("  🗑️  Eliminando relaciones de mesas...")
        TableSeat.objects.all().delete()
        Table.objects.all().delete()
        
        print("  🗑️  Eliminando asientos...")
        Seat.objects.all().delete()
        
        print("  🗑️  Eliminando zonas...")
        Zone.objects.all().delete()
        
        print("  🗑️  Eliminando configuraciones de eventos...")
        EventConfiguration.objects.all().delete()
        
        print("  🗑️  Eliminando eventos...")
        Event.objects.all().delete()
        
        print("  🗑️  Eliminando venues...")
        Venue.objects.all().delete()
        
        print("  🗑️  Eliminando preferencias de clientes...")
        CustomerPreferences.objects.all().delete()
        
        print("  🗑️  Eliminando clientes...")
        Customer.objects.all().delete()
        
        print("  🗑️  Eliminando usuarios (excepto superusuarios)...")
        User.objects.filter(is_superuser=False).delete()
        
        print("  🗑️  Eliminando tenants...")
        Tenant.objects.all().delete()
    
    print("✅ Todos los datos de prueba han sido eliminados.")


def cleanup_tenant_data(tenant_slug):
    """Limpiar datos de un tenant específico."""
    print(f"🧹 Limpiando datos del tenant: {tenant_slug}")
    
    try:
        tenant = Tenant.objects.get(slug=tenant_slug)
    except Tenant.DoesNotExist:
        print(f"❌ Tenant '{tenant_slug}' no encontrado.")
        return
    
    with transaction.atomic():
        # Eliminar datos relacionados con el tenant
        print("  🗑️  Eliminando historial de precios...")
        PriceHistory.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando configuraciones de precios...")
        RowPricing.objects.filter(tenant=tenant).delete()
        PriceStage.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando relaciones de mesas...")
        TableSeat.objects.filter(tenant=tenant).delete()
        Table.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando asientos...")
        Seat.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando zonas...")
        Zone.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando configuraciones de eventos...")
        EventConfiguration.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando eventos...")
        Event.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando venues...")
        Venue.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando preferencias de clientes...")
        CustomerPreferences.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando clientes...")
        Customer.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando usuarios del tenant...")
        User.objects.filter(tenant=tenant).delete()
        
        print("  🗑️  Eliminando tenant...")
        tenant.delete()
    
    print(f"✅ Datos del tenant '{tenant_slug}' eliminados.")


def cleanup_events_only():
    """Limpiar solo eventos y datos relacionados, manteniendo tenants y usuarios."""
    print("🧹 Limpiando solo eventos y datos relacionados...")
    
    with transaction.atomic():
        print("  🗑️  Eliminando historial de precios...")
        PriceHistory.objects.all().delete()
        
        print("  🗑️  Eliminando configuraciones de precios...")
        RowPricing.objects.all().delete()
        PriceStage.objects.all().delete()
        
        print("  🗑️  Eliminando relaciones de mesas...")
        TableSeat.objects.all().delete()
        Table.objects.all().delete()
        
        print("  🗑️  Eliminando asientos...")
        Seat.objects.all().delete()
        
        print("  🗑️  Eliminando zonas...")
        Zone.objects.all().delete()
        
        print("  🗑️  Eliminando configuraciones de eventos...")
        EventConfiguration.objects.all().delete()
        
        print("  🗑️  Eliminando eventos...")
        Event.objects.all().delete()
    
    print("✅ Eventos y datos relacionados eliminados.")


def show_current_data():
    """Mostrar resumen de datos actuales en el sistema."""
    print("📊 Resumen de datos actuales:")
    print(f"  • Tenants: {Tenant.objects.count()}")
    print(f"  • Usuarios: {User.objects.count()}")
    print(f"  • Venues: {Venue.objects.count()}")
    print(f"  • Eventos: {Event.objects.count()}")
    print(f"  • Zonas: {Zone.objects.count()}")
    print(f"  • Asientos: {Seat.objects.count()}")
    print(f"  • Clientes: {Customer.objects.count()}")
    print(f"  • Etapas de precios: {PriceStage.objects.count()}")
    print(f"  • Precios por fila: {RowPricing.objects.count()}")
    
    if Tenant.objects.exists():
        print("\n🏢 Tenants existentes:")
        for tenant in Tenant.objects.all():
            print(f"  • {tenant.name} ({tenant.slug})")


def main():
    """Función principal con menú interactivo."""
    print("🧹 Script de Limpieza de Datos de Prueba")
    print("=" * 40)
    
    show_current_data()
    
    print("\n🔧 Opciones disponibles:")
    print("1. Limpiar TODOS los datos")
    print("2. Limpiar datos de un tenant específico")
    print("3. Limpiar solo eventos (mantener tenants y usuarios)")
    print("4. Mostrar resumen de datos")
    print("5. Salir")
    
    while True:
        try:
            choice = input("\n👉 Selecciona una opción (1-5): ").strip()
            
            if choice == '1':
                confirm = input("⚠️  ¿Estás seguro de eliminar TODOS los datos? (escriba 'SI' para confirmar): ")
                if confirm == 'SI':
                    cleanup_all_data()
                else:
                    print("❌ Operación cancelada.")
                break
                
            elif choice == '2':
                show_current_data()
                tenant_slug = input("\n👉 Ingresa el slug del tenant a eliminar: ").strip()
                if tenant_slug:
                    confirm = input(f"⚠️  ¿Eliminar tenant '{tenant_slug}' y todos sus datos? (escriba 'SI' para confirmar): ")
                    if confirm == 'SI':
                        cleanup_tenant_data(tenant_slug)
                    else:
                        print("❌ Operación cancelada.")
                break
                
            elif choice == '3':
                confirm = input("⚠️  ¿Eliminar todos los eventos y datos relacionados? (escriba 'SI' para confirmar): ")
                if confirm == 'SI':
                    cleanup_events_only()
                else:
                    print("❌ Operación cancelada.")
                break
                
            elif choice == '4':
                show_current_data()
                
            elif choice == '5':
                print("👋 ¡Hasta luego!")
                break
                
            else:
                print("❌ Opción inválida. Por favor selecciona 1-5.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Operación cancelada por el usuario.")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


if __name__ == '__main__':
    main()