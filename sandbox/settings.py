import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-local-dev-key-change-me"
DEBUG = True
ALLOWED_HOSTS = ["16.192.120.187", "localhost", "127.0.0.1", "13.60.192.50", "16.16.138.119"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.PageViewMiddleware",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "sandbox.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "sandbox.wsgi.application"

# Database — PostgreSQL in production, SQLite for local dev fallback
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

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
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_REDIRECT_URL = "dashboard"
LOGIN_URL = "login"
LOGOUT_REDIRECT_URL = "home"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Docker Swarm multi-node configuration
# ---------------------------------------------------------------------------

# Manager node (this server) — used for swarm management and local fallback
DOCKER_HOST = os.getenv("DOCKER_HOST", "https://127.0.0.1:2376")
DOCKER_TLS_CERT_DIR = os.getenv("DOCKER_TLS_CERT_DIR", str(BASE_DIR / "certs"))
DOCKER_TLS_CA_FILE = os.getenv("DOCKER_TLS_CA_FILE", "ca.pem")
DOCKER_TLS_CERT_FILE = os.getenv("DOCKER_TLS_CERT_FILE", "cert.pem")
DOCKER_TLS_KEY_FILE = os.getenv("DOCKER_TLS_KEY_FILE", "key.pem")
DOCKER_TLS_VERIFY = os.getenv("DOCKER_TLS_VERIFY", "true").lower() in {"1", "true", "yes"}
DOCKER_API_TIMEOUT = int(os.getenv("DOCKER_API_TIMEOUT", "30"))

# Public-facing URL construction
DOCKER_PUBLIC_SCHEME = os.getenv("DOCKER_PUBLIC_SCHEME", "http")

# Deprecated single-node fallback (used only when no nodes are registered)
DOCKER_SERVER_PUBLIC_IP = os.getenv("DOCKER_SERVER_PUBLIC_IP", "192.168.1.3")
DOCKER_PORT_START = int(os.getenv("DOCKER_PORT_START", "9000"))
DOCKER_PORT_END = int(os.getenv("DOCKER_PORT_END", "9100"))

# Swarm manager IP for join commands
SWARM_MANAGER_IP = os.getenv("SWARM_MANAGER_IP", "16.192.120.187")

# App server base URL (workers reach this for CA signing + token endpoints)
APP_SERVER_URL = os.getenv("APP_SERVER_URL", "http://16.192.120.187:8000")
