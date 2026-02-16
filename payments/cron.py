from datetime import date
from leases.models import Lease
from .models import RentInvoice


def generate_monthly_invoices():
    today = date.today().replace(day=1)
    active_leases = Lease.objects.filter(status="ACTIVE")

    for lease in active_leases:
        exists = RentInvoice.objects.filter(lease=lease, month=today).exists()
        if not exists:
            RentInvoice.objects.create(
                lease=lease,
                month=today,
                amount=lease.monthly_rent,
                due_date=today.replace(day=5),
            )
