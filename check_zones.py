#!/usr/bin/env python
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')
django.setup()

from venezuelan_pos.apps.events.models import Event

event = Event.objects.filter(name='Concierto de Prueba').first()
if event:
    print('Zonas disponibles:')
    for zone in event.zones.all():
        print(f'  - {zone.name} ({zone.zone_type}) - ${zone.base_price}')
else:
    print('Evento no encontrado')