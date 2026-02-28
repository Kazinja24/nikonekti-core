from rest_framework import permissions


class IsPaymentOwnerOrAdmin(permissions.BasePermission):
    """Allow access to payments only for admins, the tenant who owns the payment,
    or the landlord who owns the related property.

    This is an object-level permission and should be used alongside
    `IsAuthenticated` to protect `Payment` detail views.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", "").upper()
        if role == "ADMIN":
            return True

        if role == "TENANT":
            # tenant may access their own payments
            return getattr(obj, "tenant_id", None) == user.id

        if role == "LANDLORD":
            # landlord may access payments for properties they own
            prop = getattr(obj, "property", None)
            return prop is not None and getattr(prop, "owner_id", None) == user.id

        return False
