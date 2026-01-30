from django.core.management.base import BaseCommand
from adminpanel.models import Admin
import hashlib

class Command(BaseCommand):
    help = 'Create admin user with specified credentials'

    def handle(self, *args, **options):
        email = 'Admin@mock.com'
        password = 'Admin@2003'
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Check if admin already exists
        if Admin.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin with email {email} already exists!')
            )
            return
        
        # Create admin user
        admin = Admin.objects.create(
            email=email,
            password=hashed_password,
            name='System Administrator',
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user: {admin.email}')
        )
