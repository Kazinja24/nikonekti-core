from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Property, PropertyImage
from .serializers import PropertySerializer, PropertyImageSerializer
from users.permissions import IsLandlord


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        image = request.FILES.get("image")
        if not image:
            return Response({"error": "No image provided"}, status=400)

        property_image = PropertyImage.objects.create(
            property=property_obj,
            image=image,
        )

        serializer = PropertyImageSerializer(property_image, context={"request": request})
        return Response(serializer.data, status=201)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated(), IsLandlord()]
        if self.action in ["update", "partial_update", "destroy", "upload_image", "delete_image", "set_cover", "reorder_images"]:
            return [IsAuthenticated(), IsLandlord()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return Property.objects.filter(status="available")

        if user.role == "LANDLORD":
            return Property.objects.filter(owner=user)

        return Property.objects.filter(status="available")

    def _ensure_owner(self, property_obj):
        if property_obj.owner != self.request.user:
            raise PermissionDenied("Only the owning landlord can modify this property.")

    def perform_update(self, serializer):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_owner(instance)
        instance.delete()

    @action(detail=True, methods=["DELETE"], url_path="delete-image/(?P<image_id>[^/.]+)")
    def delete_image(self, request, pk=None, image_id=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        try:
            img = PropertyImage.objects.get(id=image_id, property=property_obj)
            img.delete()
            return Response({"message": "Image deleted"}, status=204)
        except PropertyImage.DoesNotExist:
            return Response({"error": "Image not found"}, status=404)

    @action(detail=True, methods=["POST"], url_path="set-cover/(?P<image_id>[^/.]+)")
    def set_cover(self, request, pk=None, image_id=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        try:
            selected = PropertyImage.objects.get(id=image_id, property=property_obj)
            # Remove old cover.
            PropertyImage.objects.filter(property=property_obj, is_cover=True).update(is_cover=False)
            selected.is_cover = True
            selected.save()
            return Response({"message": "Cover image set"})
        except PropertyImage.DoesNotExist:
            return Response({"error": "Image not found"}, status=404)

    @action(detail=True, methods=["POST"])
    def reorder_images(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        orders = request.data.get("orders", [])
        for item in orders:
            PropertyImage.objects.filter(
                id=item["id"],
                property=property_obj,
            ).update(order=item["order"])

        return Response({"message": "Images reordered"})
