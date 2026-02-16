from rest_framework import serializers
from .models import RentInvoice, Payment


class InvoiceSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="lease.property.title", read_only=True)
    tenant_name = serializers.CharField(source="lease.tenant.full_name", read_only=True)
    landlord_name = serializers.CharField(source="lease.landlord.full_name", read_only=True)

    class Meta:
        model = RentInvoice
        fields = "__all__"
        read_only_fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="invoice.lease.property.title", read_only=True)
    tenant_name = serializers.CharField(source="invoice.lease.tenant.full_name", read_only=True)
    lease = serializers.UUIDField(source="invoice.lease_id", read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.DateTimeField(source="paid_at", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"

    def get_status(self, obj):
        return "PAID"
