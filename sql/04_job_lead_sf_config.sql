-- Phase 5: link job_lead rows to the SF config record that produced them.
-- Nullable — jobs from YAML-fallback runs have no config ID.
ALTER TABLE job_lead
    ADD COLUMN IF NOT EXISTS sf_search_config_id VARCHAR(18);
