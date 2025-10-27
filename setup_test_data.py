#!/usr/bin/env python
"""
Script para crear usuarios y datos de prueba para el sistema POS venezolano.
Genera tenants, usuarios, eventos, venues, zonas, precios y clientes de prueba.
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

# Importar modelos después de configurar Django
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Venue, Event, EventConfiguration
from venezuelan_pos.apps.zones.models import Zone, Seat, Table, TableSeat
from venezuelan_pos.apps.pricing.models import PriceStage, RowPricing
from venezuelan_pos.apps.customers.models import Customer, CustomerPreferences


class TestDataGenerator:
    """Generador de datos de prueba para el sistema POS."""
    
    def __init__(self):
        self.tenants = {}
        self.users = {}
        self.venues = {}
        self.events = {}
        self.zones = {}
        self.customers = {}
        
    def create_tenants(self):
        """Crear tenants de prueba."""
        print("🏢 Creando tenants...")
        
        tenant_data = [
            {
                'name': 'Teatro Nacional',
                'slug': 'teatro-nacional',
                'contact_email': 'admin@teatronacional.ve',
                'contact_phone': '+58-212-555-0001',
                'fiscal_series_prefix': 'TN',
                'configuration': {
                    'currency': 'USD',
                    'timezone': 'America/Caracas',
                    'language': 'es'
                }
            },
            {
                'name': 'Centro de Convenciones Caracas',
                'slug': 'ccc-eventos',
                'contact_email': 'eventos@ccc.ve',
                'contact_phone': '+58-212-555-0002',
                'fiscal_series_prefix': 'CCC',
                'configuration': {
                    'currency': 'USD',
                    'timezone': 'America/Caracas',
                    'language': 'es'
                }
            },
            {
                'name': 'Poliedro de Caracas',
                'slug': 'poliedro',
                'contact_email': 'info@poliedro.ve',
                'contact_phone': '+58-212-555-0003',
                'fiscal_series_prefix': 'POL',
                'configuration': {
                    'currency': 'USD',
                    'timezone': 'America/Caracas',
                    'language': 'es'
                }
            }
        ]
        
        for data in tenant_data:
            tenant, created = Tenant.objects.get_or_create(
                slug=data['slug'],
                defaults=data
            )
            self.tenants[data['slug']] = tenant
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {tenant.name}")
    
    def create_users(self):
        """Crear usuarios de prueba."""
        print("\n👥 Creando usuarios...")
        
        # Usuario admin global
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@venezuelanpos.com',
                'first_name': 'Admin',
                'last_name': 'Sistema',
                'role': User.Role.ADMIN_USER,
                'is_staff': True,
                'is_superuser': True,
                'phone': '+58-212-555-0000'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        self.users['admin'] = admin_user
        status = "✅ Creado" if created else "⚠️  Ya existe"
        print(f"  {status}: Admin Global - {admin_user.username}")
        
        # Usuarios por tenant
        user_data = [
            # Teatro Nacional
            {
                'username': 'admin_teatro',
                'email': 'admin@teatronacional.ve',
                'first_name': 'María',
                'last_name': 'González',
                'role': User.Role.TENANT_ADMIN,
                'tenant': 'teatro-nacional',
                'phone': '+58-414-555-0001'
            },
            {
                'username': 'operador_teatro',
                'email': 'operador@teatronacional.ve',
                'first_name': 'Carlos',
                'last_name': 'Rodríguez',
                'role': User.Role.EVENT_OPERATOR,
                'tenant': 'teatro-nacional',
                'phone': '+58-424-555-0001'
            },
            # Centro de Convenciones
            {
                'username': 'admin_ccc',
                'email': 'admin@ccc.ve',
                'first_name': 'Ana',
                'last_name': 'Martínez',
                'role': User.Role.TENANT_ADMIN,
                'tenant': 'ccc-eventos',
                'phone': '+58-414-555-0002'
            },
            {
                'username': 'operador_ccc',
                'email': 'operador@ccc.ve',
                'first_name': 'Luis',
                'last_name': 'Pérez',
                'role': User.Role.EVENT_OPERATOR,
                'tenant': 'ccc-eventos',
                'phone': '+58-424-555-0002'
            },
            # Poliedro
            {
                'username': 'admin_poliedro',
                'email': 'admin@poliedro.ve',
                'first_name': 'Carmen',
                'last_name': 'Silva',
                'role': User.Role.TENANT_ADMIN,
                'tenant': 'poliedro',
                'phone': '+58-414-555-0003'
            },
            {
                'username': 'operador_poliedro',
                'email': 'operador@poliedro.ve',
                'first_name': 'José',
                'last_name': 'Hernández',
                'role': User.Role.EVENT_OPERATOR,
                'tenant': 'poliedro',
                'phone': '+58-424-555-0003'
            }
        ]
        
        for data in user_data:
            tenant = self.tenants[data.pop('tenant')]
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={**data, 'tenant': tenant}
            )
            if created:
                user.set_password('password123')
                user.save()
            self.users[data['username']] = user
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {user.get_role_display()} - {user.username} ({tenant.name})")
    
    def create_venues(self):
        """Crear venues de prueba."""
        print("\n🏛️  Creando venues...")
        
        venue_data = [
            # Teatro Nacional
            {
                'name': 'Sala Principal',
                'tenant': 'teatro-nacional',
                'address': 'Av. Lecuna, Plaza Morelos',
                'city': 'Caracas',
                'state': 'Distrito Capital',
                'capacity': 800,
                'venue_type': 'physical',
                'contact_phone': '+58-212-555-1001',
                'contact_email': 'sala@teatronacional.ve'
            },
            {
                'name': 'Sala Experimental',
                'tenant': 'teatro-nacional',
                'address': 'Av. Lecuna, Plaza Morelos',
                'city': 'Caracas',
                'state': 'Distrito Capital',
                'capacity': 200,
                'venue_type': 'physical',
                'contact_phone': '+58-212-555-1002',
                'contact_email': 'experimental@teatronacional.ve'
            },
            # Centro de Convenciones
            {
                'name': 'Auditorio Principal',
                'tenant': 'ccc-eventos',
                'address': 'Av. Principal de Las Mercedes',
                'city': 'Caracas',
                'state': 'Distrito Capital',
                'capacity': 1500,
                'venue_type': 'physical',
                'contact_phone': '+58-212-555-2001',
                'contact_email': 'auditorio@ccc.ve'
            },
            {
                'name': 'Salón de Eventos',
                'tenant': 'ccc-eventos',
                'address': 'Av. Principal de Las Mercedes',
                'city': 'Caracas',
                'state': 'Distrito Capital',
                'capacity': 500,
                'venue_type': 'physical',
                'contact_phone': '+58-212-555-2002',
                'contact_email': 'salon@ccc.ve'
            },
            # Poliedro
            {
                'name': 'Arena Principal',
                'tenant': 'poliedro',
                'address': 'Av. José María Vargas, Santa Fe Norte',
                'city': 'Caracas',
                'state': 'Distrito Capital',
                'capacity': 12000,
                'venue_type': 'physical',
                'contact_phone': '+58-212-555-3001',
                'contact_email': 'arena@poliedro.ve'
            }
        ]
        
        for data in venue_data:
            tenant_slug = data.pop('tenant')
            tenant = self.tenants[tenant_slug]
            
            venue, created = Venue.objects.get_or_create(
                name=data['name'],
                tenant=tenant,
                defaults=data
            )
            venue_key = f"{tenant_slug}_{data['name'].lower().replace(' ', '_')}"
            self.venues[venue_key] = venue
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {venue.name} ({tenant.name})")
    
    def create_events(self):
        """Crear eventos de prueba."""
        print("\n🎭 Creando eventos...")
        
        now = timezone.now()
        
        event_data = [
            # Teatro Nacional
            {
                'name': 'Romeo y Julieta',
                'tenant': 'teatro-nacional',
                'venue': 'teatro-nacional_sala_principal',
                'description': 'Clásica obra de Shakespeare interpretada por la Compañía Nacional de Teatro',
                'event_type': Event.EventType.NUMBERED_SEAT,
                'start_date': now + timedelta(days=30),
                'end_date': now + timedelta(days=30, hours=3),
                'sales_start_date': now + timedelta(days=1),
                'sales_end_date': now + timedelta(days=29),
                'base_currency': 'USD',
                'status': Event.Status.ACTIVE
            },
            {
                'name': 'Concierto de Piano',
                'tenant': 'teatro-nacional',
                'venue': 'teatro-nacional_sala_experimental',
                'description': 'Recital de piano clásico con obras de Chopin y Beethoven',
                'event_type': Event.EventType.GENERAL_ASSIGNMENT,
                'start_date': now + timedelta(days=15),
                'end_date': now + timedelta(days=15, hours=2),
                'sales_start_date': now,
                'sales_end_date': now + timedelta(days=14),
                'base_currency': 'USD',
                'status': Event.Status.ACTIVE
            },
            # Centro de Convenciones
            {
                'name': 'Conferencia Tech Venezuela 2024',
                'tenant': 'ccc-eventos',
                'venue': 'ccc-eventos_auditorio_principal',
                'description': 'Conferencia anual de tecnología con speakers internacionales',
                'event_type': Event.EventType.NUMBERED_SEAT,
                'start_date': now + timedelta(days=45),
                'end_date': now + timedelta(days=47),
                'sales_start_date': now,
                'sales_end_date': now + timedelta(days=44),
                'base_currency': 'USD',
                'status': Event.Status.ACTIVE
            },
            {
                'name': 'Gala Empresarial',
                'tenant': 'ccc-eventos',
                'venue': 'ccc-eventos_salón_de_eventos',
                'description': 'Cena de gala para empresarios y ejecutivos',
                'event_type': Event.EventType.NUMBERED_SEAT,
                'start_date': now + timedelta(days=20),
                'end_date': now + timedelta(days=20, hours=4),
                'sales_start_date': now,
                'sales_end_date': now + timedelta(days=19),
                'base_currency': 'USD',
                'status': Event.Status.ACTIVE
            },
            # Poliedro
            {
                'name': 'Concierto Ricardo Arjona',
                'tenant': 'poliedro',
                'venue': 'poliedro_arena_principal',
                'description': 'Concierto del cantautor guatemalteco Ricardo Arjona',
                'event_type': Event.EventType.MIXED,
                'start_date': now + timedelta(days=60),
                'end_date': now + timedelta(days=60, hours=4),
                'sales_start_date': now,
                'sales_end_date': now + timedelta(days=59),
                'base_currency': 'USD',
                'status': Event.Status.ACTIVE
            }
        ]
        
        for data in event_data:
            tenant_slug = data.pop('tenant')
            venue_key = data.pop('venue')
            tenant = self.tenants[tenant_slug]
            venue = self.venues[venue_key]
            
            event, created = Event.objects.get_or_create(
                name=data['name'],
                tenant=tenant,
                start_date=data['start_date'],
                defaults={**data, 'venue': venue}
            )
            
            # Crear configuración del evento
            if created:
                EventConfiguration.objects.create(
                    event=event,
                    tenant=tenant,
                    partial_payments_enabled=True,
                    installment_plans_enabled=True,
                    max_installments=3,
                    min_down_payment_percentage=Decimal('25.00'),
                    notifications_enabled=True,
                    email_notifications=True,
                    digital_tickets_enabled=True,
                    qr_codes_enabled=True
                )
            
            event_key = f"{tenant_slug}_{data['name'].lower().replace(' ', '_').replace('ñ', 'n')}"
            self.events[event_key] = event
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {event.name} ({tenant.name})")
    
    def create_zones_and_pricing(self):
        """Crear zonas y configuración de precios."""
        print("\n🎫 Creando zonas y precios...")
        
        # Configuración de zonas por evento
        zone_configs = {
            # Romeo y Julieta (Teatro Nacional)
            'teatro-nacional_romeo_y_julieta': [
                {
                    'name': 'Platea',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 300,
                    'rows': 15,
                    'seats_per_row': 20,
                    'base_price': Decimal('50.00'),
                    'row_pricing': {
                        1: 100.00,  # Primera fila +100%
                        2: 75.00,   # Segunda fila +75%
                        3: 50.00,   # Tercera fila +50%
                    }
                },
                {
                    'name': 'Palcos',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 80,
                    'rows': 4,
                    'seats_per_row': 20,
                    'base_price': Decimal('75.00')
                },
                {
                    'name': 'Galería',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 420,
                    'rows': 21,
                    'seats_per_row': 20,
                    'base_price': Decimal('25.00')
                }
            ],
            # Concierto de Piano (Teatro Nacional)
            'teatro-nacional_concierto_de_piano': [
                {
                    'name': 'General',
                    'zone_type': Zone.ZoneType.GENERAL,
                    'capacity': 200,
                    'base_price': Decimal('30.00')
                }
            ],
            # Conferencia Tech (CCC)
            'ccc-eventos_conferencia_tech_venezuela_2024': [
                {
                    'name': 'VIP',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 100,
                    'rows': 5,
                    'seats_per_row': 20,
                    'base_price': Decimal('150.00')
                },
                {
                    'name': 'Premium',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 400,
                    'rows': 20,
                    'seats_per_row': 20,
                    'base_price': Decimal('100.00')
                },
                {
                    'name': 'General',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 1000,
                    'rows': 50,
                    'seats_per_row': 20,
                    'base_price': Decimal('50.00')
                }
            ],
            # Gala Empresarial (CCC)
            'ccc-eventos_gala_empresarial': [
                {
                    'name': 'Mesa VIP',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 80,
                    'rows': 8,
                    'seats_per_row': 10,
                    'base_price': Decimal('200.00')
                },
                {
                    'name': 'Mesa Premium',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 420,
                    'rows': 42,
                    'seats_per_row': 10,
                    'base_price': Decimal('120.00')
                }
            ],
            # Concierto Arjona (Poliedro)
            'poliedro_concierto_ricardo_arjona': [
                {
                    'name': 'Pista',
                    'zone_type': Zone.ZoneType.GENERAL,
                    'capacity': 3000,
                    'base_price': Decimal('80.00')
                },
                {
                    'name': 'Palcos VIP',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 200,
                    'rows': 10,
                    'seats_per_row': 20,
                    'base_price': Decimal('250.00')
                },
                {
                    'name': 'Gradería Alta',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 4000,
                    'rows': 100,
                    'seats_per_row': 40,
                    'base_price': Decimal('45.00')
                },
                {
                    'name': 'Gradería Baja',
                    'zone_type': Zone.ZoneType.NUMBERED,
                    'capacity': 4800,
                    'rows': 120,
                    'seats_per_row': 40,
                    'base_price': Decimal('60.00')
                }
            ]
        }
        
        for event_key, zones in zone_configs.items():
            if event_key not in self.events:
                continue
                
            event = self.events[event_key]
            print(f"\n  📍 Zonas para {event.name}:")
            
            for i, zone_data in enumerate(zones):
                row_pricing_config = zone_data.pop('row_pricing', {})
                
                zone, created = Zone.objects.get_or_create(
                    event=event,
                    name=zone_data['name'],
                    defaults={
                        **zone_data,
                        'tenant': event.tenant,
                        'display_order': i + 1
                    }
                )
                
                # Crear pricing por filas si está configurado
                if created and row_pricing_config and zone.zone_type == Zone.ZoneType.NUMBERED:
                    for row_num, markup_percentage in row_pricing_config.items():
                        RowPricing.objects.create(
                            zone=zone,
                            tenant=event.tenant,
                            row_number=row_num,
                            percentage_markup=Decimal(str(markup_percentage)),
                            name=f"Fila {row_num} Premium"
                        )
                
                zone_key = f"{event_key}_{zone_data['name'].lower().replace(' ', '_')}"
                self.zones[zone_key] = zone
                status = "✅ Creado" if created else "⚠️  Ya existe"
                print(f"    {status}: {zone.name} ({zone.get_zone_type_display()}) - ${zone.base_price}")
        
        # Crear etapas de precios para algunos eventos
        self.create_price_stages()
    
    def create_price_stages(self):
        """Crear etapas de precios para eventos seleccionados."""
        print("\n  💰 Creando etapas de precios...")
        
        now = timezone.now()
        
        # Etapas para Romeo y Julieta
        if 'teatro-nacional_romeo_y_julieta' in self.events:
            event = self.events['teatro-nacional_romeo_y_julieta']
            
            stages = [
                {
                    'name': 'Early Bird',
                    'start_date': now + timedelta(days=1),
                    'end_date': now + timedelta(days=10),
                    'percentage_markup': Decimal('-20.00'),  # 20% descuento
                    'stage_order': 1
                },
                {
                    'name': 'Preventa',
                    'start_date': now + timedelta(days=10),
                    'end_date': now + timedelta(days=20),
                    'percentage_markup': Decimal('0.00'),  # Precio base
                    'stage_order': 2
                },
                {
                    'name': 'Venta Regular',
                    'start_date': now + timedelta(days=20),
                    'end_date': now + timedelta(days=29),
                    'percentage_markup': Decimal('15.00'),  # 15% aumento
                    'stage_order': 3
                }
            ]
            
            for stage_data in stages:
                stage, created = PriceStage.objects.get_or_create(
                    event=event,
                    name=stage_data['name'],
                    defaults={**stage_data, 'tenant': event.tenant}
                )
                status = "✅ Creado" if created else "⚠️  Ya existe"
                print(f"    {status}: {stage.name} ({stage.percentage_markup}%)")
        
        # Etapas para Conferencia Tech
        if 'ccc-eventos_conferencia_tech_venezuela_2024' in self.events:
            event = self.events['ccc-eventos_conferencia_tech_venezuela_2024']
            
            stages = [
                {
                    'name': 'Super Early Bird',
                    'start_date': now,
                    'end_date': now + timedelta(days=15),
                    'percentage_markup': Decimal('-30.00'),
                    'stage_order': 1
                },
                {
                    'name': 'Early Bird',
                    'start_date': now + timedelta(days=15),
                    'end_date': now + timedelta(days=30),
                    'percentage_markup': Decimal('-15.00'),
                    'stage_order': 2
                },
                {
                    'name': 'Regular',
                    'start_date': now + timedelta(days=30),
                    'end_date': now + timedelta(days=44),
                    'percentage_markup': Decimal('0.00'),
                    'stage_order': 3
                }
            ]
            
            for stage_data in stages:
                stage, created = PriceStage.objects.get_or_create(
                    event=event,
                    name=stage_data['name'],
                    defaults={**stage_data, 'tenant': event.tenant}
                )
                status = "✅ Creado" if created else "⚠️  Ya existe"
                print(f"    {status}: {stage.name} ({stage.percentage_markup}%)")
    
    def create_customers(self):
        """Crear clientes de prueba."""
        print("\n👥 Creando clientes...")
        
        customer_data = [
            # Teatro Nacional
            {
                'tenant': 'teatro-nacional',
                'name': 'Pedro',
                'surname': 'Ramírez',
                'phone': '+58-414-123-4567',
                'email': 'pedro.ramirez@email.com',
                'identification': 'V-12345678',
                'address': 'Av. Libertador, Caracas'
            },
            {
                'tenant': 'teatro-nacional',
                'name': 'María',
                'surname': 'López',
                'phone': '+58-424-987-6543',
                'email': 'maria.lopez@email.com',
                'identification': 'V-87654321',
                'address': 'Las Mercedes, Caracas'
            },
            {
                'tenant': 'teatro-nacional',
                'name': 'Carlos',
                'surname': 'García',
                'phone': '+58-412-555-1234',
                'email': 'carlos.garcia@email.com',
                'identification': 'V-11223344',
                'address': 'Altamira, Caracas'
            },
            # Centro de Convenciones
            {
                'tenant': 'ccc-eventos',
                'name': 'Ana',
                'surname': 'Martínez',
                'phone': '+58-416-777-8888',
                'email': 'ana.martinez@empresa.com',
                'identification': 'V-55667788',
                'address': 'La Castellana, Caracas'
            },
            {
                'tenant': 'ccc-eventos',
                'name': 'Luis',
                'surname': 'Hernández',
                'phone': '+58-426-999-0000',
                'email': 'luis.hernandez@tech.com',
                'identification': 'V-99887766',
                'address': 'El Rosal, Caracas'
            },
            {
                'tenant': 'ccc-eventos',
                'name': 'Carmen',
                'surname': 'Silva',
                'phone': '+58-414-333-2222',
                'email': 'carmen.silva@consulting.com',
                'identification': 'V-44556677',
                'address': 'Chacao, Caracas'
            },
            # Poliedro
            {
                'tenant': 'poliedro',
                'name': 'José',
                'surname': 'Rodríguez',
                'phone': '+58-424-111-2222',
                'email': 'jose.rodriguez@email.com',
                'identification': 'V-22334455',
                'address': 'Maracay, Aragua'
            },
            {
                'tenant': 'poliedro',
                'name': 'Elena',
                'surname': 'Morales',
                'phone': '+58-412-444-5555',
                'email': 'elena.morales@email.com',
                'identification': 'V-66778899',
                'address': 'Valencia, Carabobo'
            },
            {
                'tenant': 'poliedro',
                'name': 'Roberto',
                'surname': 'Díaz',
                'phone': '+58-416-666-7777',
                'email': 'roberto.diaz@email.com',
                'identification': 'V-33445566',
                'address': 'Barquisimeto, Lara'
            },
            {
                'tenant': 'poliedro',
                'name': 'Isabella',
                'surname': 'Fernández',
                'phone': '+58-426-888-9999',
                'email': 'isabella.fernandez@email.com',
                'identification': 'V-77889900',
                'address': 'Mérida, Mérida'
            }
        ]
        
        for data in customer_data:
            tenant_slug = data.pop('tenant')
            tenant = self.tenants[tenant_slug]
            
            customer, created = Customer.objects.get_or_create(
                identification=data['identification'],
                tenant=tenant,
                defaults={**data, 'tenant': tenant}
            )
            
            customer_key = f"{tenant_slug}_{data['identification']}"
            self.customers[customer_key] = customer
            status = "✅ Creado" if created else "⚠️  Ya existe"
            print(f"  {status}: {customer.full_name} ({customer.identification}) - {tenant.name}")
    
    @transaction.atomic
    def run(self):
        """Ejecutar la generación completa de datos de prueba."""
        print("🚀 Iniciando generación de datos de prueba...\n")
        
        try:
            self.create_tenants()
            self.create_users()
            self.create_venues()
            self.create_events()
            self.create_zones_and_pricing()
            self.create_customers()
            
            print("\n✅ ¡Datos de prueba creados exitosamente!")
            print("\n📋 Resumen:")
            print(f"  • Tenants: {len(self.tenants)}")
            print(f"  • Usuarios: {len(self.users)}")
            print(f"  • Venues: {len(self.venues)}")
            print(f"  • Eventos: {len(self.events)}")
            print(f"  • Zonas: {len(self.zones)}")
            print(f"  • Clientes: {len(self.customers)}")
            
            print("\n🔑 Credenciales de acceso:")
            print("  • Admin Global: admin / admin123")
            print("  • Admins Tenant: admin_teatro, admin_ccc, admin_poliedro / password123")
            print("  • Operadores: operador_teatro, operador_ccc, operador_poliedro / password123")
            
            print("\n🌐 URLs de acceso por tenant:")
            print("  • Teatro Nacional: http://teatro-nacional.localhost:8000")
            print("  • Centro Convenciones: http://ccc-eventos.localhost:8000")
            print("  • Poliedro: http://poliedro.localhost:8000")
            
        except Exception as e:
            print(f"\n❌ Error durante la generación de datos: {str(e)}")
            raise


if __name__ == '__main__':
    generator = TestDataGenerator()
    generator.run()