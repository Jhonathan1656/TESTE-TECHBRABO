import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from apps.core.roles import Role
from conftest import TEST_PASSWORD, create_user_with_role

pytestmark = pytest.mark.django_db


def test_login_returns_token_and_roles(api_client, reviewer_user):
    response = api_client.post(
        "/api/auth/login", {"username": "reviewer", "password": TEST_PASSWORD}, format="json"
    )

    assert response.status_code == 200
    assert response.data["token"] == Token.objects.get(user=reviewer_user).key
    assert response.data["user"]["roles"] == ["analyst", "reviewer"]


def test_login_with_wrong_password_returns_translated_error(api_client, analyst_user):
    response = api_client.post(
        "/api/auth/login", {"username": "analyst", "password": "wrong"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["code"] == "auth.invalid_credentials"
    assert response.data["detail"] == "Usuário ou senha inválidos."


def test_current_user_requires_authentication(api_client):
    assert api_client.get("/api/auth/me").status_code == 401


def test_logout_revokes_token(api_client, analyst_user):
    token = Token.objects.create(user=analyst_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = api_client.post("/api/auth/logout")

    assert response.status_code == 204
    assert not Token.objects.filter(user=analyst_user).exists()


def test_health_is_public(api_client):
    assert api_client.get("/api/health").data == {"status": "ok"}


def test_user_without_role_has_no_roles(api_client):
    create_user_with_role("guest", None)
    response = api_client.post(
        "/api/auth/login", {"username": "guest", "password": TEST_PASSWORD}, format="json"
    )

    assert response.data["user"]["roles"] == []
    assert User.objects.filter(username="guest").exists()


def test_superuser_has_every_role():
    from apps.core.roles import find_user_roles

    admin = User.objects.create_superuser("root", password=TEST_PASSWORD)

    assert find_user_roles(admin) == set(Role)
