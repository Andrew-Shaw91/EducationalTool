"""
Small helpers for reading configuration from the environment.

Kept separate from settings.py so they can be unit-tested, and written with the
standard library only so deployment needs no extra package.

Configuration comes from, in order of priority:
  1. real environment variables (for example set by systemd or the shell);
  2. a `.env` file in the project directory (KEY=value lines).
A variable that is already set is never overridden by the file.
"""

import os
from pathlib import Path

TRUE_VALUES = {"1", "true", "yes", "on"}


def load_env_file(path: Path) -> dict[str, str]:
    """
    Read KEY=value lines from `path` into os.environ (without overriding any
    variable that is already set) and return what the file contained.

    Blank lines and lines starting with '#' are ignored. Values may be wrapped
    in single or double quotes. A missing file is not an error, so development
    works with no .env at all.
    """
    values: dict[str, str] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return values

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key:
            values[key] = value
            os.environ.setdefault(key, value)
    return values


def env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return default if value is None else value.strip()


def env_bool(name: str, default: bool) -> bool:
    """True for 1/true/yes/on (any case); anything else set is False."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in TRUE_VALUES


def env_list(name: str, default: list[str]) -> list[str]:
    """A comma-separated variable as a list, ignoring spaces and empty items."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a whole number, got {value!r}") from exc
