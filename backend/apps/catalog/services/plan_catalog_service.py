from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.models import Operator, Plan
from apps.core.exceptions import DomainError, NotFoundError


def list_operators() -> QuerySet:
    return Operator.objects.order_by("name")


def list_plans(operator_id: UUID | None = None, include_inactive: bool = False) -> QuerySet:
    plans = Plan.objects.select_related("operator").order_by("operator__name", "name")
    if operator_id:
        plans = plans.filter(operator__public_id=operator_id)
    if not include_inactive:
        plans = plans.filter(is_active=True)
    return plans


def find_plan(plan_id: UUID) -> Plan:
    plan = Plan.objects.select_related("operator").filter(public_id=plan_id).first()
    if plan is None:
        raise NotFoundError("resource.not_found")
    return plan


def find_operator(operator_id: UUID) -> Operator:
    operator = Operator.objects.filter(public_id=operator_id).first()
    if operator is None:
        raise NotFoundError("resource.not_found")
    return operator


@transaction.atomic
def deactivate_plan(plan: Plan, actor, now: datetime | None = None) -> Plan:
    """Removes a plan from the quoter without deleting it, keeping its full price history."""
    if not plan.is_active:
        raise DomainError("plan.already_inactive")
    plan.is_active = False
    plan.save(update_fields=["is_active"])
    record_event(
        AuditAction.PLAN_DEACTIVATED,
        actor=actor,
        operator=plan.operator,
        target=plan,
        payload={"plan": plan.name},
        occurred_at=now or timezone.now(),
    )
    return plan
