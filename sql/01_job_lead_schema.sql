CREATE TABLE IF NOT EXISTS job_lead (
    id              SERIAL PRIMARY KEY,
    url_hash        CHAR(64)     NOT NULL UNIQUE,
    url             TEXT         NOT NULL,
    title           TEXT,
    company         TEXT,
    ats_type        VARCHAR(30),
    score           INTEGER,
    req_number      TEXT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'new',
    sf_job_app_id   VARCHAR(18),
    sf_account_id   VARCHAR(18),
    error_message   TEXT,
    discovered_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_lead_status ON job_lead (status);
CREATE INDEX IF NOT EXISTS idx_job_lead_discovered ON job_lead (discovered_at DESC);
-- trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_job_lead_updated_at
BEFORE UPDATE ON job_lead
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
