from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from applications.models import RentalApplication
from nikonekti_backend.settings.services.sms_services import send_sms
from users.permissions import IsTenant
from .models import Viewing
from .serializers import ViewingSerializer


class ViewingViewSet(ModelViewSet):
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

        outcome = str(request.data.get("outcome", "")).upper()
        if outcome not in {"ACCEPTED", "REJECTED"}:
            return Response({"error": "Outcome must be ACCEPTED or REJECTED"}, status=400)

        application = RentalApplication.objects.filter(
            tenant=viewing.tenant,
            property=viewing.property,
            viewing=viewing,
            status="VIEWING_SCHEDULED",
        ).first()

        if not application:
            return Response({"error": "No viewing-scheduled application linked to this viewing"}, status=400)

        viewing.status = "completed" if outcome == "ACCEPTED" else "rejected"
        viewing.save(update_fields=["status"])

        application.status = outcome
        application.save(update_fields=["status"])

        return Response({"message": f"Viewing marked as {outcome.lower()}"})
