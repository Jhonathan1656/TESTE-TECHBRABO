from dataclasses import dataclass

from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from apps.core.exceptions import DomainError


@dataclass(frozen=True)
class AuthSession:
    token: str
    user: object


def start_session(username: str, password: str) -> AuthSession:
    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        raise DomainError("auth.invalid_credentials")
    token, _ = Token.objects.get_or_create(user=user)
    return AuthSession(token=token.key, user=user)


def end_session(user) -> None:
    Token.objects.filter(user=user).delete()


def find_display_name(user) -> str:
    return user.get_full_name() or user.get_username()
