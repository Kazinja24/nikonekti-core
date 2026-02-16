from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from .models import Payment, RentInvoice
from .serializers import InvoiceSerializer, PaymentSerializer


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "LANDLORD":
            return RentInvoice.objects.filter(lease__landlord=user)
        return RentInvoice.objects.filter(lease__tenant=user)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "LANDLORD":
            return Payment.objects.filter(invoice__lease__landlord=user)
        return Payment.objects.filter(invoice__lease__tenant=user)

    def create(self, request, *args, **kwargs):
        invoice_id = request.data.get("invoice")
        method = request.data.get("method")
        reference = request.data.get("reference")

        if not invoice_id:
            return Response({"error": "invoice is required"}, status=400)
        if not method:
            return Response({"error": "method is required"}, status=400)

        invoice = get_object_or_404(RentInvoice, id=invoice_id)

        if invoice.lease.tenant != request.user:
            return Response({"error": "Not your invoice"}, status=403)

        if invoice.status == "PAID":
            return Response({"error": "Invoice already paid"}, status=400)
        if invoice.lease.status != "ACTIVE":
            return Response({"error": "Payments are allowed only for ACTIVE leases"}, status=400)

        payment = Payment.objects.create(
            invoice=invoice,
            amount=invoice.amount,
            method=method,
            reference=reference,
        )

        invoice.status = "PAID"
        invoice.save(update_fields=["status"])

        serializer = self.get_serializer(payment)
        return Response(serializer.data, status=201)
