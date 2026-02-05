from django.shortcuts import render

# Create your views here.
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Property
from .serializers import PropertySerializer
from core.permissions import IsLandlord


class PropertyViewSet(ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsLandlord()]
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.role == 'landlord':
            return Property.objects.filter(owner=self.request.user)
        return Property.objects.filter(status='available')
