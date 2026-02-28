from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender_id",
            "sender_name",
            "sender_role",
            "content",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sender_id",
            "sender_name",
            "sender_role",
            "is_read",
            "read_at",
            "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(source="application.id", read_only=True)
    # property-based conversation fields (fall back to property or application)
    property_id = serializers.SerializerMethodField()
    property_title = serializers.SerializerMethodField()
    tenant_id = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    landlord_id = serializers.SerializerMethodField()
    landlord_name = serializers.SerializerMethodField()
    last_message_at = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "application_id",
            "property_id",
            "property_title",
            "tenant_id",
            "tenant_name",
            "landlord_id",
            "landlord_name",
            "created_at",
            "last_message_at",
        ]

    def get_property_id(self, obj):
        if obj.application_id and getattr(obj.application, 'property', None):
            return obj.application.property.id
        if getattr(obj, 'property_obj', None):
            return obj.property_obj.id
        return None

    def get_property_title(self, obj):
        if obj.application_id and getattr(obj.application, 'property', None):
            return obj.application.property.title
        if getattr(obj, 'property_obj', None):
            return obj.property_obj.title
        return None

    def get_tenant_id(self, obj):
        tenant = obj.tenant
        return getattr(tenant, 'id', None)

    def get_tenant_name(self, obj):
        tenant = obj.tenant
        return getattr(tenant, 'full_name', None)

    def get_landlord_id(self, obj):
        landlord = obj.landlord
        return getattr(landlord, 'id', None)

    def get_landlord_name(self, obj):
        landlord = obj.landlord
        return getattr(landlord, 'full_name', None)


class OpenConversationSerializer(serializers.Serializer):
    application_id = serializers.UUIDField(required=False)
    property_id = serializers.IntegerField(required=False)
