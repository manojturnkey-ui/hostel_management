from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.services import generate_current_month_bills


class Command(BaseCommand):
    help = "Generate monthly rent bills for all active confirmed bookings."

    def handle(self, *args, **options):
        generated = generate_current_month_bills(reference_date=timezone.localdate())
        self.stdout.write(self.style.SUCCESS(f"Generated {len(generated)} monthly bills."))
