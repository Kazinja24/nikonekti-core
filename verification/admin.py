from django.contrib import admin
from .models import LandlordVerification


@admin.register(LandlordVerification)
class LandlordVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "landlord",
        "status",
        "reviewed_by",
        "reviewed_at",
        "submitted_at",
    )
    list_filter = ("status", "submitted_at", "reviewed_at")
    search_fields = ("landlord__email", "landlord__full_name")
