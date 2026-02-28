from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from users.permissions import IsAdmin, IsLandlord
from .permissions import IsPaymentOwnerOrAdmin
import logging
from .models import Payment, RentInvoice, ListingPlan, ListingPaymentIntent
from .serializers import (
    PaymentSerializer,
    RentInvoiceSerializer,
    ListingPlanSerializer,
    ListingPaymentIntentSerializer,
    ListingPaymentIntentCreateSerializer,
    ListingPaymentIntentRequestConfirmationSerializer,
    ListingPaymentIntentReviewSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Payments - Authenticated"]),
    retrieve=extend_schema(tags=["Payments - Authenticated"]),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPaymentOwnerOrAdmin]
    throttle_classes = [UserRateThrottle]
    throttle_scope = 'payments'
    queryset = Payment.objects.all()

    # audit logger; configure handlers in Django logging config if desired
    logger = logging.getLogger("payments.audit")

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Payment.objects.all()
        if user.role == "TENANT":
            return Payment.objects.filter(tenant=user)
        if user.role == "LANDLORD":
            return Payment.objects.filter(property__owner=user)
        return Payment.objects.none()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        try:
            self.logger.info(
                "payment_list_access",
                extra={
                    "user_id": request.user.id if request.user and request.user.is_authenticated else None,
                    "username": getattr(request.user, "email", None),
                    "count": len(response.data) if isinstance(response.data, list) else None,
                    "remote_addr": request.META.get("REMOTE_ADDR"),
                },
            )
            # audit record
            try:
                from audit.utils import log_action

                log_action(request, "payments.list", data={"count": len(response.data) if isinstance(response.data, list) else None})
            except Exception:
                pass
        except Exception:
            # never fail the API because logging failed
            pass
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        try:
            obj = self.get_object()
            self.logger.info(
                "payment_detail_access",
                extra={
                    "user_id": request.user.id if request.user and request.user.is_authenticated else None,
                    "username": getattr(request.user, "email", None),
                    "payment_id": getattr(obj, "id", None),
                    "remote_addr": request.META.get("REMOTE_ADDR"),
                },
            )
            try:
                from audit.utils import log_action

                log_action(request, "payments.retrieve", target=obj, data={"payment_id": getattr(obj, "id", None)})
            except Exception:
                pass
        except Exception:
            pass
        return response


@extend_schema_view(
    list=extend_schema(tags=["Payments - Authenticated"]),
    retrieve=extend_schema(tags=["Payments - Authenticated"]),
)
class RentInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RentInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = RentInvoice.objects.select_related("lease", "lease__property", "lease__tenant", "lease__landlord")

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return self.queryset
        if user.role == "TENANT":
            return self.queryset.filter(lease__tenant=user)
        if user.role == "LANDLORD":
            return self.queryset.filter(lease__landlord=user)
        return self.queryset.none()


@extend_schema_view(
    list=extend_schema(tags=["Listings - Authenticated"]),
    retrieve=extend_schema(tags=["Listings - Authenticated"]),
)
class ListingPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ListingPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ListingPlan.objects.filter(is_active=True)


@extend_schema_view(
    list=extend_schema(tags=["Listings - Landlord/Admin"]),
    retrieve=extend_schema(tags=["Listings - Landlord/Admin"]),
    create=extend_schema(tags=["Listings - Landlord"]),
    request_confirmation=extend_schema(tags=["Listings - Landlord"]),
    confirm=extend_schema(tags=["Listings - Admin"]),
    reject=extend_schema(tags=["Listings - Admin"]),
    override=extend_schema(tags=["Listings - Admin"]),
)
class ListingPaymentIntentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ListingPaymentIntentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ListingPaymentIntent.objects.select_related("property", "landlord", "plan", "confirmed_by")
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return self.queryset
        if user.role == "LANDLORD":
            return self.queryset.filter(landlord=user)
        return self.queryset.none()

    def get_permissions(self):
        if self.action in ["confirm", "reject", "override"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.action in ["create", "request_confirmation"]:
            return [permissions.IsAuthenticated(), IsLandlord()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return ListingPaymentIntentCreateSerializer
        if self.action == "request_confirmation":
            return ListingPaymentIntentRequestConfirmationSerializer
        if self.action in ["confirm", "reject", "override"]:
            return ListingPaymentIntentReviewSerializer
        return ListingPaymentIntentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from properties.models import Property

        property_obj = get_object_or_404(Property, id=serializer.validated_data["property"])
        plan = get_object_or_404(ListingPlan, id=serializer.validated_data["plan"], is_active=True)

        if property_obj.owner != request.user:
            return Response({"error": "You can only create listing intent for your own property."}, status=403)
        if not request.user.is_verified_landlord:
            return Response({"error": "Only verified landlords can create paid listing intents."}, status=400)
        if not property_obj.can_be_monetized():
            return Response({"error": "Property must be verification-approved before listing payment intent."}, status=400)

        intent = ListingPaymentIntent.objects.create(
            property=property_obj,
            landlord=request.user,
            plan=plan,
            amount=plan.price,
            landlord_note=serializer.validated_data.get("landlord_note", ""),
            status=ListingPaymentIntent.Status.INTENT_CREATED,
        )
        output = ListingPaymentIntentSerializer(intent, context={"request": request})
        return Response(output.data, status=201)

    @action(detail=True, methods=["POST"])
    def request_confirmation(self, request, pk=None):
        intent = self.get_object()
        if intent.landlord != request.user:
            return Response({"error": "Only owning landlord can request confirmation."}, status=403)
        if intent.status not in [
            ListingPaymentIntent.Status.INTENT_CREATED,
            ListingPaymentIntent.Status.REJECTED,
        ]:
            return Response({"error": "Intent is not in a confirmable state."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        intent.payment_reference = serializer.validated_data.get("payment_reference", "")
        if serializer.validated_data.get("payment_proof"):
            intent.payment_proof = serializer.validated_data["payment_proof"]
        intent.landlord_note = serializer.validated_data.get("landlord_note", intent.landlord_note)
        intent.status = ListingPaymentIntent.Status.PENDING_CONFIRMATION
        intent.save(
            update_fields=["payment_reference", "payment_proof", "landlord_note", "status"]
        )
        return Response({"message": "Payment confirmation requested."})

    @action(detail=True, methods=["POST"])
    def confirm(self, request, pk=None):
        intent = self.get_object()
        if intent.status not in [ListingPaymentIntent.Status.PENDING_CONFIRMATION, ListingPaymentIntent.Status.INTENT_CREATED]:
            return Response({"error": "Only pending listing intents can be confirmed."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            intent.activate(
                reviewed_by=request.user,
                override=False,
                admin_note=serializer.validated_data.get("admin_note", ""),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({"message": "Listing payment confirmed."})

    @action(detail=True, methods=["POST"])
    def reject(self, request, pk=None):
        intent = self.get_object()
        if intent.status in [ListingPaymentIntent.Status.CONFIRMED, ListingPaymentIntent.Status.OVERRIDDEN, ListingPaymentIntent.Status.EXPIRED]:
            return Response({"error": "This intent cannot be rejected in its current state."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        intent.status = ListingPaymentIntent.Status.REJECTED
        intent.admin_note = serializer.validated_data.get("admin_note", "")
        intent.confirmed_by = request.user
        intent.reviewed_at = timezone.now()
        intent.save(update_fields=["status", "admin_note", "confirmed_by", "reviewed_at"])
        return Response({"message": "Listing payment rejected."})

    @action(detail=True, methods=["POST"])
    def override(self, request, pk=None):
        intent = self.get_object()
        if intent.status == ListingPaymentIntent.Status.EXPIRED:
            return Response({"error": "Expired intent cannot be overridden."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            intent.activate(
                reviewed_by=request.user,
                override=True,
                admin_note=serializer.validated_data.get("admin_note", ""),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({"message": "Listing payment overridden and activated."})
