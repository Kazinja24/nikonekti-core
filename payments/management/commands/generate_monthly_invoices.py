from django.core.management.base import BaseCommand

from payments.cron import generate_monthly_invoices


class Command(BaseCommand):
    help = "Generate monthly rent invoices for active leases"

    def handle(self, *args, **options):
        generate_monthly_invoices()
        self.stdout.write(self.style.SUCCESS("Monthly invoices generated successfully."))
