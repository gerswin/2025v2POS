#!/usr/bin/env python
"""
Export Postman Collection for Venezuelan POS System

This script generates a comprehensive Postman collection with all API endpoints
and test users for easy API testing.

Usage:
    python export_postman_collection.py
"""

import json
import uuid
from datetime import datetime

def generate_postman_collection():
    """Generate a comprehensive Postman collection."""
    
    collection = {
        "info": {
            "name": "Venezuelan POS System - Complete API",
            "description": "Complete API collection for the Venezuelan POS System with test users and all endpoints",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": str(uuid.uuid4()),
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0
            }
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://127.0.0.1:8000",
                "type": "string"
            },
            {
                "key": "accessToken",
                "value": "",
                "type": "string"
            }
        ],
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{accessToken}}",
                    "type": "string"
                }
            ]
        },
        "item": []
    }
    
    # Authentication folder
    auth_folder = {
        "name": "🔐 Authentication",
        "item": [
            {
                "name": "Login - System Admin",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "username": "admin",
                            "password": "admin123"
                        }, indent=2)
                    },
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/auth/login/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "auth", "login", ""]
                    }
                },
                "event": [
                    {
                        "listen": "test",
                        "script": {
                            "exec": [
                                "if (pm.response.code === 200) {",
                                "    const response = pm.response.json();",
                                "    pm.collectionVariables.set('accessToken', response.access);",
                                "    pm.test('Login successful', () => {",
                                "        pm.expect(response.access).to.be.a('string');",
                                "    });",
                                "} else {",
                                "    pm.test('Login failed', () => {",
                                "        pm.expect.fail('Login request failed');",
                                "    });",
                                "}"
                            ],
                            "type": "text/javascript"
                        }
                    }
                ]
            },
            {
                "name": "Login - Carlos Admin (Eventos Caracas)",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "username": "carlos.admin",
                            "password": "carlos123"
                        }, indent=2)
                    },
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/auth/login/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "auth", "login", ""]
                    }
                },
                "event": [
                    {
                        "listen": "test",
                        "script": {
                            "exec": [
                                "if (pm.response.code === 200) {",
                                "    const response = pm.response.json();",
                                "    pm.collectionVariables.set('accessToken', response.access);",
                                "    pm.test('Login successful', () => {",
                                "        pm.expect(response.access).to.be.a('string');",
                                "        pm.expect(response.user.role).to.eql('tenant_admin');",
                                "    });",
                                "}"
                            ],
                            "type": "text/javascript"
                        }
                    }
                ]
            },
            {
                "name": "Login - Maria Operator (Eventos Caracas)",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "username": "maria.operator",
                            "password": "maria123"
                        }, indent=2)
                    },
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/auth/login/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "auth", "login", ""]
                    }
                },
                "event": [
                    {
                        "listen": "test",
                        "script": {
                            "exec": [
                                "if (pm.response.code === 200) {",
                                "    const response = pm.response.json();",
                                "    pm.collectionVariables.set('accessToken', response.access);",
                                "    pm.test('Login successful', () => {",
                                "        pm.expect(response.access).to.be.a('string');",
                                "        pm.expect(response.user.role).to.eql('event_operator');",
                                "    });",
                                "}"
                            ],
                            "type": "text/javascript"
                        }
                    }
                ]
            },
            {
                "name": "Get User Profile",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/auth/profile/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "auth", "profile", ""]
                    }
                }
            }
        ]
    }
    
    # Venues folder
    venues_folder = {
        "name": "🏢 Venues",
        "item": [
            {
                "name": "List All Venues",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/venues/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "venues", ""]
                    }
                }
            },
            {
                "name": "List Active Venues",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/venues/active/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "venues", "active", ""]
                    }
                }
            },
            {
                "name": "Search Venues",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/venues/?search=teatro",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "venues", ""],
                        "query": [
                            {
                                "key": "search",
                                "value": "teatro"
                            }
                        ]
                    }
                }
            },
            {
                "name": "Filter Venues by City",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/venues/?city=Caracas",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "venues", ""],
                        "query": [
                            {
                                "key": "city",
                                "value": "Caracas"
                            }
                        ]
                    }
                }
            },
            {
                "name": "Create New Venue",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "name": "Test Venue",
                            "address": "Test Address 123",
                            "city": "Caracas",
                            "state": "Distrito Capital",
                            "country": "Venezuela",
                            "capacity": 500,
                            "venue_type": "physical",
                            "contact_phone": "+58-212-555-9999",
                            "contact_email": "test@venue.com"
                        }, indent=2)
                    },
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/venues/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "venues", ""]
                    }
                }
            }
        ]
    }
    
    # Events folder
    events_folder = {
        "name": "🎭 Events",
        "item": [
            {
                "name": "List All Events",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", ""]
                    }
                }
            },
            {
                "name": "List Active Events",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/active/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", "active", ""]
                    }
                }
            },
            {
                "name": "List Upcoming Events",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/upcoming/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", "upcoming", ""]
                    }
                }
            },
            {
                "name": "List Events with Active Sales",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/sales_active/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", "sales_active", ""]
                    }
                }
            },
            {
                "name": "Search Events",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/?search=concierto",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", ""],
                        "query": [
                            {
                                "key": "search",
                                "value": "concierto"
                            }
                        ]
                    }
                }
            },
            {
                "name": "Create New Event",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "name": "Test Event",
                            "description": "A test event for API testing",
                            "event_type": "general_assignment",
                            "venue": "VENUE_UUID_HERE",
                            "start_date": "2025-12-31T20:00:00-04:00",
                            "end_date": "2025-12-31T23:00:00-04:00",
                            "sales_start_date": "2025-11-01T00:00:00-04:00",
                            "sales_end_date": "2025-12-31T18:00:00-04:00",
                            "event_configuration": {
                                "partial_payments_enabled": True,
                                "installment_plans_enabled": True,
                                "max_installments": 3,
                                "min_down_payment_percentage": "25.00"
                            }
                        }, indent=2)
                    },
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", ""]
                    }
                }
            },
            {
                "name": "Activate Event",
                "request": {
                    "method": "POST",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/EVENT_UUID_HERE/activate/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", "EVENT_UUID_HERE", "activate", ""]
                    }
                }
            },
            {
                "name": "Deactivate Event",
                "request": {
                    "method": "POST",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/v1/events/EVENT_UUID_HERE/deactivate/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "v1", "events", "EVENT_UUID_HERE", "deactivate", ""]
                    }
                }
            }
        ]
    }
    
    # System folder
    system_folder = {
        "name": "🔧 System",
        "item": [
            {
                "name": "Health Check",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/health/",
                        "host": ["{{baseUrl}}"],
                        "path": ["health", ""]
                    }
                }
            },
            {
                "name": "API Schema",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}/api/schema/",
                        "host": ["{{baseUrl}}"],
                        "path": ["api", "schema", ""]
                    }
                }
            }
        ]
    }
    
    # Add all folders to collection
    collection["item"] = [
        auth_folder,
        venues_folder,
        events_folder,
        system_folder
    ]
    
    return collection

def save_collection():
    """Save the Postman collection to a file."""
    collection = generate_postman_collection()
    
    filename = "postman/Venezuelan_POS_System_Complete.postman_collection.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Postman collection saved to: {filename}")
    print("\n📋 Collection includes:")
    print("  • Authentication endpoints with test users")
    print("  • Venue management (CRUD operations)")
    print("  • Event management (CRUD operations)")
    print("  • System health checks")
    print("  • Automatic token management")
    print("  • Test scripts for validation")
    
    print("\n📖 To use:")
    print("  1. Import the collection into Postman")
    print("  2. Start with any login request to get a token")
    print("  3. The token will be automatically set for other requests")
    print("  4. Test different users to see multi-tenancy in action")

if __name__ == '__main__':
    save_collection()