from rest_framework import serializers

from .models import LandlordVerification


class LandlordVerificationSerializer(serializers.ModelSerializer):
    landlord_id = serializers.UUIDField(source="landlord.id", read_only=True)
    landlord_email = serializers.EmailField(source="landlord.email", read_only=True)
    reviewed_by_id = serializers.UUIDField(source="reviewed_by.id", read_only=True)

    class Meta:
        model = LandlordVerification
        fields = [
            "id",
            "landlord_id",
            "landlord_email",
            "identity_document",
            "landlord_supporting_document",
            "status",
            "review_notes",
            "reviewed_by_id",
            "reviewed_at",
            "submitted_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "landlord_id",
            "landlord_email",
            "status",
            "review_notes",
            "reviewed_by_id",
            "reviewed_at",
            "submitted_at",
            "updated_at",
        ]


class LandlordVerificationSubmitSerializer(serializers.Serializer):
    identity_document = serializers.FileField(required=True)
    landlord_supporting_document = serializers.FileField(required=True)


class LandlordVerificationReviewSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)
