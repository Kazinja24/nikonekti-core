from datetime import date
from django.utils import timezone
from leases.models import Lease
from properties.models import PropertyImage
from .models import RentInvoice, ListingPaymentIntent
from audit.utils import log_action


def generate_monthly_invoices():
    today = date.today().replace(day=1)
    active_leases = Lease.objects.filter(status=Lease.Status.ACTIVE)

    for lease in active_leases:
        exists = RentInvoice.objects.filter(lease=lease, month=today).exists()
        if not exists:
            invoice = RentInvoice.objects.create(
                lease=lease,
                month=today,
                amount=lease.monthly_rent,
                due_date=today.replace(day=5),
            )
            try:
                log_action(
                    None,
                    "invoice.created.auto",
                    target=invoice,
                    data={"lease_id": str(lease.id), "invoice_id": str(invoice.id)},
                )
            except Exception:
                pass


def expire_paid_property_listings():
    now = timezone.now()
    expired_intents = ListingPaymentIntent.objects.filter(
        status__in=[
            ListingPaymentIntent.Status.CONFIRMED,
            ListingPaymentIntent.Status.OVERRIDDEN,
        ],
        expires_at__lte=now,
    ).select_related("property")

    for intent in expired_intents:
        intent.status = ListingPaymentIntent.Status.EXPIRED
        intent.save(update_fields=["status"])
        try:
            log_action(
                None,
                "listing_intent.expired.auto",
                target=intent,
                data={"intent_id": str(intent.id), "property_id": intent.property_id},
            )
        except Exception:
            pass

        property_obj = intent.property
        if property_obj.is_published:
            property_obj.is_published = False
            property_obj.published_at = None
            property_obj.save(update_fields=["is_published", "published_at"])

            for property_image in PropertyImage.objects.filter(property=property_obj):
                if property_image.image:
                    property_image.image.delete(save=False)
                property_image.delete()


def mark_overdue_invoices():
    today = date.today()
    overdue = RentInvoice.objects.filter(
        status=RentInvoice.Status.PENDING,
        due_date__lt=today,
    )
    for invoice in overdue:
        invoice.status = RentInvoice.Status.OVERDUE
        invoice.save(update_fields=["status"])
        try:
            log_action(
                None,
                "invoice.overdue.auto",
                target=invoice,
                data={"invoice_id": str(invoice.id), "lease_id": str(invoice.lease_id)},
            )
        except Exception:
            pass
