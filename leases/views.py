from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.permissions import IsLandlord, IsTenant
from .models import Lease
from .permissions import IsLeaseParticipant
from .serializers import LeaseSerializer


class LeaseViewSet(viewsets.ModelViewSet):
    queryset = Lease.objects.all()
    serializer_class = LeaseSerializer

    def get_permissions(self):
        if self.action in ["create", "upload_contract", "activate"]:
            return [IsLandlord()]
        if self.action == "sign":
            return [IsTenant()]
        return [IsLeaseParticipant()]

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.tenant:
            return Response({"error": "Only tenant can sign lease"}, status=403)

        if lease.status not in {"LEASED", "ACTIVE"}:
            return Response({"error": "Only leased or active contracts can be signed"}, status=400)

        lease.is_signed = True
        lease.signed_at = timezone.now()
        lease.save(update_fields=["is_signed", "signed_at"])
        return Response({"message": "Lease signed"})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can activate lease"}, status=403)
        if lease.status != "LEASED":
            return Response({"error": "Only leased contracts can be activated"}, status=400)
        if not lease.is_signed:
            return Response({"error": "Lease must be signed before activation"}, status=400)

        lease.status = "ACTIVE"
        lease.save(update_fields=["status"])

        if lease.application and lease.application.status == "LEASED":
            lease.application.status = "ACTIVE"
            lease.application.save(update_fields=["status"])

        return Response({"message": "Lease activated"})

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        lease = self.get_object()
        if request.user != lease.landlord:
            return Response({"error": "Only landlord can terminate lease"}, status=403)

        lease.status = "CLOSED"
        lease.terminated_at = timezone.now()
        lease.save(update_fields=["status", "terminated_at"])

        if lease.application and lease.application.status == "ACTIVE":
            lease.application.status = "CLOSED"
            lease.application.save(update_fields=["status"])

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
        return Response({"message": "Contract uploaded successfully"})

    @action(detail=True, methods=["get"], url_path="contract")
    def download_contract(self, request, pk=None):
        lease = self.get_object()
        if request.user not in [lease.landlord, lease.tenant]:
            return Response({"error": "Not allowed to access this contract"}, status=403)

        if not lease.contract_file:
            return Response({"error": "Contract not uploaded"}, status=404)

        return FileResponse(open(lease.contract_file.path, "rb"), content_type="application/pdf")
