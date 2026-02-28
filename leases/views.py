from django.http import FileResponse
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from users.permissions import IsLandlord, IsTenant
from .models import Lease
from .permissions import IsLeaseParticipant
from .serializers import LeaseSerializer
from audit.utils import log_action


@extend_schema_view(
    list=extend_schema(tags=["Leases - Tenant/Landlord/Admin"]),
    retrieve=extend_schema(tags=["Leases - Tenant/Landlord/Admin"]),
    create=extend_schema(tags=["Leases - Landlord"]),
    sign=extend_schema(tags=["Leases - Tenant"]),
    landlord_confirm=extend_schema(tags=["Leases - Landlord"]),
    activate=extend_schema(tags=["Leases - Landlord"]),
    terminate=extend_schema(tags=["Leases - Landlord"]),
    close=extend_schema(tags=["Leases - Landlord"]),
    upload_contract=extend_schema(tags=["Leases - Landlord"]),
    download_contract=extend_schema(tags=["Leases - Tenant/Landlord"]),
)
class LeaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Lease.objects.all()
    serializer_class = LeaseSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Lease.objects.none()
        if user.role == "ADMIN":
            return Lease.objects.all()
        if user.role == "LANDLORD":
            return Lease.objects.filter(landlord=user)
        if user.role == "TENANT":
            return Lease.objects.filter(tenant=user)
        return Lease.objects.none()

    def get_permissions(self):
        if self.action in ["create", "upload_contract", "activate", "landlord_confirm"]:
            return [IsLandlord()]
        if self.action == "sign":
            return [IsTenant()]
        return [IsLeaseParticipant()]

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.tenant:
            return Response({"error": "Only tenant can sign lease"}, status=403)

        if lease.status != Lease.Status.PENDING:
            return Response({"error": "Only pending contracts can be signed"}, status=400)

        if lease.tenant_confirmed_at:
            return Response({"message": "Tenant already confirmed lease."})

        lease.mark_tenant_confirmed()
        try:
            from audit.utils import log_action

            log_action(request, "lease.tenant_confirmed", target=lease, data={"lease_id": str(lease.id)})
        except Exception:
            pass
        return Response({"message": "Tenant confirmation recorded."})

    @action(detail=True, methods=["post"])
    def landlord_confirm(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can confirm lease"}, status=403)

        if lease.status != Lease.Status.PENDING:
            return Response({"error": "Only pending contracts can be confirmed"}, status=400)

        if lease.landlord_confirmed_at:
            return Response({"message": "Landlord already confirmed lease."})

        lease.mark_landlord_confirmed()
        try:
            from audit.utils import log_action

            log_action(request, "lease.landlord_confirmed", target=lease, data={"lease_id": str(lease.id)})
        except Exception:
            pass
        return Response({"message": "Landlord confirmation recorded."})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can activate lease"}, status=403)
        if lease.status != Lease.Status.PENDING:
            return Response({"error": "Only pending contracts can be activated"}, status=400)
        if not lease.is_fully_confirmed():
            return Response({"error": "Both tenant and landlord confirmations are required before activation."}, status=400)

        try:
            with transaction.atomic():
                lease.transition_to(Lease.Status.ACTIVE)

                # Lock the property lifecycle to rented once an agreement is active.
                property_obj = lease.property
                property_update_fields = []
                if property_obj.status != "rented":
                    property_obj.status = "rented"
                    property_update_fields.append("status")
                if property_obj.is_published:
                    property_obj.is_published = False
                    property_obj.published_at = None
                    property_update_fields.extend(["is_published", "published_at"])
                if property_update_fields:
                    property_obj.save(update_fields=property_update_fields)

                # Close competing applications and viewing requests on the same property.
                active_statuses = [Lease.Status.PENDING, Lease.Status.ACTIVE]
                has_other_active_lease = Lease.objects.filter(
                    property=property_obj,
                    status__in=active_statuses,
                ).exclude(id=lease.id).exists()

                if has_other_active_lease:
                    raise ValidationError("Property already has an active or pending lease.")

                from applications.models import RentalApplication
                from viewings.models import Viewing

                RentalApplication.objects.filter(
                    property=property_obj,
                    status__in=[RentalApplication.Status.PENDING, RentalApplication.Status.APPROVED],
                ).exclude(id=lease.application_id).update(
                    status=RentalApplication.Status.EXPIRED,
                    decided_at=timezone.now(),
                    landlord_note="Closed automatically because the property has been rented.",
                )

                Viewing.objects.filter(
                    property=property_obj,
                    status__in=[Viewing.Status.PENDING, Viewing.Status.APPROVED],
                ).exclude(application_id=lease.application_id).update(
                    status=Viewing.Status.REJECTED
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            log_action(request, "lease.activated", target=lease, data={"lease_id": str(lease.id)})
        except Exception:
            pass
        return Response({"message": "Lease activated"})

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can terminate lease"}, status=403)

        try:
            lease.transition_to(Lease.Status.TERMINATED)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            log_action(request, "lease.terminated", target=lease, data={"lease_id": str(lease.id)})
        except Exception:
            pass
        return Response({"message": "Lease terminated"})

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self.terminate(request, pk=pk)

    @action(detail=True, methods=["post"], url_path="upload-contract")
    def upload_contract(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can upload contract"}, status=403)

        file_obj = request.FILES.get("contract_file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=400)

        lease.contract_file = file_obj
        lease.save(update_fields=["contract_file"])
        try:
            from audit.utils import log_action

            log_action(request, "lease.contract_uploaded", target=lease, data={"lease_id": str(lease.id)})
        except Exception:
            pass
        return Response({"message": "Contract uploaded successfully"})

    @action(detail=True, methods=["get"], url_path="contract")
    def download_contract(self, request, pk=None):
        lease = self.get_object()
        if request.user not in [lease.landlord, lease.tenant]:
            return Response({"error": "Not allowed to access this contract"}, status=403)

        if not lease.contract_file:
            return Response({"error": "Contract not uploaded"}, status=404)

        return FileResponse(open(lease.contract_file.path, "rb"), content_type="application/pdf")

    @action(detail=True, methods=["post"], url_path="generate-contract")
    def generate_contract(self, request, pk=None):
        lease = self.get_object()
        # only landlord can generate contract
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can generate contract"}, status=403)

        # Try to generate PDF using reportlab
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except Exception:
            return Response({"error": "PDF generation not available on server. Please install reportlab."}, status=501)

        from io import BytesIO
        from django.core.files.base import ContentFile

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        text = c.beginText(40, 800)
        text.setFont("Helvetica", 12)
        text.textLine("Lease Agreement")
        text.textLine("")
        text.textLine(f"Property: {lease.property.title}")
        text.textLine(f"Landlord: {lease.landlord.email}")
        text.textLine(f"Tenant: {lease.tenant.email}")
        text.textLine(f"Start Date: {lease.start_date}")
        text.textLine(f"End Date: {lease.end_date}")
        text.textLine(f"Monthly Rent: {lease.monthly_rent}")
        text.textLine(f"Security Deposit: {lease.security_deposit}")
        text.textLine("")
        text.textLine("Terms:")
        text.textLine("1. The tenant agrees to pay rent on time.")
        text.textLine("2. The landlord agrees to maintain the property.")
        c.drawText(text)
        c.showPage()
        c.save()

        buffer.seek(0)
        file_content = buffer.getvalue()
        filename = f"lease_{lease.id}.pdf"
        lease.contract_file.save(filename, ContentFile(file_content))
        lease.save(update_fields=["contract_file"])
        try:
            from audit.utils import log_action

            log_action(request, "lease.contract_generated", target=lease, data={"lease_id": str(lease.id)})
        except Exception:
            pass

        return Response({"message": "Contract generated and uploaded."})
