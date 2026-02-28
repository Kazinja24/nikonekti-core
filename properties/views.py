from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from .models import Property, PropertyImage, Feature, PropertyReviewLog
from django.core.mail import send_mail
from django.conf import settings
from django.conf import settings
from .serializers import PropertySerializer, PropertyImageSerializer, FeatureSerializer
from users.permissions import IsLandlord, IsAdmin
from audit.utils import log_action


@extend_schema_view(
    list=extend_schema(tags=["Properties - Public"]),
    retrieve=extend_schema(tags=["Properties - Public"]),
    create=extend_schema(tags=["Properties - Landlord"]),
    update=extend_schema(tags=["Properties - Landlord"]),
    partial_update=extend_schema(tags=["Properties - Landlord"]),
    destroy=extend_schema(tags=["Properties - Landlord"]),
    upload_image=extend_schema(tags=["Properties - Landlord"]),
    upload_images=extend_schema(tags=["Properties - Landlord"]),
    delete_image=extend_schema(tags=["Properties - Landlord"]),
    set_cover=extend_schema(tags=["Properties - Landlord"]),
    reorder_images=extend_schema(tags=["Properties - Landlord"]),
    submit_ownership_document=extend_schema(tags=["Verification - Landlord"]),
    publish=extend_schema(tags=["Properties - Landlord"]),
    unpublish=extend_schema(tags=["Properties - Landlord"]),
    approve_verification=extend_schema(tags=["Verification - Admin"]),
    reject_verification=extend_schema(tags=["Verification - Admin"]),
)
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
        # Allow landlords to upload images before identity verification

        image = request.FILES.get("image")
        if not image:
            return Response({"error": "No image provided"}, status=400)

        # Validate size
        max_mb = getattr(settings, "IMAGE_MAX_SIZE_MB", 5)
        if image.size > max_mb * 1024 * 1024:
            return Response({"error": f"Image exceeds maximum size of {max_mb} MB"}, status=400)

        property_image = PropertyImage.objects.create(
            property=property_obj,
            image=image,
        )

        try:
            from audit.utils import log_action

            log_action(request, "property.image_uploaded", target=property_obj, data={"image_id": property_image.id})
        except Exception:
            pass

        serializer = PropertyImageSerializer(property_image, context={"request": request})
        return Response(serializer.data, status=201)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_images(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)
        # Allow landlords to upload images before identity verification

        images = request.FILES.getlist("images")
        if not images:
            single_image = request.FILES.get("image")
            if single_image:
                images = [single_image]

        if not images:
            return Response({"error": "No images provided"}, status=400)

        # Validate each image
        max_mb = getattr(settings, "IMAGE_MAX_SIZE_MB", 5)
        valid_images = []
        for image in images:
            if image.size > max_mb * 1024 * 1024:
                continue
            valid_images.append(image)

        if not valid_images:
            return Response({"error": f"No valid images found (max size {max_mb} MB)"}, status=400)

        created_images = [PropertyImage.objects.create(property=property_obj, image=image) for image in valid_images]

        try:
            from audit.utils import log_action

            log_action(request, "property.images_uploaded", target=property_obj, data={"count": len(created_images)})
        except Exception:
            pass

        serializer = PropertyImageSerializer(created_images, many=True, context={"request": request})
        return Response({"count": len(created_images), "images": serializer.data}, status=201)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsLandlord],
        parser_classes=[MultiPartParser, FormParser],
    )
    def submit_ownership_document(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        ownership_document = request.FILES.get("ownership_document")
        if not ownership_document:
            return Response({"error": "No ownership document provided"}, status=400)

        property_obj.ownership_document = ownership_document
        property_obj.verification_status = "pending"
        property_obj.verification_notes = ""
        property_obj.verified_by = None
        property_obj.verified_at = None
        property_obj.is_published = False
        property_obj.published_at = None
        property_obj.save()
        self._delete_property_images(property_obj)

        try:
            from audit.utils import log_action

            log_action(request, "property.ownership_document_submitted", target=property_obj, data={"property_id": getattr(property_obj, "id", None)})
        except Exception:
            pass

        serializer = self.get_serializer(property_obj)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsLandlord],
    )
    def publish(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        if not property_obj.can_be_published():
            return Response(
                {
                    "error": (
                        "Landlord identity and property ownership verification "
                        "must both be approved before publishing."
                    )
                },
                status=400,
            )
        if not self._has_active_paid_listing(property_obj.id):
            return Response(
                {"error": "An active paid listing is required before publishing this property."},
                status=400,
            )

        property_obj.is_published = True
        property_obj.published_at = timezone.now()
        property_obj.listing_status = "published"
        property_obj.approved_by = request.user
        property_obj.approved_at = timezone.now()
        property_obj.save(update_fields=["is_published", "published_at", "listing_status", "approved_by", "approved_at"])
        try:
            from audit.utils import log_action

            log_action(request, "property.published", target=property_obj, data={"property_id": getattr(property_obj, "id", None)})
        except Exception:
            pass
        return Response({"message": "Property published successfully."})

    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated, IsLandlord])
    def submit_for_review(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        # Basic validation: require at least one image
        if property_obj.images.count() == 0:
            return Response({"error": "At least one property image is required to submit for review."}, status=400)

        property_obj.listing_status = "pending_review"
        property_obj.submitted_by = request.user
        property_obj.admin_review_notes = ""
        property_obj.save(update_fields=["listing_status", "submitted_by", "admin_review_notes"])
        # Log submission
        try:
            PropertyReviewLog.objects.create(property=property_obj, action="submitted", admin=request.user, notes="Submitted by landlord")
        except Exception:
            pass
        try:
            from audit.utils import log_action

            log_action(request, "property.submitted_for_review", target=property_obj, data={"property_id": getattr(property_obj, "id", None)})
        except Exception:
            pass
        return Response({"message": "Property submitted for review."})

    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated, IsAdmin])
    def admin_approve_listing(self, request, pk=None):
        property_obj = self.get_object()

        property_obj.listing_status = "published"
        property_obj.is_published = True
        property_obj.published_at = timezone.now()
        property_obj.approved_by = request.user
        property_obj.approved_at = timezone.now()
        property_obj.admin_review_notes = request.data.get("admin_review_notes", "")
        property_obj.save(update_fields=[
            "listing_status",
            "is_published",
            "published_at",
            "approved_by",
            "approved_at",
            "admin_review_notes",
        ])
        # create review log
        try:
            PropertyReviewLog.objects.create(property=property_obj, action="approved", admin=request.user, notes=property_obj.admin_review_notes)
        except Exception:
            pass
        # notify landlord
        try:
            subject = f"Your listing '{property_obj.title}' has been approved"
            message = property_obj.admin_review_notes or "Your listing has been approved and is now published."
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            if property_obj.owner and property_obj.owner.email and from_email:
                send_mail(subject, message, from_email, [property_obj.owner.email])
        except Exception:
            pass
        return Response({"message": "Listing approved and published."})


    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated, IsAdmin])
    def admin_reject_listing(self, request, pk=None):
        property_obj = self.get_object()

        property_obj.listing_status = "rejected"
        property_obj.is_published = False
        property_obj.published_at = None
        property_obj.admin_review_notes = request.data.get("admin_review_notes", "")
        property_obj.approved_by = request.user
        property_obj.approved_at = timezone.now()
        property_obj.save(update_fields=[
            "listing_status",
            "is_published",
            "published_at",
            "admin_review_notes",
            "approved_by",
            "approved_at",
        ])
        # create review log
        try:
            PropertyReviewLog.objects.create(property=property_obj, action="rejected", admin=request.user, notes=property_obj.admin_review_notes)
        except Exception:
            pass
        # notify landlord
        try:
            subject = f"Your listing '{property_obj.title}' has been rejected"
            message = property_obj.admin_review_notes or "Your listing has been rejected by the admin. Please review the notes and resubmit."
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            if property_obj.owner and property_obj.owner.email and from_email:
                send_mail(subject, message, from_email, [property_obj.owner.email])
        except Exception:
            pass
        return Response({"message": "Listing rejected."})

    @action(detail=False, methods=["GET"], permission_classes=[IsAuthenticated, IsAdmin])
    def pending_reviews(self, request):
        qs = Property.objects.filter(listing_status="pending_review").order_by("-submitted_by", "-created_at")
        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["POST"], permission_classes=[IsAuthenticated, IsAdmin])
    def batch_approve(self, request):
        ids = request.data.get("ids", [])
        admin_notes = request.data.get("admin_review_notes", "")
        results = {"approved": [], "failed": []}
        for pid in ids:
            try:
                prop = Property.objects.get(id=pid)
                prop.listing_status = "published"
                prop.is_published = True
                prop.published_at = timezone.now()
                prop.approved_by = request.user
                prop.approved_at = timezone.now()
                prop.admin_review_notes = admin_notes
                prop.save(update_fields=["listing_status", "is_published", "published_at", "approved_by", "approved_at", "admin_review_notes"]) 
                PropertyReviewLog.objects.create(property=prop, action="approved", admin=request.user, notes=admin_notes)
                results["approved"].append(pid)
            except Exception:
                results["failed"].append(pid)
        return Response(results)

    @action(detail=False, methods=["POST"], permission_classes=[IsAuthenticated, IsAdmin])
    def batch_reject(self, request):
        ids = request.data.get("ids", [])
        admin_notes = request.data.get("admin_review_notes", "")
        results = {"rejected": [], "failed": []}
        for pid in ids:
            try:
                prop = Property.objects.get(id=pid)
                prop.listing_status = "rejected"
                prop.is_published = False
                prop.published_at = None
                prop.admin_review_notes = admin_notes
                prop.approved_by = request.user
                prop.approved_at = timezone.now()
                prop.save(update_fields=["listing_status", "is_published", "published_at", "admin_review_notes", "approved_by", "approved_at"]) 
                PropertyReviewLog.objects.create(property=prop, action="rejected", admin=request.user, notes=admin_notes)
                results["rejected"].append(pid)
            except Exception:
                results["failed"].append(pid)
        return Response(results)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsLandlord],
    )
    def unpublish(self, request, pk=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        property_obj.is_published = False
        property_obj.published_at = None
        property_obj.save(update_fields=["is_published", "published_at"])
        self._delete_property_images(property_obj)
        return Response({"message": "Property unpublished successfully."})

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsAdmin],
    )
    def approve_verification(self, request, pk=None):
        property_obj = self.get_object()

        if not property_obj.ownership_document:
            return Response({"error": "Ownership document is required before approval."}, status=400)

        property_obj.verification_status = "approved"
        property_obj.verification_notes = request.data.get("verification_notes", "")
        property_obj.verified_by = request.user
        property_obj.verified_at = timezone.now()
        property_obj.save(
            update_fields=["verification_status", "verification_notes", "verified_by", "verified_at"]
        )
        return Response({"message": "Property ownership verification approved."})

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsAdmin],
    )
    def reject_verification(self, request, pk=None):
        property_obj = self.get_object()

        property_obj.verification_status = "rejected"
        property_obj.verification_notes = request.data.get("verification_notes", "")
        property_obj.verified_by = request.user
        property_obj.verified_at = timezone.now()
        property_obj.is_published = False
        property_obj.published_at = None
        property_obj.save(
            update_fields=[
                "verification_status",
                "verification_notes",
                "verified_by",
                "verified_at",
                "is_published",
                "published_at",
            ]
        )
        self._delete_property_images(property_obj)
        return Response({"message": "Property ownership verification rejected."})

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated(), IsLandlord()]
        if self.action in [
            "update",
            "partial_update",
            "destroy",
            "upload_image",
            "upload_images",
            "delete_image",
            "set_cover",
            "reorder_images",
            "submit_ownership_document",
            "publish",
            "unpublish",
        ]:
            return [IsAuthenticated(), IsLandlord()]
        if self.action in ["approve_verification", "reject_verification"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Public and tenants should see published & verified properties regardless of paid listing status.
        # Paid listing status affects prioritization (priority_score) and featured placement, not basic visibility.
        base_qs = Property.objects.all()

        if not user or not user.is_authenticated:
            base_qs = base_qs.filter(status="available", is_published=True, verification_status="approved")
        elif user.role == "LANDLORD":
            base_qs = base_qs.filter(owner=user)
        elif user.role == "ADMIN":
            base_qs = base_qs
        else:
            # TENANT or other authenticated users
            base_qs = base_qs.filter(status="available", is_published=True, verification_status="approved")

        # Support query params for filtering and sorting on the listing endpoint
        params = self.request.query_params
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        location = params.get("location")
        bedrooms = params.get("bedrooms")
        property_type = params.get("property_type")
        features = params.get("features")  # comma separated feature ids
        sort = params.get("sort")  # 'priority', 'price_asc', 'price_desc', 'newest'

        if min_price:
            try:
                base_qs = base_qs.filter(price__gte=float(min_price))
            except Exception:
                pass
        if max_price:
            try:
                base_qs = base_qs.filter(price__lte=float(max_price))
            except Exception:
                pass
        if location:
            base_qs = base_qs.filter(location__icontains=location)
        if bedrooms:
            try:
                b = int(bedrooms)
                if b == 3:
                    base_qs = base_qs.filter(bedrooms__gte=3)
                else:
                    base_qs = base_qs.filter(bedrooms=b)
            except Exception:
                pass
        if property_type:
            base_qs = base_qs.filter(property_type__iexact=property_type)
        if features:
            try:
                ids = [int(x) for x in features.split(",") if x]
                if ids:
                    base_qs = base_qs.filter(features__id__in=ids).distinct()
            except Exception:
                pass

        # Sorting: default by priority_score desc then published_at desc
        if sort == "price_asc":
            base_qs = base_qs.order_by("price", "-priority_score")
        elif sort == "price_desc":
            base_qs = base_qs.order_by("-price", "-priority_score")
        elif sort == "newest":
            base_qs = base_qs.order_by("-published_at", "-priority_score")
        else:
            base_qs = base_qs.order_by("-priority_score", "-published_at")

        return base_qs

    def _ensure_owner(self, property_obj):
        if property_obj.owner != self.request.user:
            raise PermissionDenied("Only the owning landlord can modify this property.")

    def _ensure_verified_landlord(self):
        if not self.request.user.is_verified_landlord:
            raise PermissionDenied("Only verified landlords can upload property images.")

    def _delete_property_images(self, property_obj):
        for property_image in property_obj.images.all():
            if property_image.image:
                property_image.image.delete(save=False)
            if getattr(property_image, 'thumbnail', None):
                try:
                    property_image.thumbnail.delete(save=False)
                except Exception:
                    pass
            property_image.delete()

    def _has_active_paid_listing(self, property_id):
        from payments.models import ListingPaymentIntent

        return ListingPaymentIntent.has_active_paid_listing(property_id=property_id)

    def _active_paid_listing_property_ids(self):
        from payments.models import ListingPaymentIntent

        now = timezone.now()
        return ListingPaymentIntent.objects.filter(
            status__in=[
                ListingPaymentIntent.Status.CONFIRMED,
                ListingPaymentIntent.Status.OVERRIDDEN,
            ],
            expires_at__gt=now,
        ).values_list("property_id", flat=True)

    def perform_update(self, serializer):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_owner(instance)
        instance.delete()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="image_id",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
            )
        ]
    )
    @action(detail=True, methods=["DELETE"], url_path="delete-image/(?P<image_id>[^/.]+)")
    def delete_image(self, request, pk=None, image_id=None):
        property_obj = self.get_object()
        self._ensure_owner(property_obj)

        try:
            img = PropertyImage.objects.get(id=image_id, property=property_obj)
            if img.image:
                img.image.delete(save=False)
            if getattr(img, 'thumbnail', None):
                try:
                    img.thumbnail.delete(save=False)
                except Exception:
                    pass
            img.delete()
            return Response({"message": "Image deleted"}, status=204)
        except PropertyImage.DoesNotExist:
            return Response({"error": "Image not found"}, status=404)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="image_id",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
            )
        ]
    )
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

    @action(detail=False, methods=["GET"], permission_classes=[AllowAny])
    def config(self, request):
        """Get upload configuration for properties."""
        max_mb = getattr(settings, "IMAGE_MAX_SIZE_MB", 5)
        return Response({
            "image_max_size_mb": max_mb,
        })


class FeatureViewSet(viewsets.ModelViewSet):
    """Manage master list of property features/amenities."""
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]
