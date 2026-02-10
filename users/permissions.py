from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "ADMIN"


class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "LANDLORD"


class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "TENANT"


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "AGENT"
