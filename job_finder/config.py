import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value


# Google
GOOGLE_API_KEY = _require("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = _require("GOOGLE_CSE_ID")

# Anthropic
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# Salesforce
SF_USERNAME       = _require("SF_USERNAME")
SF_PASSWORD       = _require("SF_PASSWORD")
SF_SECURITY_TOKEN = _require("SF_SECURITY_TOKEN")
SF_DOMAIN         = os.getenv("SF_DOMAIN", "login")

# PostgreSQL
PG_HOST     = os.getenv("PG_HOST", "localhost")
PG_PORT     = int(os.getenv("PG_PORT", "5432"))
PG_DBNAME   = _require("PG_DBNAME")
PG_USER     = _require("PG_USER")
PG_PASSWORD = _require("PG_PASSWORD")
PG_SSLMODE  = os.getenv("PG_SSLMODE", "require")

# Pipeline tuning
DAILY_LIMIT         = int(os.getenv("DAILY_LIMIT", "20"))
DEFAULT_KEYWORDS    = os.getenv("DEFAULT_KEYWORDS", "Software Developer,Software Engineer")
LOCATION_PREFERENCE = os.getenv("LOCATION_PREFERENCE", "Remote")
SENIORITY_TARGETS   = [s.strip().lower() for s in os.getenv("SENIORITY_TARGETS", "mid,senior").split(",")]

# Salary threshold — jobs with a known max salary below this are hard-filtered
# Set to 0 (default) to disable filtering
MIN_ANNUAL_SALARY = float(os.getenv("MIN_ANNUAL_SALARY", "0"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
