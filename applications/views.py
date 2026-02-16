from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import RentalApplication
from .serializers import RentalApplicationSerializer
from users.permissions import IsTenant


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = RentalApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "LANDLORD":
            queryset = RentalApplication.objects.filter(property__owner=user).select_related("tenant", "property")

            property_id = self.request.query_params.get("property")
            if property_id:
                queryset = queryset.filter(property_id=property_id)

            status_value = self.request.query_params.get("status")
            if status_value:
                statuses = [status.strip().upper() for status in status_value.split(",") if status.strip()]
                if statuses:
                    queryset = queryset.filter(status__in=statuses)

            return queryset
        if user.role == "ADMIN":
            return RentalApplication.objects.select_related("tenant", "property")
        return RentalApplication.objects.filter(tenant=user).select_related("tenant", "property")

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsTenant()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user)

    @action(detail=True, methods=["POST"])
    def approve(self, request, pk=None):
        application = self.get_object()

        if application.property.owner != request.user:
            return Response({"error": "Only landlord can approve"}, status=403)
        if application.status != "PENDING":
            return Response({"error": "Only pending applications can be approved"}, status=400)

        application.status = "APPROVED"
        application.decided_at = timezone.now()
        application.landlord_note = request.data.get("note", "")
        application.save(update_fields=["status", "decided_at", "landlord_note"])

        return Response({"message": "Application approved"})

    @action(detail=True, methods=["POST"])
    def reject(self, request, pk=None):
        application = self.get_object()

        if application.property.owner != request.user:
            return Response({"error": "Only landlord can reject"}, status=403)
        if application.status not in {"PENDING", "VIEWING_SCHEDULED"}:
            return Response({"error": "Only pending or viewing scheduled applications can be rejected"}, status=400)

        application.status = "REJECTED"
        application.decided_at = timezone.now()
        application.landlord_note = request.data.get("note", "")
        application.save(update_fields=["status", "decided_at", "landlord_note"])

        return Response({"message": "Application rejected"})

    @action(detail=True, methods=["POST"])
    def accept(self, request, pk=None):
        application = self.get_object()

        if application.property.owner != request.user:
            return Response({"error": "Only landlord can accept"}, status=403)
        if application.status != "VIEWING_SCHEDULED":
            return Response({"error": "Only viewing scheduled applications can be accepted"}, status=400)

        application.status = "ACCEPTED"
        application.decided_at = timezone.now()
        application.landlord_note = request.data.get("note", "")
        application.save(update_fields=["status", "decided_at", "landlord_note"])

        return Response({"message": "Application accepted"})

    @action(detail=True, methods=["GET"], url_path="tenant-profile")
    def tenant_profile(self, request, pk=None):
        application = self.get_object()

        if request.user not in [application.property.owner, application.tenant] and request.user.role != "ADMIN":
            return Response({"error": "Not allowed"}, status=403)

        tenant = application.tenant
        return Response(
            {
                "id": str(tenant.id),
                "full_name": tenant.full_name,
                "email": tenant.email,
                "role": tenant.role,
                "created_at": tenant.created_at,
            }
        )
