from django.contrib import admin

from .models import RentalOffer


@admin.register(RentalOffer)
class RentalOfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "tenant",
        "landlord",
        "status",
        "monthly_rent",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("property__title", "tenant__email", "landlord__email")

