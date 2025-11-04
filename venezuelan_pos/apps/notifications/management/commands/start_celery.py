"""
Management command to start Celery worker and beat scheduler.
"""

from django.core.management.base import BaseCommand
import subprocess
import sys
import os


class Command(BaseCommand):
    help = 'Start Celery worker and beat scheduler for notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-only',
            action='store_true',
            help='Start only the worker, not the beat scheduler',
        )
        parser.add_argument(
            '--beat-only',
            action='store_true',
            help='Start only the beat scheduler, not the worker',
        )
        parser.add_argument(
            '--concurrency',
            type=int,
            default=4,
            help='Number of concurrent worker processes',
        )
        parser.add_argument(
            '--loglevel',
            default='info',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Logging level',
        )

    def handle(self, *args, **options):
        if options['beat_only']:
            self.start_beat(options['loglevel'])
        elif options['worker_only']:
            self.start_worker(options['concurrency'], options['loglevel'])
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    'Starting both Celery worker and beat scheduler...\n'
                    'Run with --worker-only or --beat-only to start individually.'
                )
            )
            self.stdout.write(
                'To start manually:\n'
                '  Worker: celery -A venezuelan_pos worker --loglevel=info\n'
                '  Beat: celery -A venezuelan_pos beat --loglevel=info\n'
                '  Flower: celery -A venezuelan_pos flower\n'
            )

    def start_worker(self, concurrency, loglevel):
        """Start Celery worker."""
        self.stdout.write(f'Starting Celery worker with {concurrency} processes...')
        
        cmd = [
            'celery', '-A', 'venezuelan_pos', 'worker',
            '--loglevel', loglevel,
            '--concurrency', str(concurrency),
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(f'Failed to start Celery worker: {e}')
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write('\nStopping Celery worker...')

    def start_beat(self, loglevel):
        """Start Celery beat scheduler."""
        self.stdout.write('Starting Celery beat scheduler...')
        
        cmd = [
            'celery', '-A', 'venezuelan_pos', 'beat',
            '--loglevel', loglevel,
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(f'Failed to start Celery beat: {e}')
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write('\nStopping Celery beat...')