from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from config.settings import env


class Command(BaseCommand):
    help = "Create or update a default panel admin from environment variables."

    def handle(self, *args, **options):
        email = (env("PANEL_ADMIN_EMAIL", "") or "").strip()
        password = env("PANEL_ADMIN_PASSWORD", "") or ""
        username = (env("PANEL_ADMIN_USERNAME", "") or email).strip()
        display_name = (env("PANEL_ADMIN_NAME", "Panel Admin") or "Panel Admin").strip()

        if not email or not password or not username:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped panel admin bootstrap. Set PANEL_ADMIN_EMAIL, PANEL_ADMIN_USERNAME, and PANEL_ADMIN_PASSWORD."
                )
            )
            return

        User = get_user_model()
        user = User.objects.filter(username__iexact=username).first() or User.objects.filter(email__iexact=email).first()
        created = user is None

        if created:
            user = User(username=username)

        user.email = email
        user.display_name = display_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} panel admin: {username}"))
