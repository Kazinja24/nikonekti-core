from django.contrib import admin
from .models import PropertyReport, UserBlock


@admin.register(PropertyReport)
class PropertyReportAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "reporter", "status", "reviewed_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("property__title", "reporter__email", "reporter__full_name")


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked_user", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("blocker__email", "blocked_user__email")
