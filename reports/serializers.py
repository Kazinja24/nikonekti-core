from rest_framework import serializers

from .models import PropertyReport, UserBlock


class PropertyReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)
    property_owner_id = serializers.UUIDField(source="property.owner.id", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.full_name", read_only=True)

    class Meta:
        model = PropertyReport
        fields = "__all__"
        read_only_fields = [
            "reporter",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "created_at",
        ]

    def validate(self, attrs):
        property_obj = attrs["property"]
        user = self.context["request"].user
        if property_obj.owner == user:
            raise serializers.ValidationError("You cannot report your own property.")
        return attrs


class PropertyReportReviewSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)


class UserBlockSerializer(serializers.ModelSerializer):
    blocker_name = serializers.CharField(source="blocker.full_name", read_only=True)
    blocked_user_name = serializers.CharField(source="blocked_user.full_name", read_only=True)
    blocked_user_email = serializers.EmailField(source="blocked_user.email", read_only=True)

    class Meta:
        model = UserBlock
        fields = "__all__"
        read_only_fields = ["blocker", "is_active", "created_at"]

    def validate(self, attrs):
        request_user = self.context["request"].user
        blocked_user = attrs["blocked_user"]
        if blocked_user == request_user:
            raise serializers.ValidationError("You cannot block yourself.")
        if blocked_user.role == "ADMIN":
            raise serializers.ValidationError("Admin users cannot be blocked.")
        return attrs
