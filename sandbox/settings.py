import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY signs sessions and password-reset tokens. There is intentionally
# no default: set DJANGO_SECRET_KEY in the environment for any deployment.
# Generate one with:
#   ./venv/bin/python -c "from django.core.management.utils import \
#     get_random_secret_key; print(get_random_secret_key())"
# Rotating it invalidates existing sessions and pending reset links.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set. Export it before starting the app:\n"
        '  export DJANGO_SECRET_KEY="$(./venv/bin/python -c '
        "'from django.core.management.utils import get_random_secret_key; "
        'print(get_random_secret_key())\'"" )"\n'
        "See INSTALLATION_GUIDE.md section 3.4."
    )

# Never leave DEBUG on for a reachable deployment: it renders full tracebacks
# and settings on error pages.
DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}

# Comma-separated in the environment, e.g.
#   ALLOWED_HOSTS="somacloud.example.com,10.0.1.5"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,[::1]",
    ).split(",")
    if h.strip()
]

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
DOCKER_SERVER_PUBLIC_IP = os.getenv("DOCKER_SERVER_PUBLIC_IP", "127.0.0.1")
DOCKER_PORT_START = int(os.getenv("DOCKER_PORT_START", "9000"))
DOCKER_PORT_END = int(os.getenv("DOCKER_PORT_END", "9100"))

# Swarm manager IP for join commands. Required when running multi-node.
SWARM_MANAGER_IP = os.getenv("SWARM_MANAGER_IP", "")

# App server base URL (workers reach this for CA signing + token endpoints).
# Must be reachable *from the worker nodes*, not just from the app server.
APP_SERVER_URL = os.getenv("APP_SERVER_URL", "http://127.0.0.1:8000")

# ---------------------------------------------------------------------------
# Email / Password Reset
# ---------------------------------------------------------------------------
# Email / password reset
# ---------------------------------------------------------------------------
# No credentials live in this file. Supply them through the environment, e.g.
# in the systemd unit:
#
#   [Service]
#   Environment="EMAIL_HOST_USER=you@example.com"
#   Environment="EMAIL_HOST_PASSWORD=your-app-password"
#   EnvironmentFile=/etc/somacloud/env
#
# For Gmail use an App Password (not your account password), with 2FA enabled.
# Locally, override the backend to print mail to the terminal instead:
#
#   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
#
# Leaving EMAIL_HOST_PASSWORD unset disables outbound mail; password-reset
# links will then be logged rather than sent.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", f"SomaCloud <{EMAIL_HOST_USER or 'noreply@example.com'}>"
)

DOMAIN = os.getenv("DOMAIN", "127.0.0.1")
SITE_NAME = "SomaCloud"
