from datetime import datetime

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
        read_only_fields = ["status", "created_at"]

    def validate(self, data):
        request = self.context["request"]
        property_obj = data["property"]

        application = RentalApplication.objects.filter(
            tenant=request.user,
            property=property_obj,
            status="APPROVED",
        ).first()

        if not application:
            raise serializers.ValidationError("You need an approved application before requesting viewing.")

        data["_application"] = application
        return data

    def create(self, validated_data):
        application = validated_data.pop("_application")

        if application.status != "APPROVED":
            raise serializers.ValidationError("Application is no longer approved for viewing scheduling.")

        validated_data["status"] = "approved"
        viewing = super().create(validated_data)

        application.viewing = viewing
        application.status = "VIEWING_SCHEDULED"
        application.save(update_fields=["viewing", "status"])

        return viewing

    def get_date(self, obj):
        return obj.scheduled_date.date().isoformat()

    def get_time_window(self, obj):
        hour = obj.scheduled_date.hour
        if hour < 12:
            return "morning"
        if hour < 16:
            return "afternoon"
        return "evening"
