"""
Django management command to set up development environment.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Set up development environment with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations',
        )
        parser.add_argument(
            '--skip-superuser',
            action='store_true',
            help='Skip creating superuser',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Setting up Venezuelan POS development environment...')
        )

        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS('✓ Database connection successful'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Database connection failed: {e}')
            )
            return

        # Run migrations
        if not options['skip_migrations']:
            self.stdout.write('Running migrations...')
            call_command('migrate', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✓ Migrations completed'))

        # Collect static files
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', verbosity=0, interactive=False)
        self.stdout.write(self.style.SUCCESS('✓ Static files collected'))

        # Create superuser
        if not options['skip_superuser']:
            self.stdout.write('Creating superuser...')
            try:
                call_command(
                    'createsuperuser',
                    username='admin',
                    email='admin@venezuelanpos.com',
                    interactive=False
                )
                self.stdout.write(self.style.SUCCESS('✓ Superuser created (admin/admin)'))
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Superuser creation skipped: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Development environment setup complete!')
        )
        self.stdout.write('You can now run: python manage.py runserver')
        self.stdout.write('Admin panel: http://127.0.0.1:8000/admin/')
        self.stdout.write('API docs: http://127.0.0.1:8000/api/docs/')