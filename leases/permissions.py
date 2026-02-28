from rest_framework.permissions import BasePermission


class IsLeaseParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "role", None) == "ADMIN":
            return True
        return user in [obj.tenant, obj.landlord]
