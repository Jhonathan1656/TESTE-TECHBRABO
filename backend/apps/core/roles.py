from enum import StrEnum


class Role(StrEnum):
    ANALYST = "analyst"
    REVIEWER = "reviewer"


ROLE_GROUP_NAMES: dict[Role, str] = {
    Role.ANALYST: "analysts",
    Role.REVIEWER: "reviewers",
}

# Reviewers can do everything analysts do, plus publish and reject batches.
_IMPLIED_ROLES: dict[Role, set[Role]] = {Role.REVIEWER: {Role.ANALYST}}


def find_user_roles(user) -> set[Role]:
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return set(Role)
    group_to_role = {group_name: role for role, group_name in ROLE_GROUP_NAMES.items()}
    direct_roles = {
        group_to_role[name]
        for name in user.groups.values_list("name", flat=True)
        if name in group_to_role
    }
    implied = set().union(*(_IMPLIED_ROLES.get(role, set()) for role in direct_roles))
    return direct_roles | implied


def user_has_role(user, role: Role) -> bool:
    return role in find_user_roles(user)
