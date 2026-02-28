from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from .authentication import EmailTokenObtainPairSerializer
from .serializers import RegisterSerializer, AuthResponseSerializer, ProfileSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model


@extend_schema(tags=["Auth - Authenticated"])
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {"role": user.role}

        # lazy imports to avoid circular imports at module import time
        from applications.models import RentalApplication
        from viewings.models import Viewing
        from leases.models import Lease
        from payments.models import Payment
        from properties.models import Property
        from messages.models import Conversation

        if user.role == "TENANT":
            data.update(
                {
                    "applications_count": RentalApplication.objects.filter(tenant=user).count(),
                    "viewings_count": Viewing.objects.filter(tenant=user).count(),
                    "leases_count": Lease.objects.filter(tenant=user).count(),
                    "payments_count": Payment.objects.filter(tenant=user).count(),
                    "conversations_count": Conversation.objects.filter(
                        Q(application__tenant=user) | Q(property_obj__owner=user) | Q(initiator=user)
                    ).count(),
                }
            )
        elif user.role == "LANDLORD":
            data.update(
                {
                    "properties_count": Property.objects.filter(owner=user).count(),
                    "applications_count": RentalApplication.objects.filter(property__owner=user).count(),
                    "viewings_count": Viewing.objects.filter(property__owner=user).count(),
                    "leases_count": Lease.objects.filter(landlord=user).count(),
                    "payments_count": Payment.objects.filter(property__owner=user).count(),
                    "conversations_count": Conversation.objects.filter(
                        Q(application__property__owner=user) | Q(property_obj__owner=user) | Q(initiator=user)
                    ).count(),
                }
            )
        else:
            # admin: provide some global counts
            User = get_user_model()
            data.update(
                {
                    "users_count": User.objects.count(),
                    "properties_count": Property.objects.count(),
                    "applications_count": RentalApplication.objects.count(),
                    "leases_count": Lease.objects.count(),
                }
            )

        return Response(data)


@extend_schema(tags=["Auth - Public"])
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_verified_landlord": user.is_verified_landlord,
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth - Authenticated"])
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProfileSerializer})
    def get(self, request):
        user = request.user
        data = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_verified_landlord": user.is_verified_landlord,
        }
        return Response(data)

@extend_schema(tags=["Auth - Public"])
class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
