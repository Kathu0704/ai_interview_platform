from django.apps import AppConfig


class AdminpanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminpanel'

    def ready(self):
        """
        Ensure the platform has exactly one initial Admin account in production,
        without exposing any admin registration page.

        Runs after migrations via the post_migrate signal.
        """
        from django.db.models.signals import post_migrate

        def _ensure_default_admin(sender, **kwargs):
            try:
                import os
                import hashlib
                from .models import Admin

                default_email = os.getenv("DEFAULT_ADMIN_EMAIL", "Admin@mock.com")
                default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@2025")

                # Create the default admin only if none exist yet.
                if not Admin.objects.exists():
                    Admin.objects.create(
                        email=default_email.strip(),
                        password=hashlib.sha256(default_password.encode()).hexdigest(),
                        name="System Administrator",
                        is_active=True,
                    )
            except Exception:
                # Never crash app startup because of this helper.
                # If DB isn't ready yet, migrations will run and post_migrate will try again.
                return

        post_migrate.connect(_ensure_default_admin, sender=self, dispatch_uid="adminpanel.ensure_default_admin")