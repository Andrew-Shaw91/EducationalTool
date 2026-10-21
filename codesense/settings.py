"""
Django settings for CodeSense.

CodeSense is a research prototype for introductory programming education
in a generative-AI-rich environment. Settings stay deliberately simple
so the work can focus on pedagogical experimentation rather than
deployment complexity.

Configuration is read from environment variables, optionally supplied through
a `.env` file next to manage.py (see `.env.example`). With nothing set, the
defaults give a working local development setup: DEBUG on, localhost only,
SQLite in the project folder. Production values are described in DEPLOYMENT.md.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .envconfig import env_bool, env_int, env_list, env_str, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent

# Real environment variables always win over the file. CODESENSE_ENV_FILE lets
# tests (or an unusual server layout) point somewhere else.
load_env_file(Path(os.environ.get("CODESENSE_ENV_FILE") or BASE_DIR / ".env"))

# --- Core ------------------------------------------------------------------
# DEBUG defaults to True so a fresh checkout runs with `runserver`. On a server
# set DEBUG=False; the app then refuses to start without a real SECRET_KEY.
DEBUG = env_bool("DEBUG", True)

_DEV_SECRET_KEY = "django-insecure-codesense-development-only-never-use-in-production"
SECRET_KEY = env_str("SECRET_KEY") or _DEV_SECRET_KEY
if not DEBUG and SECRET_KEY.startswith(("django-insecure", "replace-me")):
    raise ImproperlyConfigured(
        "DEBUG is off but SECRET_KEY is missing or still a placeholder. Generate one with:\n"
        "  python3 -c \"import secrets; print(secrets.token_urlsafe(64))\"\n"
        "and put it in the .env file as SECRET_KEY=... (see DEPLOYMENT.md)."
    )

# Comma-separated host names / IP addresses the site may be served under,
# e.g. ALLOWED_HOSTS=203.0.113.10,example.org
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["127.0.0.1", "localhost"])

# Only needed once the site is served over HTTPS from a domain, as full origins:
# CSRF_TRUSTED_ORIGINS=https://example.org
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])

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

# --- Database --------------------------------------------------------------
# SQLite. DATABASE_PATH lets a server keep the database outside the code folder
# (so updating the code can never overwrite research data). Several gunicorn
# workers share the file, so outside DEBUG it uses write-ahead logging and
# takes the write lock up front, which avoids "database is locked" errors.
_sqlite_options = {"timeout": 20}
if not DEBUG:
    _sqlite_options.update(
        {
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
        }
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(env_str("DATABASE_PATH") or BASE_DIR / "db.sqlite3"),
        "OPTIONS": _sqlite_options,
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
# STATIC_ROOT with the web server (nginx, see deploy/).
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cookies, sessions and CSRF ---------------------------------------------
# USE_HTTPS=True once the site is served over HTTPS (it needs a domain name and
# a certificate). While the site is reachable only by plain-HTTP IP address it
# must stay False: browsers do not send "Secure" cookies over HTTP, which would
# break sessions (participant codes) and every form submission.
USE_HTTPS = env_bool("USE_HTTPS", False)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if USE_HTTPS:
    # nginx terminates TLS and forwards the original scheme in this header.
    # Gunicorn listens only on 127.0.0.1, so only nginx can set it.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # HSTS tells browsers to refuse plain HTTP for this long. Leave at 0 until
    # HTTPS is known to work, then raise (e.g. 3600, later 31536000).
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)

# --- Logging ----------------------------------------------------------------
# Everything goes to the console (gunicorn sends that to journald) and to
# logs/codesense.log. If the log folder cannot be written the app still runs
# with console logging only, rather than failing to start.
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "codesense.log"
LOG_LEVEL = env_str("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _log_file_ok = os.access(LOG_DIR, os.W_OK)
except OSError:
    _log_file_ok = False

_log_handlers = ["console"] + (["file"] if _log_file_ok else [])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        # WatchedFileHandler reopens the file if logrotate renames it, which
        # matters because several gunicorn workers write to the same file.
        **(
            {
                "file": {
                    "class": "logging.handlers.WatchedFileHandler",
                    "filename": str(LOG_FILE),
                    "encoding": "utf-8",
                    "formatter": "standard",
                }
            }
            if _log_file_ok
            else {}
        ),
    },
    "loggers": {
        # Request errors (4xx warnings, 5xx errors with tracebacks), security
        # events, template and migration problems.
        "django": {"handlers": _log_handlers, "level": "INFO", "propagate": False},
        # Application messages, e.g. the unusable-LLM-response warning.
        "practice": {"handlers": _log_handlers, "level": LOG_LEVEL, "propagate": False},
        "research": {"handlers": _log_handlers, "level": LOG_LEVEL, "propagate": False},
    },
    "root": {"handlers": _log_handlers, "level": "WARNING"},
}

# --- AI scaffolding (hints, explanations, follow-ups) ----------------------
# Supported values today: "mock"
AI_PROVIDER = "mock"

# --- Free-text assessment --------------------------------------------------
# "keyword": transparent offline baseline.
# "ai":      LLM-ready service; uses a mock reply while LLM_API_KEY is empty.
# Leave CODESENSE_LLM_API_KEY empty until a real LLM adapter has been written:
# with a key set and no adapter, the "ai" service has nothing to call.
FEEDBACK_SERVICE = env_str("CODESENSE_FEEDBACK_SERVICE", "keyword")
LLM_API_KEY = env_str("CODESENSE_LLM_API_KEY", "")

# --- Research data collection ----------------------------------------------
# Every option is documented in research/conf.py and every stored field in
# research/models.py. Set CODESENSE_ANALYTICS=0 to collect nothing at all.
RESEARCH = {
    "ANALYTICS_ENABLED": env_bool("CODESENSE_ANALYTICS", True),
    "STORE_RESPONSE_TEXT": env_bool("CODESENSE_STORE_RESPONSE_TEXT", True),
    "STORE_HINT_USAGE": env_bool("CODESENSE_STORE_HINT_USAGE", True),
    "STORE_TIMESTAMPS": env_bool("CODESENSE_STORE_TIMESTAMPS", True),
}
