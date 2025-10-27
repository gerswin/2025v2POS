#!/usr/bin/env python
"""
Simple script to get seat information for testing
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from venezuelan_pos.apps.zones.models import Zone

def get_seat_info():
    # Find the ZonaTest zone
    zone = Zone.objects.filter(name='ZonaTest', rows=10, seats_per_row=6).first()
    if not zone:
        print("❌ ZonaTest zone not found")
        return
    
    print("=== Seat Management Test Info ===")
    print(f"Zone: {zone.name}")
    print(f"Zone ID: {zone.id}")
    print(f"Event: {zone.event.name}")
    print(f"Tenant: {zone.tenant.name}")
    print(f"Configuration: {zone.rows} rows × {zone.seats_per_row} seats = {zone.capacity} total")
    print()
    print("=== Test URLs ===")
    print(f"Login: http://localhost:8001/auth/login/")
    print(f"Seat Management: http://localhost:8001/zones/{zone.id}/seats/")
    print()
    print("=== Test Credentials ===")
    print("Username: caracas_admin")
    print("Password: caracas123")
    print()
    print("=== Expected Result ===")
    print("You should see 10 rows with 6 seats each (60 total seats)")
    print("If you see fewer seats, there's a JavaScript rendering issue")

if __name__ == "__main__":
    get_seat_info()