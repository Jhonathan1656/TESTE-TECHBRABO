from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent


def record_event(
    action: AuditAction,
    *,
    actor=None,
    operator=None,
    target=None,
    payload: dict | None = None,
    occurred_at=None,
) -> AuditEvent:
    return AuditEvent.objects.create(
        occurred_at=occurred_at or timezone.now(),
        actor=actor if actor is not None and actor.is_authenticated else None,
        action=action,
        operator=operator,
        target_type=target._meta.model_name if target is not None else "",
        target_public_id=getattr(target, "public_id", None),
        payload=payload or {},
    )


def list_recent_events(limit: int = 30, target_public_id=None, operator=None):
    events = AuditEvent.objects.select_related("actor", "operator")
    if target_public_id is not None:
        events = events.filter(target_public_id=target_public_id)
    if operator is not None:
        events = events.filter(operator=operator)
    return events[:limit]
