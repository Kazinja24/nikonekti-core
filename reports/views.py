from django.core.exceptions import ValidationError
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from users.permissions import IsAdmin
from .models import PropertyReport, UserBlock
from .serializers import (
    PropertyReportSerializer,
    PropertyReportReviewSerializer,
    UserBlockSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Safety - Reports"]),
    retrieve=extend_schema(tags=["Safety - Reports"]),
    create=extend_schema(tags=["Safety - Reports"]),
    under_review=extend_schema(tags=["Safety - Admin"]),
    resolve=extend_schema(tags=["Safety - Admin"]),
    dismiss=extend_schema(tags=["Safety - Admin"]),
)
class PropertyReportViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PropertyReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = PropertyReport.objects.select_related("reporter", "property", "property__owner", "reviewed_by")

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return self.queryset
        if user.role == "LANDLORD":
            return self.queryset.filter(property__owner=user) | self.queryset.filter(reporter=user)
        return self.queryset.filter(reporter=user)

    def get_serializer_class(self):
        if self.action in ["under_review", "resolve", "dismiss"]:
            return PropertyReportReviewSerializer
        return PropertyReportSerializer

    def get_permissions(self):
        if self.action in ["under_review", "resolve", "dismiss"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=["POST"])
    def under_review(self, request, pk=None):
        report = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.review_notes = serializer.validated_data.get("review_notes", "")
        try:
            report.transition_to(PropertyReport.Status.UNDER_REVIEW, reviewed_by=request.user)
        except (ValueError, ValidationError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        report.save(update_fields=["review_notes"])
        return Response({"message": "Report moved to under review."})

    @action(detail=True, methods=["POST"])
    def resolve(self, request, pk=None):
        report = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.review_notes = serializer.validated_data.get("review_notes", "")
        try:
            report.transition_to(PropertyReport.Status.RESOLVED, reviewed_by=request.user)
        except (ValueError, ValidationError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        report.save(update_fields=["review_notes"])
        return Response({"message": "Report resolved."})

    @action(detail=True, methods=["POST"])
    def dismiss(self, request, pk=None):
        report = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.review_notes = serializer.validated_data.get("review_notes", "")
        try:
            report.transition_to(PropertyReport.Status.DISMISSED, reviewed_by=request.user)
        except (ValueError, ValidationError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        report.save(update_fields=["review_notes"])
        return Response({"message": "Report dismissed."})


@extend_schema_view(
    list=extend_schema(tags=["Safety - Blocks"]),
    retrieve=extend_schema(tags=["Safety - Blocks"]),
    create=extend_schema(tags=["Safety - Blocks"]),
    unblock=extend_schema(tags=["Safety - Blocks"]),
)
class UserBlockViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserBlockSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = UserBlock.objects.select_related("blocker", "blocked_user")

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return self.queryset
        return self.queryset.filter(blocker=user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(blocker=self.request.user, is_active=True)

    @action(detail=True, methods=["POST"])
    def unblock(self, request, pk=None):
        user_block = self.get_object()
        if request.user.role != "ADMIN" and user_block.blocker != request.user:
            return Response({"error": "Only the blocker can unblock this user."}, status=status.HTTP_403_FORBIDDEN)

        user_block.is_active = False
        user_block.save(update_fields=["is_active"])
        return Response({"message": "User unblocked."})
