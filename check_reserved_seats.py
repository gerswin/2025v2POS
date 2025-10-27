#!/usr/bin/env python
"""
Script para verificar si hay asientos reservados en el sistema.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone, Seat

def check_reserved_seats():
    """Verificar si hay asientos reservados en el sistema."""
    
    print("🔍 VERIFICANDO ASIENTOS RESERVADOS")
    print("=" * 50)
    
    # Obtener todos los eventos
    events = Event.objects.all()
    print(f"✅ Eventos encontrados: {len(events)}")
    
    total_reserved = 0
    
    for event in events:
        print(f"\\n📅 Evento: {event.name}")
        
        # Obtener zonas del evento
        zones = event.zones.all()
        print(f"   Zonas: {len(zones)}")
        
        for zone in zones:
            if zone.zone_type == Zone.ZoneType.NUMBERED:
                # Contar asientos por estado
                available = zone.seats.filter(status=Seat.Status.AVAILABLE).count()
                reserved = zone.seats.filter(status=Seat.Status.RESERVED).count()
                sold = zone.seats.filter(status=Seat.Status.SOLD).count()
                blocked = zone.seats.filter(status=Seat.Status.BLOCKED).count()
                total = zone.seats.count()
                
                print(f"   🎫 {zone.name}:")
                print(f"      Total: {total}")
                print(f"      Available: {available}")
                print(f"      Reserved: {reserved}")
                print(f"      Sold: {sold}")
                print(f"      Blocked: {blocked}")
                
                total_reserved += reserved
                
                # Si hay asientos reservados, mostrar algunos ejemplos
                if reserved > 0:
                    reserved_seats = zone.seats.filter(status=Seat.Status.RESERVED)[:3]
                    print(f"      Ejemplos de asientos reservados:")
                    for seat in reserved_seats:
                        print(f"        - {seat.seat_label} (ID: {seat.id})")
    
    print(f"\\n📊 RESUMEN GENERAL:")
    print(f"   Total asientos reservados en el sistema: {total_reserved}")
    
    if total_reserved > 0:
        print("\\n✅ SÍ HAY ASIENTOS RESERVADOS")
        print("   Deberían mostrarse en amarillo (#ffc107) en la interfaz")
        print("   No deberían ser seleccionables (cursor: not-allowed)")
    else:
        print("\\n⚠️ NO HAY ASIENTOS RESERVADOS")
        print("   Para probar la funcionalidad, puedes:")
        print("   1. Crear algunas reservas manualmente")
        print("   2. O cambiar el estado de algunos asientos a 'reserved'")
    
    return total_reserved > 0

def create_test_reservations():
    """Crear algunas reservas de prueba."""
    
    print("\\n🧪 CREANDO RESERVAS DE PRUEBA:")
    print("-" * 30)
    
    # Obtener el primer evento con zonas numeradas
    event = Event.objects.filter(zones__zone_type=Zone.ZoneType.NUMBERED).first()
    if not event:
        print("❌ No hay eventos con zonas numeradas")
        return False
    
    print(f"✅ Usando evento: {event.name}")
    
    # Obtener la primera zona numerada
    zone = event.zones.filter(zone_type=Zone.ZoneType.NUMBERED).first()
    if not zone:
        print("❌ No hay zonas numeradas")
        return False
    
    print(f"✅ Usando zona: {zone.name}")
    
    # Obtener algunos asientos disponibles
    available_seats = zone.seats.filter(status=Seat.Status.AVAILABLE)[:3]
    if not available_seats:
        print("❌ No hay asientos disponibles para reservar")
        return False
    
    print(f"✅ Asientos disponibles encontrados: {len(available_seats)}")
    
    # Cambiar algunos asientos a reservado
    reserved_count = 0
    for seat in available_seats:
        seat.status = Seat.Status.RESERVED
        seat.save()
        print(f"   🟡 {seat.seat_label} → RESERVED")
        reserved_count += 1
    
    print(f"\\n✅ {reserved_count} asientos marcados como RESERVED")
    print(f"   Evento: {event.name}")
    print(f"   Zona: {zone.name}")
    print(f"   URL para probar: http://localhost:8000/sales/events/{event.id}/select-seats/")
    
    return True

if __name__ == '__main__':
    has_reserved = check_reserved_seats()
    
    if not has_reserved:
        print("\\n🔧 ¿QUIERES CREAR RESERVAS DE PRUEBA?")
        response = input("Escribe 'si' para crear algunas reservas de prueba: ")
        
        if response.lower() in ['si', 'sí', 'yes', 'y']:
            create_test_reservations()
            print("\\n🎯 AHORA PUEDES PROBAR:")
            print("   1. Ve al navegador")
            print("   2. Refresca la página de selección de asientos")
            print("   3. Selecciona una zona numerada")
            print("   4. Deberías ver asientos amarillos (reservados)")
            print("   5. Los asientos reservados NO deberían ser seleccionables")
        else:
            print("\\n💡 Para ver asientos reservados en acción:")
            print("   1. Crea algunas reservas desde la interfaz de ventas")
            print("   2. O ejecuta este script de nuevo y acepta crear reservas de prueba")
    else:
        print("\\n🎉 HAY ASIENTOS RESERVADOS EN EL SISTEMA")
        print("   Deberían mostrarse correctamente en la interfaz")