from django.utils import timezone
from django.db.models import Q
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from applications.models import RentalApplication
from reports.models import UserBlock
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    OpenConversationSerializer,
)
from properties.models import Property
from audit.utils import log_action


@extend_schema_view(
    list=extend_schema(tags=["Messaging - Tenant/Landlord"]),
    retrieve=extend_schema(tags=["Messaging - Tenant/Landlord"]),
    open=extend_schema(tags=["Messaging - Tenant/Landlord"]),
)
class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Conversation.objects.select_related(
        "application",
        "application__tenant",
        "application__property",
        "application__property__owner",
        "property_obj",
        "initiator",
    )

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            Q(application__tenant=user)
            | Q(application__property__owner=user)
            | Q(property_obj__owner=user)
            | Q(initiator=user)
        )

    def get_serializer_class(self):
        if self.action == "open":
            return OpenConversationSerializer
        return ConversationSerializer

    def _is_blocked_between(self, user_a, user_b):
        return UserBlock.objects.filter(
            is_active=True,
        ).filter(
            Q(blocker=user_a, blocked_user=user_b) | Q(blocker=user_b, blocked_user=user_a)
        ).exists()

    @action(detail=False, methods=["POST"])
    def open(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Support opening by application_id or property_id
        app_id = serializer.validated_data.get("application_id")
        prop_id = serializer.validated_data.get("property_id")

        if app_id:
            application = RentalApplication.objects.select_related("tenant", "property", "property__owner").filter(
                id=app_id
            ).first()
            if not application:
                return Response({"error": "Application not found."}, status=404)

            if request.user != application.tenant and request.user != application.property.owner:
                return Response({"error": "Not allowed for this application."}, status=403)
            if self._is_blocked_between(application.tenant, application.property.owner):
                return Response({"error": "Conversation unavailable because one user has blocked the other."}, status=403)

            conversation, _ = Conversation.objects.get_or_create(application=application)
            output = ConversationSerializer(conversation, context={"request": request}).data
            try:
                from audit.utils import log_action

                log_action(request, "conversation.opened", target=conversation, data={"application_id": app_id})
            except Exception:
                pass
            return Response(output)

        if prop_id:
            prop = Property.objects.select_related("owner").filter(id=prop_id).first()
            if not prop:
                return Response({"error": "Property not found."}, status=404)

            # Prevent opening conversation with yourself if owner
            if request.user == prop.owner:
                return Response({"error": "Owner cannot open a contact conversation to themselves."}, status=400)

            if self._is_blocked_between(request.user, prop.owner):
                return Response({"error": "Conversation unavailable because one user has blocked the other."}, status=403)

            conversation, created = Conversation.objects.get_or_create(property_obj=prop, initiator=request.user)
            output = ConversationSerializer(conversation, context={"request": request}).data
            try:
                from audit.utils import log_action

                log_action(request, "conversation.opened", target=conversation, data={"property_id": prop_id})
            except Exception:
                pass
            return Response(output)

        return Response({"error": "application_id or property_id is required."}, status=400)


@extend_schema_view(
    list=extend_schema(tags=["Messaging - Tenant/Landlord"]),
    create=extend_schema(tags=["Messaging - Tenant/Landlord"]),
    mark_read=extend_schema(tags=["Messaging - Tenant/Landlord"]),
)
class MessageViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.select_related(
        "conversation",
        "conversation__application",
        "conversation__application__tenant",
        "conversation__application__property__owner",
        "conversation__property_obj__owner",
        "sender",
    )

    def get_queryset(self):
        user = self.request.user
        base_qs = self.queryset.filter(
            Q(conversation__application__tenant=user)
            | Q(conversation__application__property__owner=user)
            | Q(conversation__property_obj__owner=user)
            | Q(conversation__initiator=user)
        )

        conversation_id = self.request.query_params.get("conversation")
        if conversation_id:
            base_qs = base_qs.filter(conversation_id=conversation_id)
        return base_qs.order_by("created_at")

    def _is_blocked_between(self, user_a, user_b):
        return UserBlock.objects.filter(
            is_active=True,
        ).filter(
            Q(blocker=user_a, blocked_user=user_b) | Q(blocker=user_b, blocked_user=user_a)
        ).exists()

    def create(self, request, *args, **kwargs):
        conversation_id = request.data.get("conversation")
        if not conversation_id:
            return Response({"error": "conversation is required."}, status=400)

        conversation = Conversation.objects.select_related(
            "application",
            "application__tenant",
            "application__property__owner",
            "property_obj__owner",
        ).filter(id=conversation_id).first()
        if not conversation:
            return Response({"error": "Conversation not found."}, status=404)

        # Participant check: allow application-based participants or property-based initiator/owner
        tenant = conversation.tenant
        landlord = conversation.landlord
        if request.user != tenant and request.user != landlord:
            return Response({"error": "Not a participant in this conversation."}, status=403)
        if tenant and landlord and self._is_blocked_between(tenant, landlord):
            return Response({"error": "Messaging disabled because one user has blocked the other."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(sender=request.user, conversation=conversation)

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        try:
            from audit.utils import log_action

            log_action(request, "message.sent", target=conversation, data={"conversation_id": conversation.id, "sender_id": getattr(request.user, "id", None)})
        except Exception:
            pass

        return Response(serializer.data, status=201)

    @action(detail=True, methods=["POST"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        message = self.get_object()

        if message.sender_id == request.user.id:
            return Response({"error": "You cannot mark your own message as read."}, status=400)

        if not message.is_read:
            message.mark_as_read()

        return Response({"message": "Message marked as read."})
