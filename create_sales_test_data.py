#!/usr/bin/env python
"""
Script simplificado para crear datos de prueba para las interfaces de ventas.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from venezuelan_pos.apps.tenants.models import Tenant
from venezuelan_pos.apps.events.models import Venue, Event
from venezuelan_pos.apps.zones.models import Zone, Seat
from venezuelan_pos.apps.customers.models import Customer
from venezuelan_pos.apps.pricing.models import PriceStage

User = get_user_model()

def main():
    print("🔧 Creando datos de prueba para las interfaces de ventas...")
    
    # Obtener tenant y usuario existentes
    tenant = Tenant.objects.get(slug='test-venue')
    user = User.objects.get(username='sales_operator')
    print(f"✅ Usando tenant: {tenant.name}")
    print(f"✅ Usando usuario: {user.username}")
    
    # Crear venue
    venue, created = Venue.objects.get_or_create(
        tenant=tenant,
        name='Teatro Principal',
        defaults={
            'address': 'Av. Principal 123, Caracas',
            'city': 'Caracas',
            'country': 'Venezuela',
            'capacity': 500,
            'venue_type': 'physical',
            'is_active': True
        }
    )
    if created:
        print(f"✅ Venue creado: {venue.name}")
    else:
        print(f"✅ Venue existente: {venue.name}")
    
    # Crear evento activo
    start_date = timezone.now() + timedelta(days=7)
    end_date = start_date + timedelta(hours=3)
    
    event, created = Event.objects.get_or_create(
        tenant=tenant,
        name='Concierto de Prueba',
        start_date=start_date,
        defaults={
            'description': 'Evento de prueba para testing de ventas',
            'venue': venue,
            'end_date': end_date,
            'sales_start_date': timezone.now() - timedelta(days=1),
            'sales_end_date': start_date - timedelta(hours=2),
            'event_type': Event.EventType.MIXED,
            'status': Event.Status.ACTIVE,
            'base_currency': 'USD'
        }
    )
    if created:
        print(f"✅ Evento creado: {event.name}")
    else:
        print(f"✅ Evento existente: {event.name}")
    
    # Crear zonas
    zone_numbered, created = Zone.objects.get_or_create(
        tenant=tenant,
        event=event,
        name='VIP',
        defaults={
            'description': 'Zona VIP con asientos numerados',
            'zone_type': Zone.ZoneType.NUMBERED,
            'capacity': 50,
            'rows': 5,
            'seats_per_row': 10,
            'base_price': Decimal('100.00'),
            'status': Zone.Status.ACTIVE,
            'display_order': 1
        }
    )
    if created:
        print(f"✅ Zona numerada creada: {zone_numbered.name}")
    
    zone_general, created = Zone.objects.get_or_create(
        tenant=tenant,
        event=event,
        name='General',
        defaults={
            'description': 'Admisión general',
            'zone_type': Zone.ZoneType.GENERAL,
            'capacity': 200,
            'base_price': Decimal('50.00'),
            'status': Zone.Status.ACTIVE,
            'display_order': 2
        }
    )
    if created:
        print(f"✅ Zona general creada: {zone_general.name}")
    
    # Crear clientes de prueba
    customers_data = [
        {
            'name': 'Juan',
            'surname': 'Pérez',
            'phone': '+58 414 123 4567',
            'email': 'juan.perez@email.com',
            'identification': 'V-12345678'
        },
        {
            'name': 'María',
            'surname': 'González',
            'phone': '+58 424 987 6543',
            'email': 'maria.gonzalez@email.com',
            'identification': 'V-87654321'
        }
    ]
    
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            tenant=tenant,
            email=customer_data['email'],
            defaults=customer_data
        )
        if created:
            print(f"✅ Cliente creado: {customer.full_name}")
    
    print("\n🎉 Datos de prueba creados exitosamente!")
    print("\n" + "="*60)
    print("🚀 INFORMACIÓN DE ACCESO A LAS INTERFACES DE VENTAS")
    print("="*60)
    
    print("\n📱 CREDENCIALES DE ACCESO:")
    print("   Usuario: sales_operator")
    print("   Contraseña: testpass123")
    
    print("\n🌐 URLS PRINCIPALES:")
    print("   • Login: http://localhost:8000/auth/login/")
    print("   • Dashboard Principal: http://localhost:8000/")
    print("   • Dashboard de Ventas: http://localhost:8000/sales/")
    print("   • Selección de Asientos: http://localhost:8000/sales/events/{}/select-seats/".format(event.id))
    
    print("\n🎯 FLUJO DE PRUEBA RECOMENDADO:")
    print("   1. Hacer login con las credenciales arriba")
    print("   2. Ir al Dashboard de Ventas (menú lateral 'Sales')")
    print("   3. Hacer clic en 'Sell Tickets' en el evento activo")
    print("   4. Seleccionar zona VIP o General")
    print("   5. Seleccionar asientos (VIP) o cantidad (General)")
    print("   6. Agregar al carrito")
    print("   7. Proceder al checkout")
    print("   8. Seleccionar cliente y completar compra")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()