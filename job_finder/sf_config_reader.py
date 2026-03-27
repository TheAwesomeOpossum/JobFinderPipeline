"""Read Job_Search_Config__c records from Salesforce and map to profile dicts."""

import json
import logging
import time
from datetime import datetime, timezone

from simple_salesforce import Salesforce, SalesforceExpiredSession

logger = logging.getLogger(__name__)

_SOQL = """
SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c,
       Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c,
       Schedule_Minute__c, Days_Back__c
FROM Job_Search_Config__c
WHERE Is_Active__c = true
ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC
"""


def load_sf_profiles(sf: Salesforce) -> list[dict]:
    """
    Query active Job_Search_Config__c records and return as profile dicts.
    Returns empty list if the query fails (caller should fall back to YAML).
    """
    try:
        result = sf.query(_SOQL)
    except SalesforceExpiredSession:
        raise
    except Exception as exc:
        logger.warning("Could not query Job_Search_Config__c: %s — falling back to YAML", exc)
        return []

    records = result.get("records", [])
    if not records:
        logger.info("No active Job_Search_Config__c records found — falling back to YAML")
        return []

    profiles = [_map_record(r) for r in records]
    logger.info("Loaded %d profile(s) from Salesforce", len(profiles))
    return profiles


def _map_record(record: dict) -> dict:
    """Map a Job_Search_Config__c record to a profile dict."""
    def _split_multiselect(value) -> list[str]:
        if not value:
            return []
        return [s.strip() for s in str(value).split(";") if s.strip()]

    return {
        "profile_name":      record["Name"],
        "keywords":          record.get("Keywords__c") or "",
        "required_skills":   _split_multiselect(record.get("Required_Skills__c")),
        "bonus_skills":      _split_multiselect(record.get("Bonus_Skills__c")),
        "limit":             int(record.get("Daily_Limit__c") or 10),
        "min_annual_salary": float(record.get("Min_Annual_Salary__c") or 0),
        "schedule_hour":     int(record.get("Schedule_Hour__c") or 2),
        "schedule_minute":   int(record.get("Schedule_Minute__c") or 0),
        "days":              int(record.get("Days_Back__c") or 1),
        "sf_record_id":      record["Id"],
    }


def writeback(sf: Salesforce, config_id: str, summary: dict) -> None:
    """
    Write Last_Run_At__c and Last_Run_Summary__c back to the config record.
    Non-fatal — logs a warning on failure.
    """
    payload = {
        "Last_Run_At__c":      datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Last_Run_Summary__c": json.dumps(summary),
    }
    try:
        from job_finder.sf_writer import _with_backoff
        _with_backoff(lambda: sf.Job_Search_Config__c.update(config_id, payload))
        logger.info("Wrote back run summary to Job_Search_Config__c/%s", config_id)
    except SalesforceExpiredSession:
        raise
    except Exception as exc:
        logger.warning("Could not write back to Job_Search_Config__c/%s: %s", config_id, exc)
