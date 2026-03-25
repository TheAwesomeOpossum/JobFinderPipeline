"""Tests for job_finder/profiles.py"""

import pytest


def test_load_profile_returns_dict(tmp_path):
    profile_file = tmp_path / "test_profile.yaml"
    profile_file.write_text(
        "keywords: 'Python Developer'\nlimit: 15\nschedule_hour: 3\nschedule_minute: 30\n"
    )
    from job_finder.profiles import load_profile

    result = load_profile(str(profile_file))

    assert isinstance(result, dict)
    assert result["keywords"] == "Python Developer"
    assert result["limit"] == 15
    assert result["schedule_hour"] == 3
    assert result["schedule_minute"] == 30


def test_load_profile_missing_file_raises_file_not_found(tmp_path):
    from job_finder.profiles import load_profile

    with pytest.raises(FileNotFoundError, match="Profile file not found"):
        load_profile(str(tmp_path / "nonexistent.yaml"))


def test_load_profile_empty_file_returns_empty_dict(tmp_path):
    profile_file = tmp_path / "empty.yaml"
    profile_file.write_text("")
    from job_finder.profiles import load_profile

    result = load_profile(str(profile_file))

    assert result == {}


def test_load_profile_partial_keys(tmp_path):
    profile_file = tmp_path / "partial.yaml"
    profile_file.write_text("keywords: 'Rust Engineer'\n")
    from job_finder.profiles import load_profile

    result = load_profile(str(profile_file))

    assert result["keywords"] == "Rust Engineer"
    assert "limit" not in result


def test_get_schedule_uses_profile_values():
    from job_finder.profiles import get_schedule

    hour, minute = get_schedule({"schedule_hour": 3, "schedule_minute": 15})

    assert hour == 3
    assert minute == 15


def test_get_schedule_defaults_to_2am():
    from job_finder.profiles import get_schedule

    hour, minute = get_schedule({})

    assert hour == 2
    assert minute == 0


def test_get_schedule_casts_to_int():
    from job_finder.profiles import get_schedule

    # YAML may parse as int already, but cast is still safe
    hour, minute = get_schedule({"schedule_hour": "4", "schedule_minute": "30"})

    assert hour == 4
    assert minute == 30
