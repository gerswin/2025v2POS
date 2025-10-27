#!/usr/bin/env python
"""
Script para probar las interfaces web del Venezuelan POS System.
"""

import requests
from requests.sessions import Session

# Configuración
BASE_URL = "http://127.0.0.1:8000"

def test_web_interfaces():
    """Probar las interfaces web con autenticación."""
    
    print("🧪 Probando Interfaces Web del Venezuelan POS System")
    print("=" * 60)
    
    # Crear sesión para mantener cookies
    session = Session()
    
    # 1. Probar página de login
    print("\n1. 📋 Probando página de login...")
    login_url = f"{BASE_URL}/accounts/login/"
    response = session.get(login_url)
    
    if response.status_code == 200:
        print(f"   ✅ Login page: {response.status_code}")
    else:
        print(f"   ❌ Login page: {response.status_code}")
        return
    
    # 2. Obtener CSRF token
    csrf_token = None
    if 'csrftoken' in session.cookies:
        csrf_token = session.cookies['csrftoken']
    else:
        # Buscar en el HTML
        import re
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]*)"', response.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
    
    if not csrf_token:
        print("   ❌ No se pudo obtener CSRF token")
        return
    
    print(f"   ✅ CSRF token obtenido")
    
    # 3. Intentar login
    print("\n2. 🔐 Probando autenticación...")
    login_data = {
        'username': 'carlos.admin',
        'password': 'carlos123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    response = session.post(login_url, data=login_data)
    
    if response.status_code == 302:  # Redirección después del login
        print(f"   ✅ Login exitoso: {response.status_code}")
    else:
        print(f"   ❌ Login falló: {response.status_code}")
        return
    
    # 4. Probar dashboard
    print("\n3. 📊 Probando dashboard...")
    dashboard_url = f"{BASE_URL}/"
    response = session.get(dashboard_url)
    
    if response.status_code == 200:
        print(f"   ✅ Dashboard: {response.status_code}")
        if "Dashboard" in response.text:
            print("   ✅ Contenido del dashboard cargado")
    else:
        print(f"   ❌ Dashboard: {response.status_code}")
    
    # 5. Probar lista de venues
    print("\n4. 🏢 Probando lista de venues...")
    venues_url = f"{BASE_URL}/venues/"
    response = session.get(venues_url)
    
    if response.status_code == 200:
        print(f"   ✅ Lista de venues: {response.status_code}")
        if "Venues" in response.text:
            print("   ✅ Contenido de venues cargado")
    else:
        print(f"   ❌ Lista de venues: {response.status_code}")
    
    # 6. Probar formulario de crear venue
    print("\n5. ➕ Probando formulario de crear venue...")
    create_venue_url = f"{BASE_URL}/venues/create/"
    response = session.get(create_venue_url)
    
    if response.status_code == 200:
        print(f"   ✅ Crear venue: {response.status_code}")
        if "Nueva Venue" in response.text:
            print("   ✅ Formulario de crear venue cargado")
    else:
        print(f"   ❌ Crear venue: {response.status_code}")
    
    # 7. Probar lista de eventos
    print("\n6. 🎭 Probando lista de eventos...")
    events_url = f"{BASE_URL}/events/"
    response = session.get(events_url)
    
    if response.status_code == 200:
        print(f"   ✅ Lista de eventos: {response.status_code}")
        if "Eventos" in response.text or "eventos" in response.text:
            print("   ✅ Contenido de eventos cargado")
    else:
        print(f"   ❌ Lista de eventos: {response.status_code}")
    
    # 8. Probar formulario de crear evento
    print("\n7. ➕ Probando formulario de crear evento...")
    create_event_url = f"{BASE_URL}/events/create/"
    response = session.get(create_event_url)
    
    if response.status_code == 200:
        print(f"   ✅ Crear evento: {response.status_code}")
        if "Nuevo Evento" in response.text or "evento" in response.text:
            print("   ✅ Formulario de crear evento cargado")
    else:
        print(f"   ❌ Crear evento: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("🎉 Pruebas de interfaces web completadas")
    print("\n📋 URLs principales:")
    print(f"   Dashboard:     {BASE_URL}/")
    print(f"   Login:         {BASE_URL}/accounts/login/")
    print(f"   Venues:        {BASE_URL}/venues/")
    print(f"   Eventos:       {BASE_URL}/events/")
    print(f"   Admin:         {BASE_URL}/admin/")


if __name__ == '__main__':
    try:
        # Verificar que el servidor esté funcionando
        response = requests.get(f"{BASE_URL}/health/", timeout=5)
        print("✅ Servidor funcionando")
    except:
        print("❌ Servidor no está funcionando. Inicia el servidor con:")
        print("   python manage.py runserver")
        exit(1)
    
    test_web_interfaces()