from rest_framework import serializers
from .models import Payment, RentInvoice, ListingPlan, ListingPaymentIntent


class PaymentSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True)
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "property_title", "amount", "status", "reference", "tenant_name", "created_at"]
        read_only_fields = ["id", "created_at"]

class RentInvoiceSerializer(serializers.ModelSerializer):
    lease_id = serializers.UUIDField(source="lease.id", read_only=True)
    property_title = serializers.CharField(source="lease.property.title", read_only=True)
    tenant_name = serializers.CharField(source="lease.tenant.full_name", read_only=True)
    landlord_name = serializers.CharField(source="lease.landlord.full_name", read_only=True)

    class Meta:
        model = RentInvoice
        fields = [
            "id",
            "lease_id",
            "property_title",
            "tenant_name",
            "landlord_name",
            "month",
            "amount",
            "due_date",
            "status",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class ListingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPlan
        fields = "__all__"


class ListingPaymentIntentSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True)
    landlord_name = serializers.CharField(source="landlord.full_name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    is_featured = serializers.BooleanField(source="plan.is_featured", read_only=True)

    class Meta:
        model = ListingPaymentIntent
        fields = "__all__"
        read_only_fields = [
            "id",
            "landlord",
            "amount",
            "status",
            "admin_note",
            "confirmed_by",
            "reviewed_at",
            "starts_at",
            "expires_at",
            "created_at",
        ]


class ListingPaymentIntentCreateSerializer(serializers.Serializer):
    property = serializers.IntegerField(required=True)
    plan = serializers.IntegerField(required=True)
    landlord_note = serializers.CharField(required=False, allow_blank=True)


class ListingPaymentIntentRequestConfirmationSerializer(serializers.Serializer):
    payment_reference = serializers.CharField(required=False, allow_blank=True)
    payment_proof = serializers.FileField(required=False)
    landlord_note = serializers.CharField(required=False, allow_blank=True)


class ListingPaymentIntentReviewSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True)
