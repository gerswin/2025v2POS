"""
Celery configuration for Venezuelan POS System.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venezuelan_pos.settings')

app = Celery('venezuelan_pos')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule (for periodic tasks)
app.conf.beat_schedule = {
    'cleanup-expired-reservations': {
        'task': 'venezuelan_pos.apps.sales.tasks.cleanup_expired_reservations',
        'schedule': 300.0,  # Every 5 minutes
    },
    'sync-offline-blocks': {
        'task': 'venezuelan_pos.apps.offline.tasks.sync_offline_blocks',
        'schedule': 3600.0,  # Every hour
    },
}

app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')