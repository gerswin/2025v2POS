"""
Management command to start Flower for Celery monitoring.
"""

from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = 'Start Flower for Celery task monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=5555,
            help='Port to run Flower on (default: 5555)',
        )
        parser.add_argument(
            '--address',
            default='127.0.0.1',
            help='Address to bind Flower to (default: 127.0.0.1)',
        )

    def handle(self, *args, **options):
        port = options['port']
        address = options['address']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting Flower on http://{address}:{port}'
            )
        )
        
        cmd = [
            'celery', '-A', 'venezuelan_pos', 'flower',
            '--address', address,
            '--port', str(port),
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(f'Failed to start Flower: {e}')
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write('\nStopping Flower...')