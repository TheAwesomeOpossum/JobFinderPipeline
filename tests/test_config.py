"""Tests for job_finder/config.py"""

import importlib
import os
import sys
import pytest


def _reload_config(monkeypatch, extra_vars: dict):
    """Set env vars, remove cached module, reimport config, then restore."""
    required = {
        "GOOGLE_API_KEY":    "fake_google_key",
        "GOOGLE_CSE_ID":     "fake_cse_id",
        "ANTHROPIC_API_KEY": "fake_anthropic_key",
        "SF_USERNAME":       "test@example.com",
        "SF_PASSWORD":       "fake_sf_password",
        "SF_SECURITY_TOKEN": "fake_sf_token",
        "PG_DBNAME":         "test_db",
        "PG_USER":           "test_user",
        "PG_PASSWORD":       "test_password",
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
    assert cfg.GOOGLE_API_KEY == "fake_google_key"
    assert cfg.GOOGLE_CSE_ID == "fake_cse_id"
    assert cfg.PG_PORT == 5432
    assert cfg.DAILY_LIMIT == 20
    assert "mid" in cfg.SENIORITY_TARGETS


def test_missing_required_var_raises(monkeypatch):
    # Ensure GOOGLE_API_KEY is absent
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    for key in ["GOOGLE_CSE_ID", "ANTHROPIC_API_KEY", "SF_USERNAME", "SF_PASSWORD",
                "SF_SECURITY_TOKEN", "PG_DBNAME", "PG_USER", "PG_PASSWORD"]:
        monkeypatch.setenv(key, "value")

    sys.modules.pop("job_finder.config", None)
    with pytest.raises(EnvironmentError, match="GOOGLE_API_KEY"):
        import job_finder.config  # noqa: F401


def test_optional_vars_have_defaults(monkeypatch):
    cfg = _reload_config(monkeypatch, {})
    assert cfg.SF_DOMAIN == "login"
    assert cfg.PG_HOST == "localhost"
    assert cfg.PG_SSLMODE == "require"
    assert cfg.LOCATION_PREFERENCE == "Remote"
