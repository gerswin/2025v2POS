from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from venezuelan_pos.apps.tenants.models import Tenant

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an admin user for the Venezuelan POS system'
    
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Username for admin user')
        parser.add_argument('--email', type=str, default='admin@example.com', help='Email for admin user')
        parser.add_argument('--password', type=str, default='admin123', help='Password for admin user')
        parser.add_argument('--create-tenant', action='store_true', help='Create a demo tenant')
    
    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
            return
        
        # Create admin user
        admin_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=User.Role.ADMIN_USER,
            is_staff=True,
            is_superuser=True,
            first_name='System',
            last_name='Administrator'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user "{username}"')
        )
        
        # Create demo tenant if requested
        if options['create_tenant']:
            tenant, created = Tenant.objects.get_or_create(
                slug='demo-tenant',
                defaults={
                    'name': 'Demo Tenant',
                    'contact_email': 'demo@example.com',
                    'fiscal_series_prefix': 'DT',
                    'configuration': {
                        'currency': 'USD',
                        'timezone': 'America/Caracas',
                        'fiscal_year_start': '01-01'
                    }
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS('Successfully created demo tenant')
                )
                
                # Create a tenant admin user
                tenant_admin = User.objects.create_user(
                    username='tenant_admin',
                    email='tenant_admin@demo.com',
                    password='tenant123',
                    role=User.Role.TENANT_ADMIN,
                    tenant=tenant,
                    is_staff=True,
                    first_name='Tenant',
                    last_name='Administrator'
                )
                
                self.stdout.write(
                    self.style.SUCCESS('Successfully created tenant admin user')
                )
                
                # Create an event operator
                event_operator = User.objects.create_user(
                    username='operator',
                    email='operator@demo.com',
                    password='operator123',
                    role=User.Role.EVENT_OPERATOR,
                    tenant=tenant,
                    first_name='Event',
                    last_name='Operator'
                )
                
                self.stdout.write(
                    self.style.SUCCESS('Successfully created event operator user')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Demo tenant already exists')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\nSetup complete! You can now:')
        )
        self.stdout.write(f'1. Login to admin at /admin/ with username: {username}')
        if options['create_tenant']:
            self.stdout.write('2. Login as tenant admin with username: tenant_admin')
            self.stdout.write('3. Login as operator with username: operator')
        self.stdout.write('4. Access API docs at /api/docs/')
        self.stdout.write('5. Test authentication at /api/v1/auth/login/')