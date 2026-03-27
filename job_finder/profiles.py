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


def get_skills(profile: dict) -> tuple[list[str], list[str]]:
    """Return (required_skills, bonus_skills). Handles list or comma-string."""
    def _to_list(value) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(s).strip() for s in value if str(s).strip()]
        return [s.strip() for s in str(value).split(",") if s.strip()]

    return _to_list(profile.get("required_skills")), _to_list(profile.get("bonus_skills"))


def get_location(profile: dict) -> str | None:
    """Return location_preference from profile (fixes silent-ignore bug)."""
    return profile.get("location_preference") or None


def get_seniority(profile: dict) -> list[str] | None:
    """Return seniority_targets as a list (fixes silent-ignore bug)."""
    value = profile.get("seniority_targets")
    if not value:
        return None
    if isinstance(value, list):
        return [str(s).strip().lower() for s in value if str(s).strip()]
    return [s.strip().lower() for s in str(value).split(",") if s.strip()]
