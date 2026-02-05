import uuid
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        property_obj = serializer.validated_data['property']

        if property_obj.is_booked:
            raise ValidationError({"property": "Property already booked"})

        serializer.save(
            tenant=self.request.user,
            reference=str(uuid.uuid4())
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        payment = self.get_object()

        if payment.status != 'pending':
            return Response({"error": "Already processed"}, status=400)

        payment.status = 'completed'
        payment.save()

        property_obj = payment.property
        property_obj.is_booked = True
        property_obj.save()

        return Response({"message": "Payment confirmed & booking completed"})
