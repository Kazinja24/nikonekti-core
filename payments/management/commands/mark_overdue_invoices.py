from django.core.management.base import BaseCommand

from payments.cron import mark_overdue_invoices


class Command(BaseCommand):
    help = "Mark pending rent invoices as overdue when their due date has passed"

    def handle(self, *args, **options):
        mark_overdue_invoices()
        self.stdout.write(self.style.SUCCESS("Overdue invoice marking completed successfully."))

