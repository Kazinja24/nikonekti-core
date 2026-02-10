from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from nikonekti_backend.settings.services.sms_services import send_sms

from django.shortcuts import render

# Create your views here.
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Viewing
from .serializers import ViewingSerializer
from nikonekti_backend.permissions import IsTenant
from users.permissions import IsTenant, IsAgent, IsLandlord


class ViewingViewSet(ModelViewSet):
    queryset = Viewing.objects.all()
    serializer_class = ViewingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == 'tenant':
            return Viewing.objects.filter(tenant=user)

        if user.role == 'landlord':
            return Viewing.objects.filter(property__owner=user)

        return Viewing.objects.none()

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsTenant()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):

        viewing = self.get_object()

        if request.user != viewing.property.owner:
            return Response({"error": "Not allowed"}, status=403)

        if viewing.status != 'pending':
            return Response({"error": "Already processed"}, status=400)

        viewing.status = 'approved'
        viewing.save()

        send_sms(
            viewing.tenant.phone_number,
            f"Your viewing for {viewing.property.title} has been approved."
        )

        return Response({"message": "Viewing approved"})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):

        viewing = self.get_object()

        if request.user != viewing.property.owner:
            return Response({"error": "Not allowed"}, status=403)

        if viewing.status != 'pending':
            return Response({"error": "Already processed"}, status=400)

        viewing.status = 'rejected'
        viewing.save()

        send_sms(
            viewing.tenant.phone_number,
            f"Your viewing request for {viewing.property.title} was rejected."
        )

        return Response({"message": "Viewing rejected"})


def get_permissions(self):
    if self.action == 'create':
        return [IsTenant()]
    elif self.action in ['approve', 'reject']:
        return [IsAgent() | IsLandlord()]
    return [IsAuthenticated()]
