"""Tests for job_finder/salary_extractor.py"""

import pytest
from job_finder.salary_extractor import (
    extract_greenhouse_salary,
    extract_lever_salary,
    extract_salary_from_text,
    format_salary_range_text,
    annual_midpoint,
    hourly_midpoint,
    EMPTY_SALARY,
)


# ---------------------------------------------------------------------------
# extract_greenhouse_salary
# ---------------------------------------------------------------------------

def test_greenhouse_salary_annual_range():
    pay = [{"min_cents": 8000000, "max_cents": 12000000, "currency_type": "USD"}]
    result = extract_greenhouse_salary(pay)
    assert result["annual_salary_min"] == 80000.0
    assert result["annual_salary_max"] == 120000.0
    assert result["salary_type"] == "annual"
    assert result["salary_range_text"] == "$80k-$120k/yr"


def test_greenhouse_salary_empty_list():
    result = extract_greenhouse_salary([])
    assert result == EMPTY_SALARY


def test_greenhouse_salary_partial_min_only():
    pay = [{"min_cents": 9500000, "currency_type": "USD"}]
    result = extract_greenhouse_salary(pay)
    assert result["annual_salary_min"] == 95000.0
    assert result["annual_salary_max"] is None
    assert result["salary_range_text"] == "$95k+/yr"


# ---------------------------------------------------------------------------
# extract_lever_salary
# ---------------------------------------------------------------------------

def test_lever_salary_annual():
    salary = {"min": 80000, "max": 120000, "currency": "USD", "interval": "per-year"}
    result = extract_lever_salary(salary)
    assert result["annual_salary_min"] == 80000.0
    assert result["annual_salary_max"] == 120000.0
    assert result["salary_type"] == "annual"
    assert result["hourly_rate_min"] is None


def test_lever_salary_hourly():
    salary = {"min": 40, "max": 60, "currency": "USD", "interval": "per-hour"}
    result = extract_lever_salary(salary)
    assert result["hourly_rate_min"] == 40.0
    assert result["hourly_rate_max"] == 60.0
    assert result["salary_type"] == "hourly"
    assert result["annual_salary_min"] is None
    assert result["salary_range_text"] == "$40-$60/hr"


def test_lever_salary_empty():
    result = extract_lever_salary({})
    assert result == EMPTY_SALARY


def test_lever_salary_unknown_interval_treated_as_annual():
    salary = {"min": 90000, "max": 110000, "interval": "bi-weekly"}
    result = extract_lever_salary(salary)
    assert result["salary_type"] == "annual"
    assert result["annual_salary_min"] == 90000.0


# ---------------------------------------------------------------------------
# extract_salary_from_text
# ---------------------------------------------------------------------------

def test_text_annual_k_range():
    result = extract_salary_from_text("Salary: $80k - $120k annually")
    assert result["annual_salary_min"] == 80000.0
    assert result["annual_salary_max"] == 120000.0
    assert result["salary_type"] == "annual"


def test_text_hourly_range():
    result = extract_salary_from_text("Rate: $40 - $60/hr")
    assert result["hourly_rate_min"] == 40.0
    assert result["hourly_rate_max"] == 60.0
    assert result["salary_type"] == "hourly"


def test_text_single_hourly():
    result = extract_salary_from_text("Pay: $55/hour")
    assert result["hourly_rate_min"] == 55.0
    assert result["salary_type"] == "hourly"


def test_text_single_annual_k():
    result = extract_salary_from_text("Compensation: $95k")
    assert result["annual_salary_min"] == 95000.0
    assert result["salary_type"] == "annual"


def test_text_annual_full_numbers():
    result = extract_salary_from_text("$90,000 - $130,000 per year")
    assert result["annual_salary_min"] == 90000.0
    assert result["annual_salary_max"] == 130000.0


def test_text_no_salary_returns_empty():
    result = extract_salary_from_text("We offer competitive compensation.")
    assert result == EMPTY_SALARY


def test_text_empty_string():
    result = extract_salary_from_text("")
    assert result == EMPTY_SALARY


# ---------------------------------------------------------------------------
# format_salary_range_text
# ---------------------------------------------------------------------------

def test_format_annual_range():
    d = {"annual_salary_min": 80000, "annual_salary_max": 120000,
         "hourly_rate_min": None, "hourly_rate_max": None}
    assert format_salary_range_text(d) == "$80k-$120k/yr"


def test_format_annual_min_only():
    d = {"annual_salary_min": 95000, "annual_salary_max": None,
         "hourly_rate_min": None, "hourly_rate_max": None}
    assert format_salary_range_text(d) == "$95k+/yr"


def test_format_hourly_range():
    d = {"annual_salary_min": None, "annual_salary_max": None,
         "hourly_rate_min": 40, "hourly_rate_max": 60}
    assert format_salary_range_text(d) == "$40-$60/hr"


def test_format_no_data_returns_none():
    assert format_salary_range_text(EMPTY_SALARY) is None


def test_format_truncates_to_20_chars():
    # Very large salary range that would exceed 20 chars
    d = {"annual_salary_min": 200000, "annual_salary_max": 350000,
         "hourly_rate_min": None, "hourly_rate_max": None}
    result = format_salary_range_text(d)
    assert result is not None
    assert len(result) <= 20


# ---------------------------------------------------------------------------
# annual_midpoint / hourly_midpoint
# ---------------------------------------------------------------------------

def test_annual_midpoint_range():
    d = {"annual_salary_min": 80000, "annual_salary_max": 120000,
         "hourly_rate_min": None, "hourly_rate_max": None}
    assert annual_midpoint(d) == 100000.0


def test_annual_midpoint_min_only():
    d = {"annual_salary_min": 95000, "annual_salary_max": None,
         "hourly_rate_min": None, "hourly_rate_max": None}
    assert annual_midpoint(d) == 95000.0


def test_annual_midpoint_falls_back_to_hourly():
    d = {"annual_salary_min": None, "annual_salary_max": None,
         "hourly_rate_min": 50, "hourly_rate_max": None}
    assert annual_midpoint(d) == 50 * 2080


def test_annual_midpoint_no_data():
    assert annual_midpoint(EMPTY_SALARY) is None


def test_hourly_midpoint_range():
    d = {"hourly_rate_min": 40, "hourly_rate_max": 60,
         "annual_salary_min": None, "annual_salary_max": None}
    assert hourly_midpoint(d) == 50.0


def test_hourly_midpoint_no_data():
    assert hourly_midpoint(EMPTY_SALARY) is None
