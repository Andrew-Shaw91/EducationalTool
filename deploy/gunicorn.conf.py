"""
Gunicorn settings for CodeSense on a single small VM.

Start (from the project folder, with the virtual environment's gunicorn):

    gunicorn --config deploy/gunicorn.conf.py codesense.wsgi:application

Reliability over scale: a few synchronous workers, loopback only, logs to the
console (systemd keeps them in the journal; Django also writes
logs/codesense.log). Any value can be overridden with an environment variable.
"""

import os

# Listen on the loopback interface only. nginx is the only thing that should
# reach gunicorn; the firewall also keeps port 8000 closed to the internet.
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")

# 2-4 workers is plenty for SQLite and a small VM. More workers do not help
# because SQLite allows one writer at a time.
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
worker_class = "sync"

# A request taking longer than this is killed and the worker restarted.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5

# Restart each worker after roughly this many requests, which limits the effect
# of any slow memory growth. Jitter staggers restarts so workers do not all
# restart together.
max_requests = 1000
max_requests_jitter = 100

# Only trust X-Forwarded-* headers from the local nginx.
forwarded_allow_ips = "127.0.0.1"

# Logging: stdout/stderr, collected by systemd (journalctl -u codesense).
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
capture_output = True

proc_name = "codesense"
