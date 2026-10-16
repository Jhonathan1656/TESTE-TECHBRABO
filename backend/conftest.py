import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from apps.core.roles import ROLE_GROUP_NAMES, Role

TEST_PASSWORD = "test-pass-1234"


def create_user_with_role(username: str, role: Role | None) -> User:
    user = User.objects.create_user(username=username, password=TEST_PASSWORD, first_name=username)
    if role is not None:
        group, _ = Group.objects.get_or_create(name=ROLE_GROUP_NAMES[role])
        user.groups.add(group)
    return user


@pytest.fixture
def analyst_user(db) -> User:
    return create_user_with_role("analyst", Role.ANALYST)


@pytest.fixture
def reviewer_user(db) -> User:
    return create_user_with_role("reviewer", Role.REVIEWER)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def analyst_client(analyst_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(analyst_user)
    return client


@pytest.fixture
def reviewer_client(reviewer_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(reviewer_user)
    return client
