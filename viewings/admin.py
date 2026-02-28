from django.contrib import admin
from .models import Viewing


@admin.register(Viewing)
class ViewingAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "property", "tenant", "scheduled_date", "status", "created_at")
    list_filter = ("status", "scheduled_date", "created_at")
    search_fields = ("property__title", "tenant__email", "tenant__full_name")
