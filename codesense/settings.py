"""
Django settings for CodeSense.

CodeSense is a research prototype for introductory programming education
in a generative-AI-rich environment. Settings stay deliberately simple
so the work can focus on pedagogical experimentation rather than
deployment complexity.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-codesense-dissertation-prototype-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "practice",  # activity data (teaching content)
    "research",  # evaluation data (what participants did)
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

ROOT_URLCONF = "codesense.urls"

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
                "practice.context_processors.studio_context",
            ],
        },
    },
]

WSGI_APPLICATION = "codesense.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# --- Static files ----------------------------------------------------------
# Bootstrap, fonts and CSS are all vendored under /static, so the app runs
# with no internet connection. `runserver` serves them when DEBUG is True; for
# any other deployment run `python manage.py collectstatic` and serve
# STATIC_ROOT with the web server.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- AI scaffolding (hints, explanations, follow-ups) ----------------------
# Supported values today: "mock"
AI_PROVIDER = "mock"

# --- Free-text assessment --------------------------------------------------
# "keyword": transparent offline baseline.
# "ai":      LLM-ready service; uses a mock reply while LLM_API_KEY is empty.
FEEDBACK_SERVICE = os.environ.get("CODESENSE_FEEDBACK_SERVICE", "keyword")
LLM_API_KEY = os.environ.get("CODESENSE_LLM_API_KEY", "")

# --- Research data collection ----------------------------------------------
# Every option is documented in research/conf.py and every stored field in
# research/models.py. Set CODESENSE_ANALYTICS=0 to collect nothing at all.
RESEARCH = {
    "ANALYTICS_ENABLED": _env_flag("CODESENSE_ANALYTICS", True),
    "STORE_RESPONSE_TEXT": _env_flag("CODESENSE_STORE_RESPONSE_TEXT", True),
    "STORE_HINT_USAGE": _env_flag("CODESENSE_STORE_HINT_USAGE", True),
    "STORE_TIMESTAMPS": _env_flag("CODESENSE_STORE_TIMESTAMPS", True),
}
