from django.core.management.base import BaseCommand

from offers.cron import expire_sent_offers


class Command(BaseCommand):
    help = "Expire sent rental offers that passed their expires_at timestamp"

    def handle(self, *args, **options):
        expire_sent_offers()
        self.stdout.write(self.style.SUCCESS("Sent offer expiration job completed successfully."))

