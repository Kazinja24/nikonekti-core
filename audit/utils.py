from django.contrib.contenttypes.models import ContentType


def log_action(request, action: str, target=None, data: dict | None = None):
    """Create an AuditLog entry.

    - `request`: Django request (can be None)
    - `action`: short action string
    - `target`: model instance (optional)
    - `data`: extra JSON-serializable data (optional)
    """
    actor = None
    ip = None
    if request is not None:
        actor = getattr(request, "user", None) if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False) else None
        ip = request.META.get("REMOTE_ADDR")

    ct = None
    oid = None
    if target is not None:
        try:
            ct = ContentType.objects.get_for_model(type(target))
            oid = getattr(target, "id", getattr(target, "pk", None))
        except Exception:
            ct = None
            oid = None

    try:
        # import models lazily to avoid import-time app registry issues
        from .models import AuditLog

        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_content_type=ct,
            target_object_id=str(oid) if oid is not None else None,
            data=data,
            ip_address=ip,
        )
    except Exception:
        # never raise from logging
        return
