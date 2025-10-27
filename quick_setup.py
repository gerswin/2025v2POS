#!/usr/bin/env python
"""
Script rápido para configuración básica del sistema.
Crea un tenant, usuario admin y datos mínimos para empezar a probar.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

# Importar modelos
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Venue, Event, EventConfiguration
from venezuelan_pos.apps.zones.models import Zone
from venezuelan_pos.apps.customers.models import Customer


def create_basic_setup():
    """Crear configuración básica para pruebas rápidas."""
    print("🚀 Configuración rápida del sistema...\n")
    
    with transaction.atomic():
        # 1. Crear tenant principal
        print("🏢 Creando tenant principal...")
        tenant, created = Tenant.objects.get_or_create(
            slug='demo',
            defaults={
                'name': 'Demo Venue',
                'contact_email': 'admin@demo.com',
                'contact_phone': '+58-212-555-0000',
                'fiscal_series_prefix': 'DEMO',
                'configuration': {
                    'currency': 'USD',
                    'timezone': 'America/Caracas',
                    'language': 'es'
                }
            }
        )
        status = "✅ Creado" if created else "⚠️  Ya existe"
        print(f"  {status}: {tenant.name}")
        
        # 2. Crear usuario admin
        print("\n👤 Creando usuario administrador...")
        admin_user, created = User.objects.get_or_create(
            username='demo_admin',
            defaults={
                'email': 'admin@demo.com',
                'first_name': 'Admin',
                'last_name': 'Demo',
                'role': User.Role.TENANT_ADMIN,
                'tenant': tenant,
                'is_staff': True,
                'phone': '+58-414-555-0000'
            }
        )
        if created:
            admin_user.set_password('demo123')
            admin_user.save()
        status = "✅ Creado" if created else "⚠️  Ya existe"
        print(f"  {status}: {admin_user.username}")
        
        # 3. Crear venue
        print("\n🏛️  Creando venue...")
        venue, created = Venue.objects.get_or_create(
            name='Teatro Demo',
            tenant=tenant,
            defaults={
                'address': 'Av. Principal, Caracas',
                'city': 'Caracas',
                'state': 'Distrito Capital',
                'capacity': 500,
                'venue_type': 'physical',
                'contact_phone': '+58-212-555-1000',
                'contact_email': 'teatro@demo.com'
            }
        )
        status = "✅ Creado" if created else "⚠️  Ya existe"
        print(f"  {status}: {venue.name}")
        
        # 4. Crear evento de prueba
        print("\n🎭 Creando evento de prueba...")
        now = timezone.now()
        event, created = Event.objects.get_or_create(
            name='Evento Demo',
            tenant=tenant,
            start_date=now + timedelta(days=30),
            defaults={
                'description': 'Evento de demostración para pruebas del sistema',
                'venue': venue,
                'event_type': Event.EventType.NUMBERED_SEAT,
                'end_date': now + timedelta(days=30, hours=3),
                'sales_start_date': now,
                'sales_end_date': now + timedelta(days=29),
                'base_currency': 'USD',
                'status': Event.Status.ACTIVE
            }
        )
        
        if created:
            # Crear configuración del evento
            EventConfiguration.objects.create(
                event=event,
                tenant=tenant,
                partial_payments_enabled=True,
                notifications_enabled=True,
                email_notifications=True,
                digital_tickets_enabled=True,
                qr_codes_enabled=True
            )
        
        status = "✅ Creado" if created else "⚠️  Ya existe"
        print(f"  {status}: {event.name}")
        
        # 5. Crear zonas básicas
        print("\n🎫 Creando zonas...")
        zones_data = [
            {
                'name': 'VIP',
                'zone_type': Zone.ZoneType.NUMBERED,
                'capacity': 50,
                'rows': 5,
                'seats_per_row': 10,
                'base_price': Decimal('100.00'),
                'display_order': 1
            },
            {
                'name': 'Premium',
                'zone_type': Zone.ZoneType.NUMBERED,
                'capacity': 200,
                'rows': 10,
                'seats_per_row': 20,
                'base_price': Decimal('75.00'),
                'display_order': 2
            },
            {
                'name': 'General',
                'zone_type': Zone.ZoneType.NUMBERED,
                'capacity': 250,
                'rows': 25,
                'seats_per_row': 10,
                'base_price': Decimal('50.00'),
                'display_order': 3
            }
        ]
        
        for zone_data in zones_data:
            zone, created = Zone.objects.get_or_create(
                event=event,
                name=zone_data['name'],
                defaults={**zone_data, 'tenant': tenant}
            )
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {zone.name} - ${zone.base_price}")
        
        # 6. Crear algunos clientes de prueba
        print("\n👥 Creando clientes de prueba...")
        customers_data = [
            {
                'name': 'Juan',
                'surname': 'Pérez',
                'phone': '+58-414-123-4567',
                'email': 'juan.perez@email.com',
                'identification': 'V-12345678'
            },
            {
                'name': 'María',
                'surname': 'González',
                'phone': '+58-424-987-6543',
                'email': 'maria.gonzalez@email.com',
                'identification': 'V-87654321'
            },
            {
                'name': 'Carlos',
                'surname': 'Rodríguez',
                'phone': '+58-412-555-9999',
                'email': 'carlos.rodriguez@email.com',
                'identification': 'V-11223344'
            }
        ]
        
        for customer_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                identification=customer_data['identification'],
                tenant=tenant,
                defaults={**customer_data, 'tenant': tenant}
            )
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {customer.full_name} ({customer.identification})")
    
    print("\n✅ ¡Configuración básica completada!")
    print("\n🔑 Credenciales de acceso:")
    print("  • Usuario: demo_admin")
    print("  • Contraseña: demo123")
    print("\n🌐 URL de acceso:")
    print("  • http://demo.localhost:8000")
    print("  • http://localhost:8000 (si no usas subdominios)")
    print("\n📋 Datos creados:")
    print("  • 1 Tenant (Demo Venue)")
    print("  • 1 Usuario admin")
    print("  • 1 Venue (Teatro Demo)")
    print("  • 1 Evento (Evento Demo)")
    print("  • 3 Zonas (VIP, Premium, General)")
    print("  • 3 Clientes de prueba")


if __name__ == '__main__':
    try:
        create_basic_setup()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)