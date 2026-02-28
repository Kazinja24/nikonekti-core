from datetime import date

from audit.utils import log_action
from .models import Lease


def expire_ended_leases():
    today = date.today()
    leases = Lease.objects.filter(status=Lease.Status.ACTIVE, end_date__lt=today).select_related("property")
    for lease in leases:
        lease.status = Lease.Status.EXPIRED
        lease.save(update_fields=["status"])

        property_obj = lease.property
        active_for_property = Lease.objects.filter(
            property=property_obj,
            status__in=[Lease.Status.PENDING, Lease.Status.ACTIVE],
        ).exists()
        if not active_for_property and property_obj.status == "rented":
            property_obj.status = "available"
            property_obj.save(update_fields=["status"])

        try:
            log_action(
                None,
                "lease.expired.auto",
                target=lease,
                data={"lease_id": str(lease.id), "reason": "end_date passed"},
            )
        except Exception:
            pass

