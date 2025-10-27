#!/usr/bin/env python
"""
Test Users Creation Script for Venezuelan POS System

This script creates a comprehensive set of test users, tenants, venues, and events
to facilitate testing of the system's functionality.

Usage:
    python create_test_users.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from django.utils import timezone
from venezuelan_pos.apps.tenants.models import Tenant, User, TenantUser
from venezuelan_pos.apps.events.models import Venue, Event, EventConfiguration


def create_test_data():
    """Create comprehensive test data for the Venezuelan POS System."""
    
    print("🚀 Creating test data for Venezuelan POS System...")
    
    # =============================================================================
    # TENANTS
    # =============================================================================
    print("\n📊 Creating Tenants...")
    
    tenants = [
        {
            'name': 'Eventos Caracas',
            'slug': 'eventos-caracas',
            'contact_email': 'admin@eventoscaracas.com',
            'contact_phone': '+58-212-555-0001',
            'fiscal_series_prefix': 'EC',
            'configuration': {
                'default_currency': 'USD',
                'tax_rate': '16.00',
                'company_address': 'Av. Francisco de Miranda, Caracas 1060'
            }
        },
        {
            'name': 'Valencia Entertainment',
            'slug': 'valencia-entertainment',
            'contact_email': 'info@valenciaent.com',
            'contact_phone': '+58-241-555-0002',
            'fiscal_series_prefix': 'VE',
            'configuration': {
                'default_currency': 'USD',
                'tax_rate': '16.00',
                'company_address': 'Centro Comercial Sambil, Valencia 2001'
            }
        },
        {
            'name': 'Maracaibo Shows',
            'slug': 'maracaibo-shows',
            'contact_email': 'contact@maracaiboshows.com',
            'contact_phone': '+58-261-555-0003',
            'fiscal_series_prefix': 'MS',
            'configuration': {
                'default_currency': 'USD',
                'tax_rate': '16.00',
                'company_address': 'Av. 5 de Julio, Maracaibo 4001'
            }
        }
    ]
    
    created_tenants = {}
    for tenant_data in tenants:
        tenant, created = Tenant.objects.get_or_create(
            slug=tenant_data['slug'],
            defaults=tenant_data
        )
        created_tenants[tenant.slug] = tenant
        status = "✅ Created" if created else "🔄 Updated"
        print(f"  {status}: {tenant.name}")
    
    # =============================================================================
    # USERS
    # =============================================================================
    print("\n👥 Creating Users...")
    
    users_data = [
        # System Admin Users
        {
            'username': 'admin',
            'email': 'admin@venezuelanpos.com',
            'password': 'admin123',
            'first_name': 'System',
            'last_name': 'Administrator',
            'role': User.Role.ADMIN_USER,
            'tenant': None,
            'is_superuser': True,
            'is_staff': True
        },
        
        # Eventos Caracas Users
        {
            'username': 'carlos.admin',
            'email': 'carlos@eventoscaracas.com',
            'password': 'carlos123',
            'first_name': 'Carlos',
            'last_name': 'Rodríguez',
            'role': User.Role.TENANT_ADMIN,
            'tenant': 'eventos-caracas',
            'phone': '+58-414-555-1001'
        },
        {
            'username': 'maria.operator',
            'email': 'maria@eventoscaracas.com',
            'password': 'maria123',
            'first_name': 'María',
            'last_name': 'González',
            'role': User.Role.EVENT_OPERATOR,
            'tenant': 'eventos-caracas',
            'phone': '+58-424-555-1002'
        },
        {
            'username': 'jose.operator',
            'email': 'jose@eventoscaracas.com',
            'password': 'jose123',
            'first_name': 'José',
            'last_name': 'Pérez',
            'role': User.Role.EVENT_OPERATOR,
            'tenant': 'eventos-caracas',
            'phone': '+58-414-555-1003'
        },
        
        # Valencia Entertainment Users
        {
            'username': 'ana.admin',
            'email': 'ana@valenciaent.com',
            'password': 'ana123',
            'first_name': 'Ana',
            'last_name': 'Martínez',
            'role': User.Role.TENANT_ADMIN,
            'tenant': 'valencia-entertainment',
            'phone': '+58-414-555-2001'
        },
        {
            'username': 'luis.operator',
            'email': 'luis@valenciaent.com',
            'password': 'luis123',
            'first_name': 'Luis',
            'last_name': 'Hernández',
            'role': User.Role.EVENT_OPERATOR,
            'tenant': 'valencia-entertainment',
            'phone': '+58-424-555-2002'
        },
        
        # Maracaibo Shows Users
        {
            'username': 'sofia.admin',
            'email': 'sofia@maracaiboshows.com',
            'password': 'sofia123',
            'first_name': 'Sofía',
            'last_name': 'López',
            'role': User.Role.TENANT_ADMIN,
            'tenant': 'maracaibo-shows',
            'phone': '+58-414-555-3001'
        },
        {
            'username': 'pedro.operator',
            'email': 'pedro@maracaiboshows.com',
            'password': 'pedro123',
            'first_name': 'Pedro',
            'last_name': 'Ramírez',
            'role': User.Role.EVENT_OPERATOR,
            'tenant': 'maracaibo-shows',
            'phone': '+58-424-555-3002'
        }
    ]
    
    created_users = {}
    for user_data in users_data:
        tenant_slug = user_data.pop('tenant', None)
        tenant = created_tenants.get(tenant_slug) if tenant_slug else None
        
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={**user_data, 'tenant': tenant}
        )
        
        if created:
            user.set_password(user_data['password'])
            user.save()
        
        created_users[user.username] = user
        status = "✅ Created" if created else "🔄 Updated"
        tenant_name = tenant.name if tenant else "System"
        print(f"  {status}: {user.first_name} {user.last_name} ({user.get_role_display()}) - {tenant_name}")
    
    # =============================================================================
    # VENUES
    # =============================================================================
    print("\n🏢 Creating Venues...")
    
    venues_data = [
        # Eventos Caracas Venues
        {
            'tenant': 'eventos-caracas',
            'name': 'Teatro Teresa Carreño',
            'address': 'Av. Paseo Colón, Los Caobos',
            'city': 'Caracas',
            'state': 'Distrito Capital',
            'capacity': 2400,
            'venue_type': 'physical',
            'contact_phone': '+58-212-574-9122',
            'contact_email': 'info@teatroteresacarreno.gob.ve'
        },
        {
            'tenant': 'eventos-caracas',
            'name': 'Poliedro de Caracas',
            'address': 'Av. Libertador, La Rinconada',
            'city': 'Caracas',
            'state': 'Distrito Capital',
            'capacity': 15000,
            'venue_type': 'physical',
            'contact_phone': '+58-212-693-4567',
            'contact_email': 'eventos@poliedro.com.ve'
        },
        {
            'tenant': 'eventos-caracas',
            'name': 'Centro de Arte Los Galpones',
            'address': 'Av. Ávila, Los Chorros',
            'city': 'Caracas',
            'state': 'Distrito Capital',
            'capacity': 800,
            'venue_type': 'physical',
            'contact_phone': '+58-212-283-4567',
            'contact_email': 'info@losgalpones.com'
        },
        
        # Valencia Entertainment Venues
        {
            'tenant': 'valencia-entertainment',
            'name': 'Teatro Municipal de Valencia',
            'address': 'Plaza Bolívar, Centro',
            'city': 'Valencia',
            'state': 'Carabobo',
            'capacity': 1200,
            'venue_type': 'physical',
            'contact_phone': '+58-241-857-3456',
            'contact_email': 'teatro@valencia.gob.ve'
        },
        {
            'tenant': 'valencia-entertainment',
            'name': 'Forum de Valencia',
            'address': 'Av. Bolívar Norte',
            'city': 'Valencia',
            'state': 'Carabobo',
            'capacity': 8000,
            'venue_type': 'physical',
            'contact_phone': '+58-241-824-5678',
            'contact_email': 'eventos@forumvalencia.com'
        },
        
        # Maracaibo Shows Venues
        {
            'tenant': 'maracaibo-shows',
            'name': 'Teatro Baralt',
            'address': 'Av. 2 El Milagro, Centro',
            'city': 'Maracaibo',
            'state': 'Zulia',
            'capacity': 1500,
            'venue_type': 'physical',
            'contact_phone': '+58-261-722-3456',
            'contact_email': 'info@teatrobaralt.com'
        },
        {
            'tenant': 'maracaibo-shows',
            'name': 'Centro de Convenciones Lago Mar',
            'address': 'Av. El Milagro',
            'city': 'Maracaibo',
            'state': 'Zulia',
            'capacity': 5000,
            'venue_type': 'physical',
            'contact_phone': '+58-261-700-1234',
            'contact_email': 'eventos@lagomar.com.ve'
        }
    ]
    
    created_venues = {}
    for venue_data in venues_data:
        tenant_slug = venue_data.pop('tenant')
        tenant = created_tenants[tenant_slug]
        
        venue, created = Venue.objects.get_or_create(
            tenant=tenant,
            name=venue_data['name'],
            defaults=venue_data
        )
        
        created_venues[f"{tenant_slug}_{venue.name}"] = venue
        status = "✅ Created" if created else "🔄 Updated"
        print(f"  {status}: {venue.name} ({venue.city}) - {tenant.name}")
    
    # =============================================================================
    # EVENTS
    # =============================================================================
    print("\n🎭 Creating Events...")
    
    now = timezone.now()
    
    events_data = [
        # Eventos Caracas Events
        {
            'tenant': 'eventos-caracas',
            'venue': 'eventos-caracas_Teatro Teresa Carreño',
            'name': 'Concierto Sinfónico de Año Nuevo',
            'description': 'Gran concierto sinfónico para celebrar el Año Nuevo 2025',
            'event_type': Event.EventType.NUMBERED_SEAT,
            'start_date': now + timedelta(days=67),  # New Year's Eve
            'end_date': now + timedelta(days=67, hours=3),
            'sales_start_date': now + timedelta(days=1),
            'sales_end_date': now + timedelta(days=66),
            'status': Event.Status.ACTIVE,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50'),
            'configuration': {
                'dress_code': 'Formal',
                'age_restriction': '12+',
                'parking_available': True
            }
        },
        {
            'tenant': 'eventos-caracas',
            'venue': 'eventos-caracas_Poliedro de Caracas',
            'name': 'Festival Rock Venezolano 2025',
            'description': 'El festival de rock más grande de Venezuela',
            'event_type': Event.EventType.GENERAL_ASSIGNMENT,
            'start_date': now + timedelta(days=45),
            'end_date': now + timedelta(days=45, hours=8),
            'sales_start_date': now - timedelta(days=5),
            'sales_end_date': now + timedelta(days=44),
            'status': Event.Status.ACTIVE,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50')
        },
        {
            'tenant': 'eventos-caracas',
            'venue': 'eventos-caracas_Centro de Arte Los Galpones',
            'name': 'Exposición de Arte Contemporáneo',
            'description': 'Muestra de artistas venezolanos contemporáneos',
            'event_type': Event.EventType.GENERAL_ASSIGNMENT,
            'start_date': now + timedelta(days=15),
            'end_date': now + timedelta(days=45),
            'sales_start_date': now - timedelta(days=10),
            'sales_end_date': now + timedelta(days=44),
            'status': Event.Status.ACTIVE,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50')
        },
        
        # Valencia Entertainment Events
        {
            'tenant': 'valencia-entertainment',
            'venue': 'valencia-entertainment_Teatro Municipal de Valencia',
            'name': 'Obra Teatral: Romeo y Julieta',
            'description': 'Adaptación moderna del clásico de Shakespeare',
            'event_type': Event.EventType.NUMBERED_SEAT,
            'start_date': now + timedelta(days=30),
            'end_date': now + timedelta(days=30, hours=2, minutes=30),
            'sales_start_date': now - timedelta(days=2),
            'sales_end_date': now + timedelta(days=29),
            'status': Event.Status.ACTIVE,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50')
        },
        {
            'tenant': 'valencia-entertainment',
            'venue': 'valencia-entertainment_Forum de Valencia',
            'name': 'Concierto de Salsa Internacional',
            'description': 'Los mejores exponentes de la salsa internacional',
            'event_type': Event.EventType.MIXED,
            'start_date': now + timedelta(days=60),
            'end_date': now + timedelta(days=60, hours=5),
            'sales_start_date': now + timedelta(days=5),
            'sales_end_date': now + timedelta(days=59),
            'status': Event.Status.DRAFT,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50')
        },
        
        # Maracaibo Shows Events
        {
            'tenant': 'maracaibo-shows',
            'venue': 'maracaibo-shows_Teatro Baralt',
            'name': 'Recital de Piano Clásico',
            'description': 'Recital de música clásica con pianista internacional',
            'event_type': Event.EventType.NUMBERED_SEAT,
            'start_date': now + timedelta(days=25),
            'end_date': now + timedelta(days=25, hours=2),
            'sales_start_date': now - timedelta(days=7),
            'sales_end_date': now + timedelta(days=24),
            'status': Event.Status.ACTIVE,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50')
        },
        {
            'tenant': 'maracaibo-shows',
            'venue': 'maracaibo-shows_Centro de Convenciones Lago Mar',
            'name': 'Feria Gastronómica del Zulia',
            'description': 'Muestra de la gastronomía tradicional zuliana',
            'event_type': Event.EventType.GENERAL_ASSIGNMENT,
            'start_date': now + timedelta(days=40),
            'end_date': now + timedelta(days=42),
            'sales_start_date': now + timedelta(days=2),
            'sales_end_date': now + timedelta(days=39),
            'status': Event.Status.DRAFT,
            'base_currency': 'USD',
            'currency_conversion_rate': Decimal('36.50')
        }
    ]
    
    created_events = {}
    for event_data in events_data:
        tenant_slug = event_data.pop('tenant')
        venue_key = event_data.pop('venue')
        
        tenant = created_tenants[tenant_slug]
        venue = created_venues[venue_key]
        
        event, created = Event.objects.get_or_create(
            tenant=tenant,
            name=event_data['name'],
            start_date=event_data['start_date'],
            defaults={**event_data, 'venue': venue}
        )
        
        # Create event configuration
        if created:
            config_data = {
                'partial_payments_enabled': True,
                'installment_plans_enabled': True,
                'flexible_payments_enabled': False,
                'max_installments': 3,
                'min_down_payment_percentage': Decimal('25.00'),
                'notifications_enabled': True,
                'email_notifications': True,
                'digital_tickets_enabled': True,
                'qr_codes_enabled': True,
                'pdf_tickets_enabled': True
            }
            
            EventConfiguration.objects.create(
                tenant=tenant,
                event=event,
                **config_data
            )
        
        created_events[f"{tenant_slug}_{event.name}"] = event
        status = "✅ Created" if created else "🔄 Updated"
        print(f"  {status}: {event.name} - {venue.name}")
    
    print("\n🎉 Test data creation completed successfully!")
    
    # =============================================================================
    # SUMMARY
    # =============================================================================
    print("\n" + "="*80)
    print("📋 TEST DATA SUMMARY")
    print("="*80)
    
    print(f"\n🏢 Tenants Created: {len(created_tenants)}")
    for tenant in created_tenants.values():
        print(f"  • {tenant.name} ({tenant.slug})")
    
    print(f"\n👥 Users Created: {len(created_users)}")
    for user in created_users.values():
        tenant_name = user.tenant.name if user.tenant else "System"
        print(f"  • {user.username} - {user.first_name} {user.last_name} ({user.get_role_display()}) - {tenant_name}")
    
    print(f"\n🏢 Venues Created: {len(created_venues)}")
    for venue in created_venues.values():
        print(f"  • {venue.name} ({venue.city}) - {venue.tenant.name}")
    
    print(f"\n🎭 Events Created: {len(created_events)}")
    for event in created_events.values():
        print(f"  • {event.name} - {event.venue.name} ({event.get_status_display()})")
    
    return {
        'tenants': created_tenants,
        'users': created_users,
        'venues': created_venues,
        'events': created_events
    }


if __name__ == '__main__':
    try:
        create_test_data()
    except Exception as e:
        print(f"\n❌ Error creating test data: {e}")
        sys.exit(1)