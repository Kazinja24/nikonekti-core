from rest_framework import serializers

from applications.models import RentalApplication
from .models import Lease


class LeaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lease
        fields = "__all__"
        read_only_fields = ["status", "signed_at", "terminated_at", "landlord", "is_signed", "application"]

    def validate(self, data):
        request = self.context["request"]
        property_obj = data["property"]
        tenant = data["tenant"]

        if property_obj.owner != request.user:
            raise serializers.ValidationError("Only the landlord owner can create this lease.")

        application = RentalApplication.objects.filter(
            property=property_obj,
            tenant=tenant,
            status="ACCEPTED",
        ).first()

        if not application:
            raise serializers.ValidationError("Lease cannot be created without an ACCEPTED application.")

        data["_application"] = application
        return data

    def create(self, validated_data):
        application = validated_data.pop("_application")
        validated_data["landlord"] = self.context["request"].user
        validated_data["application"] = application
        lease = super().create(validated_data)

        application.status = "LEASED"
        application.save(update_fields=["status"])

        return lease
