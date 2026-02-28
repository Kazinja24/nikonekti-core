from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "action",
            "target_type",
            "target_object_id",
            "data",
            "ip_address",
            "created_at",
        ]

    def get_target_type(self, obj):
        return obj.target_content_type.model if obj.target_content_type else None
