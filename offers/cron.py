from django.utils import timezone

from audit.utils import log_action
from .models import RentalOffer


def expire_sent_offers():
    now = timezone.now()
    offers = RentalOffer.objects.filter(
        status=RentalOffer.Status.SENT,
        expires_at__isnull=False,
        expires_at__lte=now,
    )
    for offer in offers:
        offer.status = RentalOffer.Status.EXPIRED
        offer.responded_at = now
        offer.save(update_fields=["status", "responded_at"])
        try:
            log_action(
                None,
                "offer.expired.auto",
                target=offer,
                data={"offer_id": str(offer.id), "reason": "expires_at reached"},
            )
        except Exception:
            pass

