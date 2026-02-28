from django.core.management.base import BaseCommand

from payments.cron import expire_paid_property_listings


class Command(BaseCommand):
    help = "Expire paid listing intents and unpublish properties with expired listing validity"

    def handle(self, *args, **options):
        expire_paid_property_listings()
        self.stdout.write(self.style.SUCCESS("Expired paid property listings processed successfully."))

