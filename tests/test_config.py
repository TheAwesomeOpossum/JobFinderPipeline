"""Tests for job_finder/config.py"""

import importlib
import os
import sys
import pytest


def _reload_config(monkeypatch, extra_vars: dict):
    """Set env vars, remove cached module, reimport config, then restore."""
    required = {
        "SERPER_API_KEY":      "fake_serper_key",
        "ANTHROPIC_API_KEY":   "fake_anthropic_key",
        "SF_USERNAME":         "test@example.com",
        "SF_PASSWORD":         "fake_sf_password",
        "SF_SECURITY_TOKEN":   "fake_sf_token",
        "PG_DBNAME":           "test_db",
        "PG_USER":             "test_user",
        "PG_PASSWORD":         "test_password",
        # Explicit defaults so load_dotenv() doesn't pull in real .env values
        "SF_DOMAIN":           "login",
        "PG_HOST":             "localhost",
        "PG_SSLMODE":          "require",
        "LOCATION_PREFERENCE": "Remote",
    }
    required.update(extra_vars)
    for k, v in required.items():
        monkeypatch.setenv(k, v)

    # Remove cached module so _require() re-runs
    sys.modules.pop("job_finder.config", None)
    import job_finder.config as cfg
    return cfg


def test_config_loads_with_all_vars(monkeypatch):
    cfg = _reload_config(monkeypatch, {})
    assert cfg.SERPER_API_KEY == "fake_serper_key"
    assert cfg.PG_PORT == 5432
    assert cfg.DAILY_LIMIT == 20
    assert "mid" in cfg.SENIORITY_TARGETS


def test_missing_required_var_raises(monkeypatch):
    # Empty string → _require() raises; load_dotenv(override=False) won't overwrite it
    monkeypatch.setenv("SERPER_API_KEY", "")
    for key in ["ANTHROPIC_API_KEY", "SF_USERNAME", "SF_PASSWORD",
                "SF_SECURITY_TOKEN", "PG_DBNAME", "PG_USER", "PG_PASSWORD"]:
        monkeypatch.setenv(key, "value")

    sys.modules.pop("job_finder.config", None)
    with pytest.raises(EnvironmentError, match="SERPER_API_KEY"):
        import job_finder.config  # noqa: F401


def test_optional_vars_have_defaults(monkeypatch):
    cfg = _reload_config(monkeypatch, {})
    assert cfg.SF_DOMAIN == "login"
    assert cfg.PG_HOST == "localhost"
    assert cfg.PG_SSLMODE == "require"
    assert cfg.LOCATION_PREFERENCE == "Remote"
