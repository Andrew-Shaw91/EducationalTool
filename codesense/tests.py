"""
Deployment-readiness tests: environment handling, production settings, logging
and the files shipped in deploy/. They do not touch educational behaviour.

Settings are checked in a subprocess because they are evaluated once at import
time; each run gets a clean environment so a developer's own .env or shell
variables cannot change the result.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

from codesense.envconfig import env_bool, env_int, env_list, env_str, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent
GOOD_KEY = "k8Jf2-test-only-5Hq9ZxW3vLm7Rt1YcNb4Ua6PdGs0EoXiTzVhKyQwBjMnFlAr"

PROBE = (
    "import os, json;"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codesense.settings');"
    "from django.conf import settings as s;"
    "print(json.dumps({"
    "'DEBUG': s.DEBUG, 'ALLOWED_HOSTS': s.ALLOWED_HOSTS,"
    "'CSRF_TRUSTED_ORIGINS': s.CSRF_TRUSTED_ORIGINS,"
    "'SESSION_COOKIE_SECURE': s.SESSION_COOKIE_SECURE,"
    "'CSRF_COOKIE_SECURE': s.CSRF_COOKIE_SECURE,"
    "'SESSION_COOKIE_HTTPONLY': s.SESSION_COOKIE_HTTPONLY,"
    "'SSL_REDIRECT': getattr(s, 'SECURE_SSL_REDIRECT', False),"
    "'PROXY_HEADER': getattr(s, 'SECURE_PROXY_SSL_HEADER', None),"
    "'DB': str(s.DATABASES['default']['NAME']),"
    "'DB_OPTIONS': s.DATABASES['default']['OPTIONS'],"
    "'LLM_KEY': s.LLM_API_KEY, 'SECRET_KEY': s.SECRET_KEY,"
    "'STATIC_ROOT': str(s.STATIC_ROOT)}))"
)


UNWRITABLE_LOG_PROBE = '''
import json, os, pathlib
os.environ["DJANGO_SETTINGS_MODULE"] = "codesense.settings"
original = pathlib.Path.mkdir
def blocked(self, *args, **kwargs):
    if self.name == "logs":
        raise PermissionError("read-only")
    return original(self, *args, **kwargs)
pathlib.Path.mkdir = blocked
from django.conf import settings
print(json.dumps(sorted(settings.LOGGING["handlers"])))
'''


def clean_env(**extra):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {
            "DEBUG", "SECRET_KEY", "ALLOWED_HOSTS", "USE_HTTPS", "DATABASE_PATH",
            "CSRF_TRUSTED_ORIGINS", "LOG_LEVEL", "SECURE_HSTS_SECONDS",
            "CODESENSE_LLM_API_KEY", "CODESENSE_FEEDBACK_SERVICE", "CODESENSE_ENV_FILE",
        }
    }
    # A file that does not exist: settings then use only the variables given here.
    env["CODESENSE_ENV_FILE"] = str(Path(tempfile.gettempdir()) / "codesense-no-such.env")
    env.update(extra)
    return env


def run_python(code, **env):
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BASE_DIR, env=clean_env(**env), capture_output=True, text=True, timeout=60,
    )


def read_settings(**env):
    result = run_python(PROBE, **env)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


class EnvHelperTests(SimpleTestCase):
    def test_booleans(self):
        with mock.patch.dict(os.environ, {"A": "True", "B": "0", "C": "yes", "D": "", "E": "off"}):
            self.assertTrue(env_bool("A", False))
            self.assertFalse(env_bool("B", True))
            self.assertTrue(env_bool("C", False))
            self.assertTrue(env_bool("D", True))  # empty = use default
            self.assertFalse(env_bool("E", True))
            self.assertTrue(env_bool("MISSING_FLAG", True))

    def test_lists_ignore_spaces_and_empty_items(self):
        with mock.patch.dict(os.environ, {"H": " a.example , ,b.example,"}):
            self.assertEqual(env_list("H", ["x"]), ["a.example", "b.example"])
        self.assertEqual(env_list("MISSING_LIST", ["x"]), ["x"])

    def test_int_and_str(self):
        with mock.patch.dict(os.environ, {"N": " 42 ", "S": " hi "}):
            self.assertEqual(env_int("N", 0), 42)
            self.assertEqual(env_str("S"), "hi")
        with mock.patch.dict(os.environ, {"N": "many"}):
            with self.assertRaises(ValueError):
                env_int("N", 0)

    def test_env_file_parsing(self):
        text = (
            "# comment\n\nPLAIN=value\nQUOTED=\"two words\"\nSINGLE='x=y'\n"
            "export EXPORTED=1\nHASHED=a#b$c%d\nNOEQUALS\nEMPTY=\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(text, encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=False):
                for key in ("PLAIN", "QUOTED", "SINGLE", "EXPORTED", "HASHED", "EMPTY"):
                    os.environ.pop(key, None)
                values = load_env_file(path)
                self.assertEqual(values["PLAIN"], "value")
                self.assertEqual(values["QUOTED"], "two words")
                self.assertEqual(values["SINGLE"], "x=y")
                self.assertEqual(values["EXPORTED"], "1")
                self.assertEqual(values["HASHED"], "a#b$c%d")
                self.assertEqual(values["EMPTY"], "")
                self.assertNotIn("NOEQUALS", values)
                self.assertEqual(os.environ["PLAIN"], "value")
                for key in values:
                    os.environ.pop(key, None)

    def test_real_environment_beats_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("CS_TEST_PRIORITY=from-file\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"CS_TEST_PRIORITY": "from-shell"}):
                load_env_file(path)
                self.assertEqual(os.environ["CS_TEST_PRIORITY"], "from-shell")

    def test_missing_file_is_fine(self):
        self.assertEqual(load_env_file(Path(tempfile.gettempdir()) / "nope-codesense.env"), {})


class ProductionSettingsTests(SimpleTestCase):
    def test_development_defaults_need_no_configuration(self):
        s = read_settings()
        self.assertTrue(s["DEBUG"])
        self.assertEqual(s["ALLOWED_HOSTS"], ["127.0.0.1", "localhost"])
        self.assertEqual(s["LLM_KEY"], "")
        self.assertTrue(s["DB"].endswith("db.sqlite3"))

    def test_debug_off_without_a_secret_key_refuses_to_start(self):
        result = run_python(PROBE, DEBUG="False")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_placeholder_secret_key_is_refused(self):
        result = run_python(PROBE, DEBUG="False", SECRET_KEY="replace-me-with-a-long-random-string")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_environment_values_are_used(self):
        s = read_settings(
            DEBUG="False", SECRET_KEY=GOOD_KEY, ALLOWED_HOSTS="203.0.113.10, example.org",
            CSRF_TRUSTED_ORIGINS="https://example.org", DATABASE_PATH="/srv/codesense/data/db.sqlite3",
            CODESENSE_LLM_API_KEY="",
        )
        self.assertFalse(s["DEBUG"])
        self.assertEqual(s["SECRET_KEY"], GOOD_KEY)
        self.assertEqual(s["ALLOWED_HOSTS"], ["203.0.113.10", "example.org"])
        self.assertEqual(s["CSRF_TRUSTED_ORIGINS"], ["https://example.org"])
        self.assertTrue(s["DB"].replace("\\", "/").endswith("/srv/codesense/data/db.sqlite3"))
        self.assertTrue(s["STATIC_ROOT"].replace("\\", "/").endswith("/staticfiles"))

    def test_production_database_uses_wal_and_waits_for_locks(self):
        prod = read_settings(DEBUG="False", SECRET_KEY=GOOD_KEY)["DB_OPTIONS"]
        self.assertIn("WAL", prod["init_command"])
        self.assertEqual(prod["transaction_mode"], "IMMEDIATE")
        self.assertGreaterEqual(prod["timeout"], 10)
        self.assertNotIn("init_command", read_settings()["DB_OPTIONS"])  # dev: plain SQLite

    def test_plain_http_deployment_keeps_cookies_usable(self):
        """Over http://IP, Secure cookies would never be sent and forms would break."""
        s = read_settings(DEBUG="False", SECRET_KEY=GOOD_KEY)
        self.assertFalse(s["SESSION_COOKIE_SECURE"])
        self.assertFalse(s["CSRF_COOKIE_SECURE"])
        self.assertFalse(s["SSL_REDIRECT"])
        self.assertTrue(s["SESSION_COOKIE_HTTPONLY"])

    def test_https_mode_secures_cookies_and_trusts_the_proxy_header(self):
        s = read_settings(DEBUG="False", SECRET_KEY=GOOD_KEY, USE_HTTPS="True")
        self.assertTrue(s["SESSION_COOKIE_SECURE"])
        self.assertTrue(s["CSRF_COOKIE_SECURE"])
        self.assertTrue(s["SSL_REDIRECT"])
        self.assertEqual(s["PROXY_HEADER"], ["HTTP_X_FORWARDED_PROTO", "https"])

    def test_deploy_check_is_clean_for_https_and_for_http(self):
        def deploy_check(**env):
            return subprocess.run(
                [sys.executable, "manage.py", "check", "--deploy"],
                cwd=BASE_DIR, env=clean_env(DEBUG="False", SECRET_KEY=GOOD_KEY, **env),
                capture_output=True, text=True, timeout=90,
            )

        https = deploy_check(USE_HTTPS="True")
        self.assertEqual(https.returncode, 0, https.stdout + https.stderr)
        for check_id in ("W009", "W018", "W012", "W016", "W008", "W007", "W006"):
            self.assertNotIn(f"security.{check_id}", https.stderr + https.stdout)

        plain = deploy_check()
        self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
        for check_id in ("W009", "W018", "W007", "W006"):
            self.assertNotIn(f"security.{check_id}", plain.stderr + plain.stdout)

    def test_example_env_file_is_complete_but_refuses_to_run_unedited(self):
        example = BASE_DIR / ".env.example"
        values = load_env_file_isolated(example)
        for name in ("DEBUG", "SECRET_KEY", "ALLOWED_HOSTS", "CODESENSE_LLM_API_KEY", "DATABASE_PATH"):
            self.assertIn(name, values)
        self.assertEqual(values["CODESENSE_LLM_API_KEY"], "")
        result = run_python(PROBE, CODESENSE_ENV_FILE=str(example))
        self.assertNotEqual(result.returncode, 0)  # placeholder SECRET_KEY rejected


def load_env_file_isolated(path):
    """Parse a .env file without leaking its values into this process."""
    with mock.patch.dict(os.environ, {}, clear=False):
        before = dict(os.environ)
        values = load_env_file(path)
        for key in list(os.environ):
            if key not in before:
                del os.environ[key]
        return values


class LoggingTests(SimpleTestCase):
    def test_configured_for_console_and_logs_codesense_log(self):
        handlers = settings.LOGGING["handlers"]
        self.assertIn("console", handlers)
        self.assertIn("file", handlers)
        self.assertEqual(
            Path(handlers["file"]["filename"]).parts[-2:], ("logs", "codesense.log")
        )
        for name in ("django", "practice", "research"):
            self.assertIn("console", settings.LOGGING["loggers"][name]["handlers"])
            self.assertIn("file", settings.LOGGING["loggers"][name]["handlers"])

    def test_application_warnings_reach_the_log_file(self):
        log_file = Path(settings.LOG_FILE)
        marker = f"deployment-test-marker-{os.getpid()}"
        logging.getLogger("practice.feedback.ai_enhanced").warning(marker)
        for handler in logging.getLogger("practice").handlers:
            handler.flush()
        self.assertIn(marker, log_file.read_text(encoding="utf-8"))

    def test_django_errors_are_captured_with_tracebacks(self):
        marker = f"django-request-marker-{os.getpid()}"
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            logging.getLogger("django.request").error("Internal Server Error: /x", exc_info=True)
        text = Path(settings.LOG_FILE).read_text(encoding="utf-8")
        self.assertIn(marker, text)
        self.assertIn("Traceback", text)

    def test_unwritable_log_folder_falls_back_to_console_only(self):
        """The app must still start if logs/ cannot be created or written."""
        result = run_python(UNWRITABLE_LOG_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]), ["console"])


class DeployFilesTests(SimpleTestCase):
    def text(self, relative):
        return (BASE_DIR / relative).read_text(encoding="utf-8")

    def test_requirements_include_gunicorn_for_linux_only(self):
        reqs = self.text("requirements.txt")
        self.assertIn("Django>=5.2,<6", reqs)
        line = next(l for l in reqs.splitlines() if l.startswith("gunicorn"))
        self.assertIn("sys_platform", line)

    def test_gunicorn_config_is_loopback_and_modest(self):
        namespace = {}
        exec((BASE_DIR / "deploy" / "gunicorn.conf.py").read_text(encoding="utf-8"), namespace)
        self.assertTrue(namespace["bind"].startswith("127.0.0.1:"))
        self.assertTrue(2 <= namespace["workers"] <= 4)
        self.assertEqual(namespace["worker_class"], "sync")
        self.assertGreaterEqual(namespace["timeout"], 30)

    def test_systemd_unit_restarts_and_starts_on_boot(self):
        unit = self.text("deploy/codesense.service")
        for needle in (
            "Restart=on-failure", "WantedBy=multi-user.target", "User=codesense",
            "WorkingDirectory=/srv/codesense/app",
            "/srv/codesense/venv/bin/gunicorn", "codesense.wsgi:application",
            "deploy/gunicorn.conf.py",
        ):
            self.assertIn(needle, unit)
        # Start-limit keys belong in [Unit]; in [Service] systemd ignores them.
        service_part = unit.split("[Service]", 1)[1]
        self.assertNotIn("StartLimit", service_part)

    def test_nginx_config_serves_static_proxies_and_sets_headers(self):
        conf = self.text("deploy/nginx-codesense.conf")
        for needle in (
            "proxy_pass http://codesense_app", "server 127.0.0.1:8000",
            "alias /srv/codesense/app/staticfiles/", "default_server", "server_name _",
            "X-Forwarded-Proto $scheme", "proxy_set_header Host $host",
            "X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy",
            "server_tokens off",
        ):
            self.assertIn(needle, conf)
        self.assertEqual(conf.count("{"), conf.count("}"))
        # A location with its own add_header would silently drop the security headers.
        active = [l for l in conf.splitlines() if not l.strip().startswith("#")]
        location_blocks = "\n".join(active).split("location ")[1:]
        for block in location_blocks:
            self.assertNotIn("add_header", block)

    def test_static_paths_agree_between_settings_nginx_and_docs(self):
        self.assertEqual(settings.STATIC_ROOT.name, "staticfiles")
        docs = self.text("DEPLOYMENT.md")
        for needle in ("/srv/codesense/app", "collectstatic", "codesense.service", "ufw", "journalctl"):
            self.assertIn(needle, docs)

    def test_deployment_documents_exist_and_cover_every_step(self):
        docs = self.text("DEPLOYMENT.md")
        for heading in (
            "Copy the project", "virtual environment", "Install the requirements",
            "migrations", "collectstatic", "gunicorn", "nginx", "systemd", "automatically",
            "UFW", "logs", "Updating",
        ):
            self.assertIn(heading.lower(), docs.lower(), heading)
        self.assertGreater(len(self.text("DEPLOYMENT_CHECKLIST.md").splitlines()), 20)

    def test_secrets_stay_out_of_version_control(self):
        ignore = self.text(".gitignore").splitlines()
        for pattern in (".env", "logs/", "staticfiles/", "db.sqlite3"):
            self.assertIn(pattern, ignore)
