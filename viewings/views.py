from rest_framework.decorators import action
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view

from nikonekti_backend.settings.services.sms_services import send_sms
from users.permissions import IsTenant
from .models import Viewing
from .serializers import ViewingSerializer


@extend_schema_view(
    list=extend_schema(tags=["Viewings - Tenant/Landlord"]),
    retrieve=extend_schema(tags=["Viewings - Tenant/Landlord"]),
    create=extend_schema(tags=["Viewings - Tenant"]),
    approve=extend_schema(tags=["Viewings - Landlord"]),
    reject=extend_schema(tags=["Viewings - Landlord"]),
    complete=extend_schema(tags=["Viewings - Landlord"]),
)
class ViewingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Viewing.objects.all()
    serializer_class = ViewingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == "TENANT":
            return Viewing.objects.filter(tenant=user)

        if user.role == "LANDLORD":
            return Viewing.objects.filter(property__owner=user)

        return Viewing.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsTenant()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        viewing = self.get_object()

        if request.user != viewing.property.owner:
            return Response({"error": "Not allowed"}, status=403)

        if viewing.status != "pending":
            return Response({"error": "Already processed"}, status=400)

        if not viewing.application or viewing.application.status != "approved":
            return Response({"error": "Viewing is locked because application is not approved."}, status=400)

        viewing.status = "approved"
        viewing.save(update_fields=["status"])

        phone = getattr(viewing.tenant, "phone", "")
        if phone:
            send_sms(phone, f"Your viewing for {viewing.property.title} has been approved.")

        return Response({"message": "Viewing approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        viewing = self.get_object()

        if request.user != viewing.property.owner:
            return Response({"error": "Not allowed"}, status=403)

        if viewing.status != "pending":
            return Response({"error": "Already processed"}, status=400)

        viewing.status = "rejected"
        viewing.save(update_fields=["status"])

        phone = getattr(viewing.tenant, "phone", "")
        if phone:
            send_sms(phone, f"Your viewing request for {viewing.property.title} was rejected.")

        return Response({"message": "Viewing rejected"})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        viewing = self.get_object()

        if request.user != viewing.property.owner:
            return Response({"error": "Only landlord can complete viewing"}, status=403)

        if viewing.status not in {"approved", "pending"}:
            return Response({"error": "Only pending or approved viewings can be completed"}, status=400)

        if not viewing.application or viewing.application.status != "approved":
            return Response({"error": "Viewing is locked because application is not approved."}, status=400)

        viewing.status = "completed"
        viewing.save(update_fields=["status"])

        return Response({"message": "Viewing marked as completed"})
