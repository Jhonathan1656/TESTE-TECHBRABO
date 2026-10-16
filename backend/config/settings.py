from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from config.env import read_env_bool, read_env_int, read_env_list, read_env_str

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env", override=False)

DEBUG = read_env_bool("DJANGO_DEBUG", default=False)
SECRET_KEY = read_env_str("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = read_env_list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = read_env_list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.core",
    "apps.audit",
    "apps.catalog",
    "apps.sources",
    "apps.ans_reference",
    "apps.ingestion",
    "apps.quality",
    "apps.pricing",
    "apps.monitoring",
    "apps.demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": read_env_str("POSTGRES_DB", default="cotador"),
        "USER": read_env_str("POSTGRES_USER", default="cotador"),
        "PASSWORD": read_env_str("POSTGRES_PASSWORD"),
        "HOST": read_env_str("POSTGRES_HOST", default="localhost"),
        "PORT": read_env_int("POSTGRES_PORT", default=5432),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = Path(read_env_str("MEDIA_ROOT", default=str(BASE_DIR / "media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.handle_api_exception",
}

MAX_DOCUMENT_BYTES = read_env_int("MAX_DOCUMENT_BYTES", default=20 * 1024 * 1024)

ANS_OPEN_DATA_BASE_URL = read_env_str(
    "ANS_OPEN_DATA_BASE_URL", default="https://dadosabertos.ans.gov.br/FTP/PDA"
)

ANTHROPIC_API_KEY = read_env_str("ANTHROPIC_API_KEY", default="")
LLM_EXTRACTION_MODEL = read_env_str("LLM_EXTRACTION_MODEL", default="claude-opus-5-5")

DEMO_MODE = read_env_bool("DEMO_MODE", default=False)
DEMO_PASSWORD = read_env_str("DEMO_PASSWORD", default="")

QUALITY_THRESHOLDS = {
    "large_variation_pct": Decimal("25"),
    "non_uniform_tolerance_pp": Decimal("1.0"),
    "decimal_shift_tolerance": Decimal("0.15"),
    "late_capture_days": 1,
}
MONITORING_STALE_TABLE_DAYS = read_env_int("MONITORING_STALE_TABLE_DAYS", default=365)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
