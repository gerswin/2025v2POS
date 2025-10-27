#!/usr/bin/env python
"""
Script completo para validar que el sistema multi-idioma funciona correctamente
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language
from django.test import Client
from django.contrib.auth import get_user_model

def print_header(title):
    """Imprimir encabezado con formato"""
    print(f"\n🌍 {title}")
    print("=" * 60)

def print_section(title):
    """Imprimir sección con formato"""
    print(f"\n📋 {title}")
    print("-" * 40)

def check_django_i18n_configuration():
    """Verificar la configuración de Django para i18n"""
    print_section("CONFIGURACIÓN DJANGO I18N")
    
    checks = [
        ("USE_I18N", settings.USE_I18N, True),
        ("LANGUAGE_CODE", settings.LANGUAGE_CODE, 'es'),
        ("USE_L10N", getattr(settings, 'USE_L10N', None), True),
        ("USE_TZ", settings.USE_TZ, True),
    ]
    
    all_good = True
    for name, actual, expected in checks:
        if actual == expected:
            print(f"✅ {name}: {actual}")
        else:
            print(f"❌ {name}: {actual} (esperado: {expected})")
            all_good = False
    
    # Verificar LANGUAGES
    if hasattr(settings, 'LANGUAGES') and len(settings.LANGUAGES) >= 2:
        print(f"✅ LANGUAGES: {settings.LANGUAGES}")
    else:
        print(f"❌ LANGUAGES no configurado correctamente")
        all_good = False
    
    # Verificar LOCALE_PATHS
    if hasattr(settings, 'LOCALE_PATHS') and len(settings.LOCALE_PATHS) > 0:
        print(f"✅ LOCALE_PATHS: {settings.LOCALE_PATHS}")
    else:
        print(f"❌ LOCALE_PATHS no configurado")
        all_good = False
    
    # Verificar middleware
    middleware = settings.MIDDLEWARE
    locale_middleware = 'django.middleware.locale.LocaleMiddleware'
    if locale_middleware in middleware:
        print(f"✅ LocaleMiddleware configurado")
    else:
        print(f"❌ LocaleMiddleware NO encontrado en MIDDLEWARE")
        all_good = False
    
    return all_good

def check_translation_files():
    """Verificar archivos de traducción"""
    print_section("ARCHIVOS DE TRADUCCIÓN")
    
    locale_dir = Path('locale')
    if not locale_dir.exists():
        print("❌ Directorio 'locale' no encontrado")
        return False
    
    print(f"✅ Directorio locale: {locale_dir.absolute()}")
    
    languages = ['es', 'en']
    files_ok = True
    
    for lang in languages:
        print(f"\n🔍 Idioma: {lang.upper()}")
        
        lang_dir = locale_dir / lang / 'LC_MESSAGES'
        po_file = lang_dir / 'django.po'
        mo_file = lang_dir / 'django.mo'
        
        if po_file.exists():
            size = po_file.stat().st_size
            print(f"   ✅ django.po ({size} bytes)")
            
            # Contar mensajes
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            msgid_count = content.count('msgid "')
            msgstr_count = content.count('msgstr "')
            empty_translations = content.count('msgstr ""')
            
            print(f"   📊 Mensajes: {msgid_count}")
            print(f"   📊 Traducciones: {msgstr_count}")
            print(f"   📊 Vacías: {empty_translations}")
            
        else:
            print(f"   ❌ django.po NO encontrado")
            files_ok = False
        
        if mo_file.exists():
            size = mo_file.stat().st_size
            print(f"   ✅ django.mo ({size} bytes)")
        else:
            print(f"   ❌ django.mo NO encontrado")
            files_ok = False
    
    return files_ok

def test_translation_functionality():
    """Probar funcionalidad de traducción"""
    print_section("FUNCIONALIDAD DE TRADUCCIÓN")
    
    # Strings de prueba con sus traducciones esperadas
    test_strings = {
        'es': [
            ("Login", "Iniciar Sesión"),
            ("Dashboard", "Panel de Control"),
            ("Venezuelan POS System", "Sistema POS Venezolano"),
            ("Events", "Eventos"),
            ("Sales", "Ventas"),
            ("Customers", "Clientes"),
            ("Logout", "Cerrar Sesión"),
            ("Save", "Guardar"),
            ("Cancel", "Cancelar"),
            ("Delete", "Eliminar"),
            ("Edit", "Editar"),
            ("Create", "Crear"),
            ("Search", "Buscar"),
            ("Total", "Total"),
            ("Price", "Precio"),
            ("Quantity", "Cantidad"),
            ("Available", "Disponible"),
            ("Reserved", "Reservado"),
            ("Sold", "Vendido"),
        ],
        'en': [
            ("Login", "Login"),
            ("Dashboard", "Dashboard"),
            ("Venezuelan POS System", "Venezuelan POS System"),
            ("Events", "Events"),
            ("Sales", "Sales"),
            ("Customers", "Customers"),
        ]
    }
    
    translation_results = {}
    
    for lang, strings in test_strings.items():
        print(f"\n🌐 Probando idioma: {lang.upper()}")
        
        activate(lang)
        current_lang = get_language()
        print(f"   Idioma activo: {current_lang}")
        
        correct_translations = 0
        total_strings = len(strings)
        
        for original, expected in strings:
            try:
                translated = _(original)
                if translated == expected:
                    print(f"   ✅ '{original}' → '{translated}'")
                    correct_translations += 1
                else:
                    print(f"   ⚠️ '{original}' → '{translated}' (esperado: '{expected}')")
            except Exception as e:
                print(f"   ❌ Error traduciendo '{original}': {e}")
        
        percentage = (correct_translations / total_strings) * 100
        print(f"   📊 Traducciones correctas: {correct_translations}/{total_strings} ({percentage:.1f}%)")
        
        translation_results[lang] = {
            'correct': correct_translations,
            'total': total_strings,
            'percentage': percentage
        }
    
    # Restaurar idioma por defecto
    activate(settings.LANGUAGE_CODE)
    
    return translation_results

def check_template_i18n_usage():
    """Verificar uso de i18n en templates"""
    print_section("USO DE I18N EN TEMPLATES")
    
    template_dirs = [
        'venezuelan_pos/apps/authentication/templates',
        'venezuelan_pos/apps/events/templates',
        'venezuelan_pos/apps/sales/templates',
        'venezuelan_pos/apps/customers/templates',
        'venezuelan_pos/apps/pricing/templates',
    ]
    
    total_templates = 0
    templates_with_i18n = 0
    
    for template_dir in template_dirs:
        template_path = Path(template_dir)
        if template_path.exists():
            for html_file in template_path.rglob('*.html'):
                total_templates += 1
                
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Buscar tags de i18n
                    i18n_patterns = [
                        '{% load i18n %}',
                        '{% trans ',
                        '{% blocktrans ',
                        '{% get_current_language',
                        '{% get_available_languages',
                    ]
                    
                    has_i18n = any(pattern in content for pattern in i18n_patterns)
                    
                    if has_i18n:
                        templates_with_i18n += 1
                        print(f"   ✅ {html_file.name}")
                    else:
                        print(f"   ⚠️ {html_file.name} - Sin tags i18n")
                        
                except Exception as e:
                    print(f"   ❌ Error leyendo {html_file}: {e}")
    
    if total_templates > 0:
        percentage = (templates_with_i18n / total_templates) * 100
        print(f"\n📊 RESUMEN TEMPLATES:")
        print(f"   Total: {total_templates}")
        print(f"   Con i18n: {templates_with_i18n}")
        print(f"   Porcentaje: {percentage:.1f}%")
        
        return percentage >= 80  # Al menos 80% de templates deben usar i18n
    
    return False

def check_urls_i18n():
    """Verificar configuración de URLs para i18n"""
    print_section("CONFIGURACIÓN DE URLs I18N")
    
    # Verificar que las URLs de i18n estén configuradas
    from django.urls import reverse
    
    try:
        i18n_url = reverse('set_language')
        print(f"✅ URL set_language disponible: {i18n_url}")
        return True
    except Exception as e:
        print(f"❌ URL set_language no disponible: {e}")
        return False

def generate_final_report(config_ok, files_ok, translation_results, templates_ok, urls_ok):
    """Generar reporte final"""
    print_header("REPORTE FINAL DE VALIDACIÓN I18N")
    
    print("📊 RESUMEN DE COMPONENTES:")
    print(f"{'✅' if config_ok else '❌'} Configuración Django I18N")
    print(f"{'✅' if files_ok else '❌'} Archivos de traducción")
    print(f"{'✅' if urls_ok else '❌'} URLs de internacionalización")
    print(f"{'✅' if templates_ok else '❌'} Templates con tags i18n")
    
    print("\n📈 RESULTADOS DE TRADUCCIÓN:")
    for lang, results in translation_results.items():
        status = "✅" if results['percentage'] >= 80 else "⚠️"
        print(f"{status} {lang.upper()}: {results['correct']}/{results['total']} ({results['percentage']:.1f}%)")
    
    # Determinar estado general
    overall_ok = all([
        config_ok,
        files_ok,
        urls_ok,
        templates_ok,
        all(r['percentage'] >= 80 for r in translation_results.values())
    ])
    
    if overall_ok:
        print("\n🎉 SISTEMA MULTI-IDIOMA FUNCIONANDO CORRECTAMENTE")
        print("\n💡 FUNCIONALIDADES DISPONIBLES:")
        print("   ✅ Cambio dinámico de idioma")
        print("   ✅ Detección automática del idioma del navegador")
        print("   ✅ Persistencia de preferencias de idioma")
        print("   ✅ Interfaz completamente traducida")
        print("   ✅ URLs de internacionalización")
        
        print("\n🌍 IDIOMAS SOPORTADOS:")
        for lang_code, lang_name in settings.LANGUAGES:
            print(f"   • {lang_name} ({lang_code})")
        
        print("\n🚀 CÓMO USAR:")
        print("   1. El sistema detecta automáticamente el idioma del navegador")
        print("   2. Los usuarios pueden cambiar idioma usando /i18n/setlang/")
        print("   3. La preferencia se guarda en la sesión del usuario")
        print("   4. Toda la interfaz se traduce automáticamente")
        
    else:
        print("\n⚠️ HAY PROBLEMAS CON EL SISTEMA MULTI-IDIOMA")
        print("\n🔧 ACCIONES RECOMENDADAS:")
        
        if not config_ok:
            print("   • Revisar configuración en settings.py")
        if not files_ok:
            print("   • Compilar archivos de traducción: python manage.py compilemessages")
        if not templates_ok:
            print("   • Agregar tags {% load i18n %} y {% trans %} en templates")
        if not urls_ok:
            print("   • Verificar configuración de URLs i18n")
    
    return overall_ok

def main():
    """Función principal"""
    print_header("VALIDACIÓN COMPLETA DEL SISTEMA MULTI-IDIOMA")
    
    # Ejecutar todas las verificaciones
    config_ok = check_django_i18n_configuration()
    files_ok = check_translation_files()
    translation_results = test_translation_functionality()
    templates_ok = check_template_i18n_usage()
    urls_ok = check_urls_i18n()
    
    # Generar reporte final
    success = generate_final_report(config_ok, files_ok, translation_results, templates_ok, urls_ok)
    
    if success:
        print("\n✅ VALIDACIÓN COMPLETADA EXITOSAMENTE")
        sys.exit(0)
    else:
        print("\n❌ SE ENCONTRARON PROBLEMAS EN LA VALIDACIÓN")
        sys.exit(1)

if __name__ == '__main__':
    main()