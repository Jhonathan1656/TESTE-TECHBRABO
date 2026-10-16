import os

from django.core.exceptions import ImproperlyConfigured

_REQUIRED = object()


def read_env_str(name: str, default: object = _REQUIRED) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if default is _REQUIRED:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return str(default)


def read_env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def read_env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def read_env_list(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]
