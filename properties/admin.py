from django.contrib import admin
from .models import Property, PropertyImage
from .models import Feature, PropertyReviewLog
from .models import Feature


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "status",
        "verification_status",
        "is_published",
        "listing_status",
        "created_at",
    )
    list_filter = ("status", "verification_status", "is_published", "created_at")
    search_fields = ("title", "owner__email", "owner__full_name")


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "is_cover", "order", "uploaded_at")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")


@admin.register(PropertyReviewLog)
class PropertyReviewLogAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "action", "admin", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("property__title", "admin__email", "notes")
