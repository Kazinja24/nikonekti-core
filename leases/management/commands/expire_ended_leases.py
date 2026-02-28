from django.core.management.base import BaseCommand

from leases.cron import expire_ended_leases


class Command(BaseCommand):
    help = "Expire active leases whose end_date has passed"

    def handle(self, *args, **options):
        expire_ended_leases()
        self.stdout.write(self.style.SUCCESS("Lease expiration job completed successfully."))

