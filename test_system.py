#!/usr/bin/env python
"""
Script de prueba para validar que el sistema Venezuelan POS funciona correctamente.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "venezuelan_pos.settings")
    django.setup()
    
    print("🚀 Venezuelan POS System - Validation Test")
    print("=" * 50)
    
    # Test 1: Database Connection
    print("1. Testing database connection...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("   ✅ Database connection successful")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Test 2: Cache Configuration
    print("2. Testing cache configuration...")
    try:
        from django.core.cache import cache
        cache.set('test_key', 'test_value', 30)
        value = cache.get('test_key')
        if value == 'test_value':
            print("   ✅ Cache working correctly")
        else:
            print("   ⚠️  Cache not working as expected")
    except Exception as e:
        print(f"   ⚠️  Cache error (using dummy cache): {e}")
    
    # Test 3: Installed Apps
    print("3. Testing installed applications...")
    required_apps = [
        'django.contrib.admin',
        'django.contrib.auth',
        'rest_framework',
        'drf_spectacular',
        'django_extensions',
        'silk',
    ]
    
    for app in required_apps:
        if app in settings.INSTALLED_APPS:
            print(f"   ✅ {app}")
        else:
            print(f"   ❌ {app} not found")
    
    # Test 4: Middleware Configuration
    print("4. Testing middleware configuration...")
    required_middleware = [
        'django.middleware.security.SecurityMiddleware',
        'corsheaders.middleware.CorsMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ]
    
    for middleware in required_middleware:
        if middleware in settings.MIDDLEWARE:
            print(f"   ✅ {middleware}")
        else:
            print(f"   ❌ {middleware} not found")
    
    # Test 5: REST Framework Configuration
    print("5. Testing REST Framework configuration...")
    try:
        rest_config = settings.REST_FRAMEWORK
        if 'rest_framework_simplejwt.authentication.JWTAuthentication' in rest_config.get('DEFAULT_AUTHENTICATION_CLASSES', []):
            print("   ✅ JWT Authentication configured")
        else:
            print("   ❌ JWT Authentication not configured")
            
        if 'drf_spectacular.openapi.AutoSchema' in rest_config.get('DEFAULT_SCHEMA_CLASS', ''):
            print("   ✅ API Documentation configured")
        else:
            print("   ❌ API Documentation not configured")
    except Exception as e:
        print(f"   ❌ REST Framework configuration error: {e}")
    
    # Test 6: Celery Configuration
    print("6. Testing Celery configuration...")
    try:
        broker_url = settings.CELERY_BROKER_URL
        result_backend = settings.CELERY_RESULT_BACKEND
        if broker_url and result_backend:
            print("   ✅ Celery configuration found")
        else:
            print("   ❌ Celery configuration incomplete")
    except Exception as e:
        print(f"   ❌ Celery configuration error: {e}")
    
    # Test 7: Security Settings
    print("7. Testing security settings...")
    security_checks = [
        ('SECURE_BROWSER_XSS_FILTER', True),
        ('SECURE_CONTENT_TYPE_NOSNIFF', True),
        ('X_FRAME_OPTIONS', 'DENY'),
    ]
    
    for setting_name, expected_value in security_checks:
        actual_value = getattr(settings, setting_name, None)
        if actual_value == expected_value:
            print(f"   ✅ {setting_name}")
        else:
            print(f"   ⚠️  {setting_name}: {actual_value} (expected: {expected_value})")
    
    # Test 8: File Structure
    print("8. Testing project structure...")
    required_dirs = [
        'venezuelan_pos/apps',
        'logs',
        'static',
        'media',
        'postman',
    ]
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ not found")
    
    # Test 9: Configuration Files
    print("9. Testing configuration files...")
    config_files = [
        'requirements.txt',
        '.env',
        '.env.example',
        'pytest.ini',
        'gunicorn.conf.py',
        'Dockerfile',
        'docker-compose.yml',
    ]
    
    for file_name in config_files:
        if os.path.exists(file_name):
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} not found")
    
    print("\n" + "=" * 50)
    print("🎉 System validation completed!")
    print("\nNext steps:")
    print("1. Run: python manage.py runserver")
    print("2. Visit: http://127.0.0.1:8000/admin/")
    print("3. API Docs: http://127.0.0.1:8000/api/docs/")
    print("4. Import Postman collection from postman/ directory")
    print("\n📚 Documentation:")
    print("- Postman collection: postman/README.md")
    print("- Requirements: .kiro/specs/venezuelan-pos-system/requirements.md")
    print("- Design: .kiro/specs/venezuelan-pos-system/design.md")
    print("- Tasks: .kiro/specs/venezuelan-pos-system/tasks.md")