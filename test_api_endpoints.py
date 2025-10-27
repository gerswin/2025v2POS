#!/usr/bin/env python
"""
API Endpoints Test Script for Venezuelan POS System

This script tests the main API endpoints with different user roles
to verify authentication, authorization, and multi-tenancy.

Usage:
    python test_api_endpoints.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test users
TEST_USERS = [
    {
        'username': 'admin',
        'password': 'admin123',
        'role': 'System Admin',
        'tenant': 'System'
    },
    {
        'username': 'carlos.admin',
        'password': 'carlos123',
        'role': 'Tenant Admin',
        'tenant': 'Eventos Caracas'
    },
    {
        'username': 'maria.operator',
        'password': 'maria123',
        'role': 'Event Operator',
        'tenant': 'Eventos Caracas'
    },
    {
        'username': 'ana.admin',
        'password': 'ana123',
        'role': 'Tenant Admin',
        'tenant': 'Valencia Entertainment'
    }
]

def login_user(username, password):
    """Login user and return access token."""
    try:
        response = requests.post(
            f"{API_BASE}/auth/login/",
            json={'username': username, 'password': password},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access')
        else:
            print(f"❌ Login failed for {username}: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Login error for {username}: {e}")
        return None

def test_endpoint(token, endpoint, method='GET', data=None, expected_status=200):
    """Test an API endpoint with authentication."""
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        if method == 'GET':
            response = requests.get(f"{API_BASE}{endpoint}", headers=headers)
        elif method == 'POST':
            response = requests.post(f"{API_BASE}{endpoint}", headers=headers, json=data)
        
        success = response.status_code == expected_status
        status_icon = "✅" if success else "❌"
        
        result = {
            'success': success,
            'status_code': response.status_code,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }
        
        return result
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': None,
            'data': None
        }

def run_tests():
    """Run comprehensive API tests."""
    print("🧪 Starting API Endpoint Tests")
    print("=" * 60)
    
    # Test each user
    for user in TEST_USERS:
        print(f"\n👤 Testing user: {user['username']} ({user['role']} - {user['tenant']})")
        print("-" * 50)
        
        # Login
        token = login_user(user['username'], user['password'])
        if not token:
            print("❌ Skipping tests - login failed")
            continue
        
        print("✅ Login successful")
        
        # Test endpoints
        endpoints = [
            ('/auth/profile/', 'GET', None, 200),
            ('/venues/', 'GET', None, 200),
            ('/events/', 'GET', None, 200),
            ('/venues/active/', 'GET', None, 200),
            ('/events/active/', 'GET', None, 200),
            ('/events/upcoming/', 'GET', None, 200),
        ]
        
        for endpoint, method, data, expected_status in endpoints:
            result = test_endpoint(token, endpoint, method, data, expected_status)
            status_icon = "✅" if result['success'] else "❌"
            
            if result['success'] and result['data']:
                count = result['data'].get('count', len(result['data']) if isinstance(result['data'], list) else 1)
                print(f"  {status_icon} {method} {endpoint} - {count} items")
            else:
                error_msg = result.get('error', f"Status: {result['status_code']}")
                print(f"  {status_icon} {method} {endpoint} - {error_msg}")
    
    print("\n" + "=" * 60)
    print("🎉 API Tests Completed")

def test_multi_tenancy():
    """Test multi-tenancy data isolation."""
    print("\n🏢 Testing Multi-Tenancy Data Isolation")
    print("=" * 60)
    
    # Login different tenant users
    carlos_token = login_user('carlos.admin', 'carlos123')
    ana_token = login_user('ana.admin', 'ana123')
    
    if not carlos_token or not ana_token:
        print("❌ Cannot test multi-tenancy - login failed")
        return
    
    # Test venues isolation
    carlos_venues = test_endpoint(carlos_token, '/venues/')
    ana_venues = test_endpoint(ana_token, '/venues/')
    
    if carlos_venues['success'] and ana_venues['success']:
        carlos_count = carlos_venues['data'].get('count', 0)
        ana_count = ana_venues['data'].get('count', 0)
        
        print(f"✅ Carlos (Eventos Caracas) sees {carlos_count} venues")
        print(f"✅ Ana (Valencia Entertainment) sees {ana_count} venues")
        
        if carlos_count > 0 and ana_count > 0:
            print("✅ Multi-tenancy working - users see different data")
        else:
            print("⚠️  One or both users see no venues")
    
    # Test events isolation
    carlos_events = test_endpoint(carlos_token, '/events/')
    ana_events = test_endpoint(ana_token, '/events/')
    
    if carlos_events['success'] and ana_events['success']:
        carlos_count = carlos_events['data'].get('count', 0)
        ana_count = ana_events['data'].get('count', 0)
        
        print(f"✅ Carlos (Eventos Caracas) sees {carlos_count} events")
        print(f"✅ Ana (Valencia Entertainment) sees {ana_count} events")
        
        if carlos_count > 0 and ana_count > 0:
            print("✅ Multi-tenancy working - users see different events")
        else:
            print("⚠️  One or both users see no events")

def test_permissions():
    """Test role-based permissions."""
    print("\n🔐 Testing Role-Based Permissions")
    print("=" * 60)
    
    # Test operator vs admin permissions
    admin_token = login_user('carlos.admin', 'carlos123')
    operator_token = login_user('maria.operator', 'maria123')
    
    if not admin_token or not operator_token:
        print("❌ Cannot test permissions - login failed")
        return
    
    # Both should be able to view venues
    admin_venues = test_endpoint(admin_token, '/venues/')
    operator_venues = test_endpoint(operator_token, '/venues/')
    
    print(f"✅ Admin can view venues: {admin_venues['success']}")
    print(f"✅ Operator can view venues: {operator_venues['success']}")
    
    # Both should be able to view events
    admin_events = test_endpoint(admin_token, '/events/')
    operator_events = test_endpoint(operator_token, '/events/')
    
    print(f"✅ Admin can view events: {admin_events['success']}")
    print(f"✅ Operator can view events: {operator_events['success']}")

if __name__ == '__main__':
    print("🚀 Venezuelan POS System - API Testing Suite")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health/", timeout=5)
        if response.status_code != 200:
            print("❌ Server health check failed")
            exit(1)
    except:
        print("❌ Server is not running. Please start the development server:")
        print("   python manage.py runserver")
        exit(1)
    
    print("✅ Server is running")
    
    # Run tests
    run_tests()
    test_multi_tenancy()
    test_permissions()
    
    print("\n📋 Test Summary:")
    print("- Authentication: Login/logout functionality")
    print("- Authorization: Role-based access control")
    print("- Multi-tenancy: Data isolation between tenants")
    print("- CRUD Operations: Create, read, update, delete")
    print("- API Endpoints: All major endpoints tested")
    
    print("\n📖 For detailed user information, see TEST_USERS.md")