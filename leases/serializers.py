from rest_framework import serializers

from applications.models import RentalApplication
from offers.models import RentalOffer
from .models import Lease


class LeaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lease
        fields = "__all__"
        read_only_fields = [
            "status",
            "signed_at",
            "tenant_confirmed_at",
            "landlord_confirmed_at",
            "terminated_at",
            "landlord",
            "is_signed",
            "application",
        ]

    def validate(self, data):
        request = self.context["request"]
        property_obj = data["property"]
        tenant = data["tenant"]

        if property_obj.owner != request.user:
            raise serializers.ValidationError("Only the landlord owner can create this lease.")
        if property_obj.status != "available":
            raise serializers.ValidationError("Lease cannot be created because the property is not available.")

        application = RentalApplication.objects.filter(
            property=property_obj,
            tenant=tenant,
            status=RentalApplication.Status.APPROVED,
        ).first()

        if not application:
            raise serializers.ValidationError("Lease cannot be created without an approved application.")
        if not hasattr(application, "offer") or application.offer.status != RentalOffer.Status.ACCEPTED:
            raise serializers.ValidationError("Lease cannot be created without an accepted rental offer.")

        data["_application"] = application
        return data

    def create(self, validated_data):
        application = validated_data.pop("_application")
        validated_data["landlord"] = self.context["request"].user
        validated_data["application"] = application
        return super().create(validated_data)
