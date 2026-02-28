from django.contrib import admin
from .models import RentalApplication


@admin.register(RentalApplication)
class RentalApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "property",
        "status",
        "created_at",
        "decided_at",
    )
    list_filter = ("status", "created_at", "decided_at")
    search_fields = ("tenant__email", "tenant__full_name", "property__title")
