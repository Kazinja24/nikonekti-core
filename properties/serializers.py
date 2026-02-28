from rest_framework import serializers

from .models import Property, PropertyImage, Feature


class PropertyImageSerializer(serializers.ModelSerializer):
    thumbnail = serializers.ImageField(read_only=True)

    class Meta:
        model = PropertyImage
        fields = ["id", "image", "thumbnail", "is_cover", "order", "uploaded_at"]


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ["id", "name", "slug", "description"]


class PropertySerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    features = FeatureSerializer(many=True, read_only=True)
    feature_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Feature.objects.all(), source="features"
    )

    class Meta:
        model = Property
        fields = "__all__"
        read_only_fields = [
            "owner",
            "status",
            "verification_status",
            "verification_notes",
            "verified_by",
            "verified_at",
            "is_published",
            "published_at",
            "listing_status",
            "submitted_by",
            "approved_by",
            "approved_at",
            "admin_review_notes",
            "priority_score",
            "created_at",
        ]

    def create(self, validated_data):
        features = validated_data.pop("features", None)
        validated_data["owner"] = self.context["request"].user
        instance = super().create(validated_data)
        if features is not None:
            instance.features.set(features)
        return instance

    def update(self, instance, validated_data):
        features = validated_data.pop("features", None)
        instance = super().update(instance, validated_data)
        if features is not None:
            instance.features.set(features)
        return instance
