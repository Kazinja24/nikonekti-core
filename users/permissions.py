from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, "is_authenticated", False) and user.role == "ADMIN")


class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, "is_authenticated", False) and user.role == "LANDLORD")


class IsTenant(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, "is_authenticated", False) and user.role == "TENANT")


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(getattr(user, "is_authenticated", False) and user.role == "AGENT")
