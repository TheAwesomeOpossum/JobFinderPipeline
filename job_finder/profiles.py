"""YAML profile loader for JobFinder keyword/schedule configurations."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_profile(path: str) -> dict:
    """Load a YAML profile file. Raises FileNotFoundError if path doesn't exist."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Profile file not found: {path}")
    with p.open() as f:
        data = yaml.safe_load(f) or {}
    logger.debug("Loaded profile from %s: %s", path, data)
    return data


def get_schedule(profile: dict) -> tuple[int, int]:
    """Return (hour, minute) from profile, defaulting to 2:00 AM."""
    hour = int(profile.get("schedule_hour", 2))
    minute = int(profile.get("schedule_minute", 0))
    return hour, minute
