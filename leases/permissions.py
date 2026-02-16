from rest_framework.permissions import BasePermission


class IsLeaseParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in [obj.tenant, obj.landlord]
