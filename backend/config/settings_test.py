import os
import tempfile
from pathlib import Path

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")

from config.settings import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MIDDLEWARE = [entry for entry in MIDDLEWARE if "whitenoise" not in entry]  # noqa: F405
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="cotador-test-media-"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Unroutable endpoints and fake credentials: no test may reach a real external service.
ANS_OPEN_DATA_BASE_URL = "http://localhost:1/ans"
ANTHROPIC_API_KEY = ""

DEMO_MODE = True
DEMO_PASSWORD = "test-demo-password"
