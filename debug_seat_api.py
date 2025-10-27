#!/usr/bin/env python
"""
Debug script to test the seat API endpoint directly
"""
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from venezuelan_pos.apps.zones.models import Zone, Seat
from venezuelan_pos.apps.zones.serializers import SeatSerializer
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from venezuelan_pos.apps.tenants.models import Tenant

def test_seat_api():
    print("=== Testing Seat API Endpoint ===")
    
    # Find the ZonaTest zone
    zone = Zone.objects.filter(name='ZonaTest', rows=10, seats_per_row=6).first()
    if not zone:
        print("❌ ZonaTest zone not found")
        return
    
    print(f"✅ Found zone: {zone.name} (ID: {zone.id})")
    
    # Get seats from database
    seats = Seat.objects.filter(zone=zone).order_by('row_number', 'seat_number')
    print(f"✅ Found {seats.count()} seats in database")
    
    # Test serializer directly
    print("\n=== Testing Serializer ===")
    serializer = SeatSerializer(seats, many=True)
    serialized_data = serializer.data
    print(f"✅ Serialized {len(serialized_data)} seats")
    
    # Show first few seats
    print("\n=== First 6 Seats (Serialized) ===")
    for i, seat_data in enumerate(serialized_data[:6]):
        print(f"Seat {i+1}: Row {seat_data['row_number']}, Seat {seat_data['seat_number']}, Status: {seat_data['status']}")
    
    # Test API client
    print("\n=== Testing API Client ===")
    client = APIClient()
    
    # Try without authentication first
    response = client.get(f'/api/v1/api/seats/?zone={zone.id}')
    print(f"Without auth - Status: {response.status_code}")
    
    if response.status_code == 401:
        print("API requires authentication, trying with user...")
        
        # Find a user with access to this tenant
        tenant = zone.tenant
        user = User.objects.filter(tenantuser__tenant=tenant).first()
        
        if user:
            print(f"Found user: {user.username} for tenant: {tenant.name}")
            client.force_authenticate(user=user)
            
            response = client.get(f'/api/v1/api/seats/?zone={zone.id}')
            print(f"With auth - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API returned {len(data.get('results', []))} seats")
                
                # Show structure
                if data.get('results'):
                    first_seat = data['results'][0]
                    print(f"First seat structure: {json.dumps(first_seat, indent=2)}")
            else:
                print(f"❌ API error: {response.content}")
        else:
            print("❌ No user found for this tenant")
    
    elif response.status_code == 200:
        data = response.json()
        print(f"✅ API returned {len(data.get('results', []))} seats without auth")
    
    print("\n=== Summary ===")
    print(f"Zone ID: {zone.id}")
    print(f"Total seats in DB: {seats.count()}")
    print(f"Expected: 10 rows × 6 seats = 60 seats")
    print(f"API endpoint: /api/v1/api/seats/?zone={zone.id}")

if __name__ == "__main__":
    test_seat_api()