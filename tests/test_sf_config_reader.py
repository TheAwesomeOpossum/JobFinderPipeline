"""Tests for job_finder/sf_config_reader.py"""

import sys
import json
import pytest
from unittest.mock import MagicMock


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x",
        "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x",
        "SF_PASSWORD": "x",
        "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x",
        "PG_USER": "x",
        "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def _import_reader(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_config_reader", None)
    from job_finder import sf_config_reader
    return sf_config_reader


def _make_record(overrides=None):
    """Return a minimal valid Job_Search_Config__c record dict."""
    record = {
        "attributes": {"type": "Job_Search_Config__c"},
        "Id": "a001x000000AAAAA",
        "Name": "Test Config",
        "Keywords__c": "Salesforce Developer, Salesforce Engineer",
        "Required_Skills__c": "Apex;SOQL",
        "Bonus_Skills__c": "Batch Apex;CPQ",
        "Daily_Limit__c": 10.0,
        "Min_Annual_Salary__c": 145000.0,
        "Schedule_Hour__c": 2.0,
        "Schedule_Minute__c": 30.0,
        "Days_Back__c": 1.0,
    }
    if overrides:
        record.update(overrides)
    return record


# ─── load_sf_profiles ───────────────────────────────────────────────────────

def test_load_sf_profiles_returns_mapped_list(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    mock_sf = MagicMock()
    mock_sf.query.return_value = {
        "totalSize": 2,
        "records": [
            _make_record({"Id": "a001x000000AAAAA", "Name": "Config A"}),
            _make_record({"Id": "a001x000000BBBBB", "Name": "Config B"}),
        ],
    }

    profiles = sf_config_reader.load_sf_profiles(mock_sf)

    assert len(profiles) == 2
    assert profiles[0]["profile_name"] == "Config A"
    assert profiles[0]["sf_record_id"] == "a001x000000AAAAA"
    assert profiles[1]["profile_name"] == "Config B"
    assert profiles[1]["sf_record_id"] == "a001x000000BBBBB"


def test_load_sf_profiles_returns_empty_on_exception(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    mock_sf = MagicMock()
    mock_sf.query.side_effect = Exception("Network error")

    profiles = sf_config_reader.load_sf_profiles(mock_sf)

    assert profiles == []


def test_load_sf_profiles_returns_empty_when_no_active_records(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    mock_sf = MagicMock()
    mock_sf.query.return_value = {"totalSize": 0, "records": []}

    profiles = sf_config_reader.load_sf_profiles(mock_sf)

    assert profiles == []


# ─── _map_record ────────────────────────────────────────────────────────────

def test_map_record_splits_semicolon_skills(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    record = _make_record({
        "Required_Skills__c": "Apex;Lightning Web Components;SOQL",
        "Bonus_Skills__c": "Batch Apex;CPQ",
    })
    profile = sf_config_reader._map_record(record)

    assert profile["required_skills"] == ["Apex", "Lightning Web Components", "SOQL"]
    assert profile["bonus_skills"] == ["Batch Apex", "CPQ"]


def test_map_record_handles_null_fields(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    record = {
        "attributes": {"type": "Job_Search_Config__c"},
        "Id": "a001x000000AAAAA",
        "Name": "Minimal Config",
        "Keywords__c": None,
        "Required_Skills__c": None,
        "Bonus_Skills__c": None,
        "Daily_Limit__c": None,
        "Min_Annual_Salary__c": None,
        "Schedule_Hour__c": None,
        "Schedule_Minute__c": None,
        "Days_Back__c": None,
    }
    profile = sf_config_reader._map_record(record)

    assert profile["keywords"] == ""
    assert profile["required_skills"] == []
    assert profile["bonus_skills"] == []
    assert profile["limit"] == 10
    assert profile["min_annual_salary"] == 0.0
    assert profile["schedule_hour"] == 2
    assert profile["schedule_minute"] == 0
    assert profile["days"] == 1


def test_map_record_casts_float_numerics(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    record = _make_record({
        "Daily_Limit__c": 10.0,
        "Schedule_Hour__c": 3.0,
        "Schedule_Minute__c": 0.0,
        "Days_Back__c": 2.0,
        "Min_Annual_Salary__c": 160000.0,
    })
    profile = sf_config_reader._map_record(record)

    assert profile["limit"] == 10
    assert isinstance(profile["limit"], int)
    assert profile["schedule_hour"] == 3
    assert isinstance(profile["schedule_hour"], int)
    assert profile["days"] == 2
    assert isinstance(profile["days"], int)
    assert profile["min_annual_salary"] == 160000.0
    assert isinstance(profile["min_annual_salary"], float)


# ─── writeback ──────────────────────────────────────────────────────────────

def test_writeback_calls_sf_update_with_correct_payload(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    mock_sf = MagicMock()
    config_id = "a001x000000AAAAA"
    summary = {"found": 10, "pushed": 5, "failed": 0}

    # Patch _with_backoff to call fn directly
    monkeypatch.setattr(
        "job_finder.sf_writer._with_backoff",
        lambda fn, **kw: fn(),
    )

    sf_config_reader.writeback(mock_sf, config_id, summary)

    mock_sf.Job_Search_Config__c.update.assert_called_once()
    call_args = mock_sf.Job_Search_Config__c.update.call_args
    called_id = call_args[0][0]
    payload = call_args[0][1]

    assert called_id == config_id
    assert "Last_Run_At__c" in payload
    assert "Last_Run_Summary__c" in payload
    assert json.loads(payload["Last_Run_Summary__c"]) == summary


def test_writeback_does_not_raise_on_failure(monkeypatch):
    sf_config_reader = _import_reader(monkeypatch)

    mock_sf = MagicMock()
    mock_sf.Job_Search_Config__c.update.side_effect = Exception("SF update failed")

    monkeypatch.setattr(
        "job_finder.sf_writer._with_backoff",
        lambda fn, **kw: fn(),
    )

    # Must not raise
    sf_config_reader.writeback(mock_sf, "a001x000000AAAAA", {"pushed": 1})
