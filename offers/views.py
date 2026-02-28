from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from users.permissions import IsLandlord, IsTenant
from audit.utils import log_action
from .models import RentalOffer
from .serializers import RentalOfferSerializer, RentalOfferRespondSerializer


@extend_schema_view(
    list=extend_schema(tags=["Offers - Tenant/Landlord/Admin"]),
    retrieve=extend_schema(tags=["Offers - Tenant/Landlord/Admin"]),
    create=extend_schema(tags=["Offers - Landlord"]),
    accept=extend_schema(tags=["Offers - Tenant"]),
    reject=extend_schema(tags=["Offers - Tenant"]),
    withdraw=extend_schema(tags=["Offers - Landlord"]),
)
class RentalOfferViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = RentalOffer.objects.select_related(
        "property",
        "application",
        "viewing",
        "tenant",
        "landlord",
    )
    serializer_class = RentalOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsLandlord()]
        if self.action in ["accept", "reject"]:
            return [permissions.IsAuthenticated(), IsTenant()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return self.queryset
        if user.role == "LANDLORD":
            return self.queryset.filter(landlord=user)
        if user.role == "TENANT":
            return self.queryset.filter(tenant=user)
        return self.queryset.none()

    def get_serializer_class(self):
        if self.action in ["accept", "reject"]:
            return RentalOfferRespondSerializer
        return RentalOfferSerializer

    def perform_create(self, serializer):
        offer = serializer.save()
        try:
            log_action(
                self.request,
                "offer.sent",
                target=offer,
                data={
                    "offer_id": str(offer.id),
                    "application_id": str(offer.application_id),
                    "property_id": offer.property_id,
                    "tenant_id": str(offer.tenant_id),
                },
            )
        except Exception:
            pass

    @action(detail=True, methods=["POST"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        if request.user != offer.tenant:
            return Response({"error": "Only the offer tenant can accept."}, status=403)
        if offer.status != RentalOffer.Status.SENT:
            return Response({"error": "Only sent offers can be accepted."}, status=400)
        if offer.expires_at and offer.expires_at <= timezone.now():
            offer.status = RentalOffer.Status.EXPIRED
            offer.responded_at = timezone.now()
            offer.save(update_fields=["status", "responded_at"])
            try:
                log_action(request, "offer.expired", target=offer, data={"offer_id": str(offer.id)})
            except Exception:
                pass
            return Response({"error": "Offer has expired."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        offer.status = RentalOffer.Status.ACCEPTED
        offer.tenant_note = serializer.validated_data.get("tenant_note", "")
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "tenant_note", "responded_at"])
        try:
            log_action(request, "offer.accepted", target=offer, data={"offer_id": str(offer.id)})
        except Exception:
            pass
        return Response({"message": "Offer accepted."})

    @action(detail=True, methods=["POST"])
    def reject(self, request, pk=None):
        offer = self.get_object()
        if request.user != offer.tenant:
            return Response({"error": "Only the offer tenant can reject."}, status=403)
        if offer.status != RentalOffer.Status.SENT:
            return Response({"error": "Only sent offers can be rejected."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        offer.status = RentalOffer.Status.REJECTED
        offer.tenant_note = serializer.validated_data.get("tenant_note", "")
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "tenant_note", "responded_at"])
        try:
            log_action(request, "offer.rejected", target=offer, data={"offer_id": str(offer.id)})
        except Exception:
            pass
        return Response({"message": "Offer rejected."})

    @action(detail=True, methods=["POST"])
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        if request.user != offer.landlord:
            return Response({"error": "Only the sending landlord can withdraw this offer."}, status=403)
        if offer.status != RentalOffer.Status.SENT:
            return Response({"error": "Only sent offers can be withdrawn."}, status=400)

        offer.status = RentalOffer.Status.WITHDRAWN
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "responded_at"])
        try:
            log_action(request, "offer.withdrawn", target=offer, data={"offer_id": str(offer.id)})
        except Exception:
            pass
        return Response({"message": "Offer withdrawn."})
