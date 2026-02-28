from django.contrib import admin
from .models import Payment, RentInvoice, ListingPlan, ListingPaymentIntent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "amount", "status", "reference", "created_at")


@admin.register(ListingPlan)
class ListingPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "price", "duration_days", "is_featured", "is_active")
    list_filter = ("code", "is_featured", "is_active")


@admin.register(RentInvoice)
class RentInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "lease", "month", "amount", "due_date", "status", "paid_at")
    list_filter = ("status", "month")
    search_fields = ("lease__property__title", "lease__tenant__email", "lease__landlord__email")


@admin.register(ListingPaymentIntent)
class ListingPaymentIntentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "landlord",
        "plan",
        "amount",
        "status",
        "created_at",
        "expires_at",
    )
    list_filter = ("status", "plan__code", "created_at")
    search_fields = ("property__title", "landlord__email", "payment_reference")
