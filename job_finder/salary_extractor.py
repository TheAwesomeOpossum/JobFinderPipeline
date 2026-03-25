"""Salary extraction and formatting utilities for all ATS parsers."""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Empty salary dict — all parsers return this structure
# ---------------------------------------------------------------------------
EMPTY_SALARY = {
    "annual_salary_min":  None,
    "annual_salary_max":  None,
    "hourly_rate_min":    None,
    "hourly_rate_max":    None,
    "salary_range_text":  None,
    "salary_type":        None,
}


# ---------------------------------------------------------------------------
# ATS-specific extractors
# ---------------------------------------------------------------------------

def extract_greenhouse_salary(pay_input_ranges: list) -> dict:
    """
    Convert Greenhouse pay_input_ranges → salary dict.
    Amounts are in cents; divide by 100 for dollars.
    Only uses the first range entry.
    """
    result = dict(EMPTY_SALARY)
    if not pay_input_ranges:
        return result

    entry = pay_input_ranges[0]
    min_cents = entry.get("min_cents")
    max_cents = entry.get("max_cents")

    if min_cents is not None:
        result["annual_salary_min"] = min_cents / 100
    if max_cents is not None:
        result["annual_salary_max"] = max_cents / 100
    if result["annual_salary_min"] is not None or result["annual_salary_max"] is not None:
        result["salary_type"] = "annual"
        result["salary_range_text"] = format_salary_range_text(result)

    return result


def extract_lever_salary(salary_obj: dict) -> dict:
    """
    Convert Lever salary object → salary dict.
    Lever returns direct dollar values (not cents).
    interval: 'per-year' → annual, 'per-hour' → hourly, others → annual by default.
    """
    result = dict(EMPTY_SALARY)
    if not salary_obj:
        return result

    min_val = salary_obj.get("min")
    max_val = salary_obj.get("max")
    interval = (salary_obj.get("interval") or "").lower()

    if min_val is None and max_val is None:
        return result

    is_hourly = interval == "per-hour"

    if is_hourly:
        result["hourly_rate_min"] = float(min_val) if min_val is not None else None
        result["hourly_rate_max"] = float(max_val) if max_val is not None else None
        result["salary_type"] = "hourly"
    else:
        result["annual_salary_min"] = float(min_val) if min_val is not None else None
        result["annual_salary_max"] = float(max_val) if max_val is not None else None
        result["salary_type"] = "annual"

    result["salary_range_text"] = format_salary_range_text(result)
    return result


# ---------------------------------------------------------------------------
# Text-based fallback extractor (Generic parser)
# ---------------------------------------------------------------------------

# Patterns ordered from most specific to least specific
_SALARY_PATTERNS = [
    # Hourly range: $40 - $60/hr, $40-$60/hour, 40-60/hr
    (r'\$\s*(\d+(?:\.\d+)?)\s*[-–]\s*\$?\s*(\d+(?:\.\d+)?)\s*/\s*(?:hr|hour)', "hourly_range"),
    # Annual range in k notation: $80k-$120k, $80K - $120K
    (r'\$\s*(\d+(?:\.\d+)?)\s*[kK]\s*[-–]\s*\$?\s*(\d+(?:\.\d+)?)\s*[kK]', "annual_range_k"),
    # Annual range full: $80,000-$120,000 or $80000-$120000
    (r'\$\s*(\d{2,3}(?:,\d{3})?)\s*[-–]\s*\$?\s*(\d{2,3}(?:,\d{3})?)', "annual_range"),
    # Single hourly: $50/hr, $50/hour
    (r'\$\s*(\d+(?:\.\d+)?)\s*/\s*(?:hr|hour)', "hourly_single"),
    # Single annual in k: $95k, $100K
    (r'\$\s*(\d+(?:\.\d+)?)\s*[kK](?!\s*/)', "annual_single_k"),
    # Single annual full: $95,000 or $95000 (4-6 digits)
    (r'\$\s*(\d{2,3}(?:,\d{3}))', "annual_single"),
]


def extract_salary_from_text(text: str) -> dict:
    """
    Regex-based salary extraction from plain-text job description.
    Returns the first confident match found.
    """
    result = dict(EMPTY_SALARY)
    if not text:
        return result

    for pattern, label in _SALARY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue

        try:
            if label == "hourly_range":
                result["hourly_rate_min"] = float(match.group(1))
                result["hourly_rate_max"] = float(match.group(2))
                result["salary_type"] = "hourly"
                break

            elif label == "annual_range_k":
                result["annual_salary_min"] = float(match.group(1)) * 1000
                result["annual_salary_max"] = float(match.group(2)) * 1000
                result["salary_type"] = "annual"
                break

            elif label == "annual_range":
                min_str = match.group(1).replace(",", "")
                max_str = match.group(2).replace(",", "")
                min_val = float(min_str)
                max_val = float(max_str)
                # Guard: must look like annual salary (>= 10000)
                if min_val >= 10000 and max_val >= 10000:
                    result["annual_salary_min"] = min_val
                    result["annual_salary_max"] = max_val
                    result["salary_type"] = "annual"
                    break

            elif label == "hourly_single":
                result["hourly_rate_min"] = float(match.group(1))
                result["salary_type"] = "hourly"
                break

            elif label == "annual_single_k":
                result["annual_salary_min"] = float(match.group(1)) * 1000
                result["salary_type"] = "annual"
                break

            elif label == "annual_single":
                val = float(match.group(1).replace(",", ""))
                if val >= 10000:
                    result["annual_salary_min"] = val
                    result["salary_type"] = "annual"
                    break

        except (ValueError, IndexError):
            continue

    if result["salary_type"] is not None:
        result["salary_range_text"] = format_salary_range_text(result)

    return result


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_salary_range_text(salary_dict: dict) -> str | None:
    """
    Return a ≤20-char string suitable for Salary_Range__c.
    Prioritizes annual over hourly.
    Returns None if no salary data is present.
    """
    ann_min = salary_dict.get("annual_salary_min")
    ann_max = salary_dict.get("annual_salary_max")
    hr_min  = salary_dict.get("hourly_rate_min")
    hr_max  = salary_dict.get("hourly_rate_max")

    def _k(val: float) -> str:
        """Format a dollar amount into compact k notation."""
        k = val / 1000
        if k == int(k):
            return f"${int(k)}k"
        return f"${k:.0f}k"

    if ann_min is not None or ann_max is not None:
        if ann_min is not None and ann_max is not None:
            text = f"{_k(ann_min)}-{_k(ann_max)}/yr"
        elif ann_min is not None:
            text = f"{_k(ann_min)}+/yr"
        else:
            text = f"up to {_k(ann_max)}/yr"
        return text[:20]

    if hr_min is not None or hr_max is not None:
        def _hr(val: float) -> str:
            return f"${val:.0f}" if val == int(val) else f"${val:.2f}"

        if hr_min is not None and hr_max is not None:
            text = f"{_hr(hr_min)}-{_hr(hr_max)}/hr"
        elif hr_min is not None:
            text = f"{_hr(hr_min)}+/hr"
        else:
            text = f"up to {_hr(hr_max)}/hr"
        return text[:20]

    return None


# ---------------------------------------------------------------------------
# Midpoint helpers (for Annual_Salary__c and Hourly_Rate__c SF fields)
# ---------------------------------------------------------------------------

def annual_midpoint(salary_dict: dict) -> float | None:
    """
    Return the midpoint for Annual_Salary__c.
    If only min is known, return min. If only max, return max.
    Converts hourly to annual (×2080) when no annual data exists.
    """
    ann_min = salary_dict.get("annual_salary_min")
    ann_max = salary_dict.get("annual_salary_max")

    if ann_min is not None and ann_max is not None:
        return (ann_min + ann_max) / 2
    if ann_min is not None:
        return ann_min
    if ann_max is not None:
        return ann_max

    # Fallback: convert hourly midpoint to annual
    hr = hourly_midpoint(salary_dict)
    if hr is not None:
        return hr * 2080

    return None


def hourly_midpoint(salary_dict: dict) -> float | None:
    """
    Return the midpoint for Hourly_Rate__c.
    If only min is known, return min. If only max, return max.
    """
    hr_min = salary_dict.get("hourly_rate_min")
    hr_max = salary_dict.get("hourly_rate_max")

    if hr_min is not None and hr_max is not None:
        return (hr_min + hr_max) / 2
    if hr_min is not None:
        return hr_min
    if hr_max is not None:
        return hr_max
    return None
