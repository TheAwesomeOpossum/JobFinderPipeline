"""ATS domain registry and Google CSE query builder."""

# Map ATS domain → parser type
ATS_SITES = [
    {"domain": "boards.greenhouse.io",      "ats_type": "greenhouse"},
    {"domain": "jobs.lever.co",             "ats_type": "lever"},
    {"domain": "wd1.myworkdayjobs.com",     "ats_type": "workday"},
    {"domain": "jobs.ashbyhq.com",          "ats_type": "ashby"},
    {"domain": "jobs.smartrecruiters.com",  "ats_type": "smartrecruiters"},
    {"domain": "linkedin.com/jobs/view",    "ats_type": "linkedin"},
]


def build_query(domain: str, keywords: str) -> str:
    """Build a Google CSE query string for a given ATS domain."""
    return f'site:{domain} {keywords}'
