#!/usr/bin/env python
"""
Script para debuggear las URLs disponibles.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from django.urls import get_resolver
from django.conf import settings

def show_urls(urlpatterns, prefix=''):
    """Mostrar todas las URLs disponibles."""
    for pattern in urlpatterns:
        if hasattr(pattern, 'url_patterns'):
            # Es un include
            new_prefix = prefix + str(pattern.pattern)
            show_urls(pattern.url_patterns, new_prefix)
        else:
            # Es una URL individual
            url = prefix + str(pattern.pattern)
            name = getattr(pattern, 'name', 'No name')
            print(f"  {url} -> {name}")

def debug_urls():
    """Debuggear las URLs del proyecto."""
    
    print("🔍 DEBUGGEANDO URLs DEL PROYECTO")
    print("=" * 60)
    
    resolver = get_resolver()
    
    print("\\n📋 TODAS LAS URLs DISPONIBLES:")
    print("-" * 40)
    
    show_urls(resolver.url_patterns)
    
    print("\\n🗺️ BUSCANDO URLs RELACIONADAS CON ZONES:")
    print("-" * 40)
    
    # Buscar URLs específicas de zones
    for pattern in resolver.url_patterns:
        pattern_str = str(pattern.pattern)
        if 'zones' in pattern_str.lower():
            print(f"✅ Encontrada: {pattern_str}")
            if hasattr(pattern, 'url_patterns'):
                print("   Sub-URLs:")
                for sub_pattern in pattern.url_patterns:
                    sub_url = str(sub_pattern.pattern)
                    sub_name = getattr(sub_pattern, 'name', 'No name')
                    print(f"     {pattern_str}{sub_url} -> {sub_name}")
    
    print("\\n🔧 INFORMACIÓN DE DEBUG:")
    print("-" * 30)
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ROOT_URLCONF: {settings.ROOT_URLCONF}")

if __name__ == '__main__':
    debug_urls()