from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from users.permissions import IsAdmin, IsLandlord
from .models import LandlordVerification
from .serializers import (
    LandlordVerificationReviewSerializer,
    LandlordVerificationSerializer,
    LandlordVerificationSubmitSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Verification - Landlord/Admin"]),
    retrieve=extend_schema(tags=["Verification - Landlord/Admin"]),
    submit=extend_schema(tags=["Verification - Landlord"]),
    approve=extend_schema(tags=["Verification - Admin"]),
    reject=extend_schema(tags=["Verification - Admin"]),
)
class LandlordVerificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = LandlordVerification.objects.select_related("landlord", "reviewed_by")
    serializer_class = LandlordVerificationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return self.queryset
        if user.role == "LANDLORD":
            return self.queryset.filter(landlord=user)
        return self.queryset.none()

    def get_permissions(self):
        if self.action == "submit":
            return [IsAuthenticated(), IsLandlord()]
        if self.action in ["approve", "reject"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "submit":
            return LandlordVerificationSubmitSerializer
        if self.action in ["approve", "reject"]:
            return LandlordVerificationReviewSerializer
        return LandlordVerificationSerializer

    @action(detail=False, methods=["POST"])
    def submit(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verification, _ = LandlordVerification.objects.update_or_create(
            landlord=request.user,
            defaults={
                "identity_document": serializer.validated_data["identity_document"],
                "landlord_supporting_document": serializer.validated_data["landlord_supporting_document"],
                "status": LandlordVerification.Status.PENDING,
                "review_notes": "",
                "reviewed_by": None,
                "reviewed_at": None,
            },
        )

        request.user.is_verified_landlord = False
        request.user.save(update_fields=["is_verified_landlord"])

        return Response(LandlordVerificationSerializer(verification, context={"request": request}).data)

    @action(detail=True, methods=["POST"])
    def approve(self, request, pk=None):
        verification = self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verification.status = LandlordVerification.Status.APPROVED
        verification.review_notes = serializer.validated_data.get("review_notes", "")
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save(update_fields=["status", "review_notes", "reviewed_by", "reviewed_at"])

        landlord = verification.landlord
        landlord.is_verified_landlord = True
        landlord.save(update_fields=["is_verified_landlord"])

        return Response({"message": "Landlord verification approved."})

    @action(detail=True, methods=["POST"])
    def reject(self, request, pk=None):
        verification = self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verification.status = LandlordVerification.Status.REJECTED
        verification.review_notes = serializer.validated_data.get("review_notes", "")
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save(update_fields=["status", "review_notes", "reviewed_by", "reviewed_at"])

        landlord = verification.landlord
        landlord.is_verified_landlord = False
        landlord.save(update_fields=["is_verified_landlord"])

        return Response({"message": "Landlord verification rejected."})
