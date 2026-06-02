from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.access_control.services import bulk_update_access_status
from apps.bookings.services import send_due_and_grace_reminders


class Command(BaseCommand):
    help = "Update access status based on monthly bill payment and grace-period rules."

    def handle(self, *args, **options):
        reference_date = timezone.localdate()
        reminders_sent = send_due_and_grace_reminders(reference_date=reference_date)
        updated = bulk_update_access_status(reference_date=reference_date)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(updated)} student access records and sent {reminders_sent} billing reminders."
            )
        )
