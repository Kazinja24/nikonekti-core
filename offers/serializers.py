from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from applications.models import RentalApplication
from viewings.models import Viewing
from .models import RentalOffer


class RentalOfferSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True)
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    landlord_name = serializers.CharField(source="landlord.full_name", read_only=True)

    class Meta:
        model = RentalOffer
        fields = "__all__"
        read_only_fields = [
            "id",
            "property",
            "tenant",
            "landlord",
            "status",
            "responded_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        request = self.context["request"]
        application = data.get("application")
        viewing = data.get("viewing")

        if request.user.role != "LANDLORD":
            raise serializers.ValidationError("Only landlords can send rental offers.")

        if not application:
            raise serializers.ValidationError("An approved application is required.")

        if application.property.owner != request.user:
            raise serializers.ValidationError("You can only send offers for your own property.")
        if hasattr(application, "offer"):
            raise serializers.ValidationError("An offer already exists for this application.")

        if application.status != RentalApplication.Status.APPROVED:
            raise serializers.ValidationError("Offer can only be sent for approved applications.")

        if application.property.status != "available":
            raise serializers.ValidationError("Property is not available for a new offer.")

        if not viewing:
            raise serializers.ValidationError("A completed viewing is required before sending an offer.")
        if viewing.application_id != application.id:
            raise serializers.ValidationError("Viewing must match the selected application.")
        if viewing.status != Viewing.Status.COMPLETED:
            raise serializers.ValidationError("Offer can only be sent after viewing is completed.")

        return data

    def create(self, validated_data):
        application = validated_data["application"]
        validated_data["property"] = application.property
        validated_data["tenant"] = application.tenant
        validated_data["landlord"] = self.context["request"].user
        validated_data["status"] = RentalOffer.Status.SENT
        if not validated_data.get("expires_at"):
            validated_data["expires_at"] = timezone.now() + timedelta(hours=72)
        return super().create(validated_data)


class RentalOfferRespondSerializer(serializers.Serializer):
    tenant_note = serializers.CharField(required=False, allow_blank=True)
