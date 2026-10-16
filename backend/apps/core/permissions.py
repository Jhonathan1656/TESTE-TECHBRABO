from rest_framework.permissions import BasePermission

from apps.core.messages import resolve_message
from apps.core.roles import Role, user_has_role


class IsAnalyst(BasePermission):
    message = resolve_message("auth.role_required")

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, Role.ANALYST)


class IsReviewer(BasePermission):
    message = resolve_message("auth.role_required")

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, Role.REVIEWER)
