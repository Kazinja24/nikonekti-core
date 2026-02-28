from rest_framework import serializers

from applications.models import RentalApplication
from .models import Viewing


class ViewingSerializer(serializers.ModelSerializer):
    tenant = serializers.HiddenField(default=serializers.CurrentUserDefault())
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)
    date = serializers.SerializerMethodField(read_only=True)
    time_window = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Viewing
        fields = "__all__"
        read_only_fields = ["status", "created_at", "tenant", "property"]

    def validate(self, data):
        request = self.context["request"]
        application = data.get("application")

        if not application:
            raise serializers.ValidationError("An application is required before requesting a viewing.")

        if application.tenant != request.user:
            raise serializers.ValidationError("You can only request a viewing for your own application.")

        if application.status != RentalApplication.Status.APPROVED:
            raise serializers.ValidationError("Viewing is locked unless the application is approved.")
        if application.property.status != "available":
            raise serializers.ValidationError("Viewing is unavailable because the property is not available.")

        has_open_viewing = Viewing.objects.filter(
            application=application,
            status__in=["pending", "approved"],
        ).exists()
        if has_open_viewing:
            raise serializers.ValidationError("An active viewing request already exists for this application.")

        data["_application"] = application
        return data

    def create(self, validated_data):
        application = validated_data.pop("_application")

        if application.status != RentalApplication.Status.APPROVED:
            raise serializers.ValidationError("Application is no longer approved for viewing scheduling.")

        validated_data["status"] = "pending"
        validated_data["property"] = application.property
        validated_data["tenant"] = application.tenant
        viewing = super().create(validated_data)

        return viewing

    def get_date(self, obj) -> str:
        return obj.scheduled_date.date().isoformat()

    def get_time_window(self, obj) -> str:
        hour = obj.scheduled_date.hour
        if hour < 12:
            return "morning"
        if hour < 16:
            return "afternoon"
        return "evening"
