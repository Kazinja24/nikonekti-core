from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.contenttypes.models import ContentType
from django.utils.dateparse import parse_datetime, parse_date
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, time

from .models import AuditLog
from .serializers import AuditLogSerializer


class IsAdminOrOwner:
    def __call__(self, request, view):
        # placeholder: use in get_permissions items
        return None


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor", "target_content_type").all()
    serializer_class = AuditLogSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        # Admins can see all logs
        if getattr(user, "role", "").upper() == "ADMIN":
            return qs

        # Allow users to see logs where they are the actor
        qs_user = qs.filter(actor=user)

        # Optionally allow users to see logs about a target object.
        target = self.request.query_params.get("target")
        target_id = self.request.query_params.get("target_id")
        if target and target_id:
            try:
                ct = ContentType.objects.get(model=target)
                qs_target = qs.filter(target_content_type=ct, target_object_id=str(target_id))
                qs = (qs_user | qs_target).distinct()
            except ContentType.DoesNotExist:
                qs = qs_user
        else:
            qs = qs_user

        action_prefix = self.request.query_params.get("action_prefix")
        if action_prefix:
            qs = qs.filter(action__istartswith=action_prefix)

        action_name = self.request.query_params.get("action")
        if action_name:
            qs = qs.filter(action__iexact=action_name)

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(target_content_type__model=entity_type.lower())

        entity_id = self.request.query_params.get("entity_id")
        if entity_id:
            qs = qs.filter(target_object_id=str(entity_id))

        created_from = self.request.query_params.get("created_from")
        if created_from:
            from_dt = parse_datetime(created_from)
            if from_dt is None:
                from_date = parse_date(created_from)
                if from_date is not None:
                    from_dt = timezone.make_aware(datetime.combine(from_date, time.min))
            if from_dt is not None:
                qs = qs.filter(created_at__gte=from_dt)

        created_to = self.request.query_params.get("created_to")
        if created_to:
            to_dt = parse_datetime(created_to)
            if to_dt is None:
                to_date = parse_date(created_to)
                if to_date is not None:
                    to_dt = timezone.make_aware(datetime.combine(to_date, time.max))
            if to_dt is not None:
                qs = qs.filter(created_at__lte=to_dt)

        return qs

    @action(detail=False, methods=["GET"], url_path="lifecycle")
    def lifecycle(self, request):
        lifecycle_query = (
            Q(action__istartswith="offer.")
            | Q(action__istartswith="lease.")
            | Q(action__istartswith="invoice.")
            | Q(action__istartswith="listing_intent.")
            | Q(action__istartswith="property.")
            | Q(action__istartswith="application.")
            | Q(action__istartswith="viewing.")
        )
        queryset = self.filter_queryset(self.get_queryset().filter(lifecycle_query))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
