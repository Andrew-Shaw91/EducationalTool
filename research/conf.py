"""
Single place that answers "what are we allowed to collect?".

Everything is controlled by the RESEARCH dict in settings.py. Code elsewhere
calls these helpers instead of reading settings directly, so a new collection
rule is added in exactly one place.
"""

from django.conf import settings

# Defaults are the most private option for everything except the master switch,
# which the researcher must consciously leave on.
DEFAULTS = {
    # Master switch. False: no Participant, no Attempt, no hint counts are
    # created or stored. The app behaves identically for the student.
    "ANALYTICS_ENABLED": True,
    # Store the student's own words (free text and reasoning). False keeps
    # only choices, correctness and assessment results.
    "STORE_RESPONSE_TEXT": True,
    # Store how many hints were requested before each submission.
    "STORE_HINT_USAGE": True,
    # Store when each participant/attempt was created. False leaves the
    # timestamp empty (useful if timing could make people identifiable).
    "STORE_TIMESTAMPS": True,
}


def option(name: str):
    return {**DEFAULTS, **getattr(settings, "RESEARCH", {})}[name]


def analytics_enabled() -> bool:
    return bool(option("ANALYTICS_ENABLED"))


def stores(name: str) -> bool:
    """True only if analytics is on AND the specific option is on."""
    return analytics_enabled() and bool(option(name))
