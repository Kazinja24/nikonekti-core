from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "action", "actor", "ip_address", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("actor__email", "action", "data")
