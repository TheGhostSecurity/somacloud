import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-local-dev-key-change-me"
DEBUG = True
ALLOWED_HOSTS = []

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
]

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
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

# Docker Remote API. Docker is exposed with mutual TLS on this host.
DOCKER_HOST = os.getenv("DOCKER_HOST", "https://127.0.0.1:2376")
DOCKER_TLS_CERT_PATH = os.getenv("DOCKER_TLS_CERT_PATH", "/etc/docker/certs")
DOCKER_TLS_CA_FILE = os.getenv("DOCKER_TLS_CA_FILE", "ca.pem")
DOCKER_TLS_CERT_FILE = os.getenv("DOCKER_TLS_CERT_FILE", "client-cert.pem")
DOCKER_TLS_KEY_FILE = os.getenv("DOCKER_TLS_KEY_FILE", "client-key.pem")
DOCKER_TLS_VERIFY = os.getenv("DOCKER_TLS_VERIFY", "true").lower() in {"1", "true", "yes"}
DOCKER_API_TIMEOUT = int(os.getenv("DOCKER_API_TIMEOUT", "30"))
DOCKER_SERVER_PUBLIC_IP = os.getenv("DOCKER_SERVER_PUBLIC_IP", "192.168.1.3")
DOCKER_PUBLIC_SCHEME = os.getenv("DOCKER_PUBLIC_SCHEME", "http")
DOCKER_PORT_START = int(os.getenv("DOCKER_PORT_START", "9000"))
DOCKER_PORT_END = int(os.getenv("DOCKER_PORT_END", "9100"))
