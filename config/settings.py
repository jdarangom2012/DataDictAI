from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-key-change-me")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Fernet key used to encrypt/decrypt DatabaseConnection.encrypted_credentials.
# Lives in env / Azure Key Vault at runtime — never in the repo, never logged.
# Documento 02 §5 / Documento 04 Parte A.1.
FERNET_KEY = env("FERNET_KEY", default=None)

# SSRF guard (Documento 04 Parte A.2): por defecto bloqueamos conexiones de clientes
# hacia rangos de IP privados/loopback/link-local. Solo True en dev/CI, donde nuestro
# propio stack (docker-compose) vive en una red privada. Nunca True en produccion.
ALLOW_PRIVATE_DB_HOSTS = env.bool("ALLOW_PRIVATE_DB_HOSTS", default=False)

# Motor de IA (ai_engine) — Documento 02 §6: solo recibe estructura, nunca filas de datos.
AI_API_KEY = env("AI_API_KEY", default=None)
AI_MODEL = env("AI_MODEL", default="gpt-4o-mini")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "connections",
    "introspection",
    "snapshots",
    "ai_engine",
    "exports",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://datadictai:datadictai@localhost:5432/datadictai",
    )
}

AUTH_USER_MODEL = "accounts.User"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Documento 04 Parte A.2 (broken authentication): verificacion de email
# obligatoria antes de poder conectar la primera base de datos. En modo
# "mandatory", allauth ademas bloquea el login hasta que se verifique.
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = False
LOGIN_REDIRECT_URL = "dashboard:home"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"

# Sin SMTP configurado en el MVP: consola en dev, override explicito en produccion.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@datadictai.dev")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis / Celery
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Documento 02 §4: la conexion al cliente nunca ocurre en una request sincrona,
# siempre via Celery. En tests puede forzarse a eager (config/settings via env).
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exception_handlers.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DataDict AI API",
    "DESCRIPTION": "API de DataDict AI — NautilusTech",
    "VERSION": "1.0.0",
}

# Ningun logger debe imprimir connection strings ni credenciales (Documento 04 Parte A.6).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
}
