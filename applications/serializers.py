from rest_framework import serializers

from .models import RentalApplication


class RentalApplicationSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    tenant_email = serializers.CharField(source="tenant.email", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)
    tenant_profile = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RentalApplication
        fields = "__all__"
        read_only_fields = ["tenant", "status", "decided_at", "landlord_note"]
        extra_kwargs = {
            "message": {"required": False, "allow_blank": True},
        }

    def validate(self, data):
        request = self.context["request"]
        property_obj = data["property"]
        tenant = request.user

        if property_obj.owner == request.user:
            raise serializers.ValidationError("You cannot apply to your own property.")

        if not property_obj.is_published or property_obj.verification_status != "approved":
            raise serializers.ValidationError("You can only apply to verified and published properties.")
        if property_obj.status != "available":
            raise serializers.ValidationError("This property is no longer available for applications.")

        has_active_application = RentalApplication.objects.filter(
            tenant=tenant,
            property=property_obj,
            status__in=RentalApplication.ACTIVE_STATUSES,
        ).exists()
        if has_active_application:
            raise serializers.ValidationError("You already have an active application for this property.")

        return data

    def create(self, validated_data):
        if validated_data.get("message") is None:
            validated_data["message"] = ""

        return super().create(validated_data)

    def get_tenant_profile(self, obj) -> dict:
        tenant = obj.tenant
        return {
            "id": str(tenant.id),
            "full_name": tenant.full_name,
            "email": tenant.email,
            "role": tenant.role,
            "created_at": tenant.created_at,
        }
