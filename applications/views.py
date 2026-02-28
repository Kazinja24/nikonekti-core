from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import RentalApplication
from .serializers import RentalApplicationSerializer
from users.permissions import IsTenant


@extend_schema_view(
    list=extend_schema(tags=["Applications - Tenant/Landlord/Admin"]),
    retrieve=extend_schema(tags=["Applications - Tenant/Landlord/Admin"]),
    create=extend_schema(tags=["Applications - Tenant"]),
    by_property=extend_schema(tags=["Applications - Landlord"]),
    can_message=extend_schema(tags=["Applications - Tenant"]),
    can_request_viewing=extend_schema(tags=["Applications - Tenant"]),
    approve=extend_schema(tags=["Applications - Landlord"]),
    reject=extend_schema(tags=["Applications - Landlord"]),
    expire=extend_schema(tags=["Applications - Landlord"]),
    tenant_profile=extend_schema(tags=["Applications - Tenant/Landlord/Admin"]),
)
class ApplicationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = RentalApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = RentalApplication.objects.select_related("tenant", "property", "property__owner")

    def get_queryset(self):
        user = self.request.user
        if user.role == "LANDLORD":
            queryset = self.queryset.filter(property__owner=user)

            property_id = self.request.query_params.get("property")
            if property_id:
                if not queryset.filter(property_id=property_id).exists():
                    return queryset.none()
                queryset = queryset.filter(property_id=property_id)

            status_value = self.request.query_params.get("status")
            if status_value:
                statuses = [status_item.strip().lower() for status_item in status_value.split(",") if status_item.strip()]
                if statuses:
                    queryset = queryset.filter(status__in=statuses)

            return queryset
        if user.role == "ADMIN":
            return self.queryset
        return self.queryset.filter(tenant=user)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsTenant()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user)

    @action(detail=False, methods=["GET"], url_path=r"property/(?P<property_id>[^/.]+)")
    def by_property(self, request, property_id=None):
        if request.user.role != "LANDLORD":
            return Response({"error": "Only landlords can access property applications."}, status=status.HTTP_403_FORBIDDEN)

        queryset = self.queryset.filter(property_id=property_id, property__owner=request.user)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["GET"])
    def can_message(self, request):
        if request.user.role != "TENANT":
            return Response({"error": "Only tenants can check this gate."}, status=status.HTTP_403_FORBIDDEN)

        property_id = request.query_params.get("property_id")
        if not property_id:
            return Response({"error": "property_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        has_active_application = RentalApplication.objects.filter(
            tenant=request.user,
            property_id=property_id,
            status__in=RentalApplication.ACTIVE_STATUSES,
        ).exists()

        return Response({"can_message_landlord": has_active_application})

    @action(detail=False, methods=["GET"])
    def can_request_viewing(self, request):
        if request.user.role != "TENANT":
            return Response({"error": "Only tenants can check this gate."}, status=status.HTTP_403_FORBIDDEN)

        property_id = request.query_params.get("property_id")
        if not property_id:
            return Response({"error": "property_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        has_approved_application = RentalApplication.objects.filter(
            tenant=request.user,
            property_id=property_id,
            status=RentalApplication.Status.APPROVED,
        ).exists()

        return Response({"can_request_viewing": has_approved_application})

    def _ensure_owner(self, application):
        if application.property.owner != self.request.user:
            return Response({"error": "Only the owning landlord can manage this application."}, status=403)
        return None

    def _transition_application(self, application, target_status, note):
        if not application.can_transition_to(target_status):
            return Response(
                {"error": f"Invalid transition from '{application.status}' to '{target_status}'."},
                status=400,
            )

        application.status = target_status
        application.decided_at = timezone.now()
        application.landlord_note = note
        application.save(update_fields=["status", "decided_at", "landlord_note"])

        if target_status in {RentalApplication.Status.REJECTED, RentalApplication.Status.EXPIRED}:
            application.viewings.filter(status__in=["pending", "approved"]).update(status="rejected")

        return Response({"message": f"Application {target_status}."})

    @action(detail=True, methods=["POST"])
    def approve(self, request, pk=None):
        application = self.get_object()
        owner_error = self._ensure_owner(application)
        if owner_error:
            return owner_error

        return self._transition_application(
            application,
            RentalApplication.Status.APPROVED,
            request.data.get("note", ""),
        )

    @action(detail=True, methods=["POST"])
    def reject(self, request, pk=None):
        application = self.get_object()
        owner_error = self._ensure_owner(application)
        if owner_error:
            return owner_error

        return self._transition_application(
            application,
            RentalApplication.Status.REJECTED,
            request.data.get("note", ""),
        )

    @action(detail=True, methods=["POST"])
    def expire(self, request, pk=None):
        application = self.get_object()
        owner_error = self._ensure_owner(application)
        if owner_error:
            return owner_error

        return self._transition_application(
            application,
            RentalApplication.Status.EXPIRED,
            request.data.get("note", ""),
        )

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
