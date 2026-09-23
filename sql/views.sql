-- Day 1 SQL views for the FA Report Autopilot.
-- Run with:  psql postgresql://fa:fa@localhost:5432/fa -f sql/views.sql
-- These are what the dashboard (Day 2) and the agent's tools (Day 3) will query.

-- Helper: manufacturer from model string (Backblaze model names are inconsistent).
CREATE OR REPLACE FUNCTION manufacturer(model TEXT) RETURNS TEXT
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN model ILIKE 'WDC%' OR model ILIKE 'WD%' OR model ILIKE 'WUH%' THEN 'Western Digital'
        WHEN model ILIKE 'HGST%' OR model ILIKE 'HMS%' OR model ILIKE 'HUH%' THEN 'HGST (WD)'
        WHEN model ILIKE 'ST%'      THEN 'Seagate'
        WHEN model ILIKE 'TOSHIBA%' OR model ILIKE 'MG%' THEN 'Toshiba'
        ELSE 'Other'
    END
$$;


-- 1) One row per drive: its life in this dataset and its latest SMART readings.
--    Agent tool: get_drive_history(serial) starts here.
CREATE OR REPLACE VIEW v_drive_summary AS
WITH latest AS (
    SELECT DISTINCT ON (serial_number) *
    FROM drive_days
    ORDER BY serial_number, date DESC
)
SELECT
    d.serial_number,
    l.model,
    manufacturer(l.model)                          AS manufacturer,
    ROUND(l.capacity_bytes / 1e12, 1)              AS capacity_tb,
    MIN(d.date)                                    AS first_seen,
    MAX(d.date)                                    AS last_seen,
    COUNT(*)                                       AS days_observed,
    BOOL_OR(d.failure = 1)                         AS failed,
    MAX(d.date) FILTER (WHERE d.failure = 1)       AS failure_date,
    ROUND(l.smart_9_raw / 24.0 / 365, 2)           AS age_years,
    l.smart_5_raw   AS reallocated_sectors,
    l.smart_187_raw AS reported_uncorrect,
    l.smart_188_raw AS command_timeout,
    l.smart_194_raw AS temperature_c,
    l.smart_197_raw AS pending_sectors,
    l.smart_198_raw AS offline_uncorrectable,
    l.smart_199_raw AS crc_errors
FROM drive_days d
JOIN latest l USING (serial_number)
GROUP BY d.serial_number, l.model, l.capacity_bytes, l.smart_9_raw, l.smart_5_raw,
         l.smart_187_raw, l.smart_188_raw, l.smart_194_raw, l.smart_197_raw,
         l.smart_198_raw, l.smart_199_raw;


-- 2) Annualized failure rate (AFR) by model — the standard Backblaze metric.
--    AFR % = failures / (drive_days / 365) * 100
--    NOTE: healthy drives are sampled in load_data.py, so absolute AFR is inflated
--    unless you load with --healthy-pct 100. Relative ranking is still useful.
CREATE OR REPLACE VIEW v_failure_rate_by_model AS
SELECT
    model,
    manufacturer(model)                                   AS manufacturer,
    COUNT(DISTINCT serial_number)                         AS drives,
    COUNT(*)                                              AS drive_days,
    SUM(failure)                                          AS failures,
    ROUND(100.0 * SUM(failure) / (COUNT(*) / 365.0), 2)   AS afr_pct
FROM drive_days
GROUP BY model
HAVING COUNT(*) >= 10000          -- ignore models with too little exposure
ORDER BY afr_pct DESC;


-- 3) Failures per day (for a time-series chart).
CREATE OR REPLACE VIEW v_daily_failures AS
SELECT
    date,
    SUM(failure)                          AS failures,
    COUNT(*)                              AS drives_reporting
FROM drive_days
GROUP BY date
ORDER BY date;


-- 4) SMART trend for every failed drive in the 30 days before it failed.
--    This is the "evidence" section of an FA report.
CREATE OR REPLACE VIEW v_pre_failure_trend AS
WITH failures AS (
    SELECT serial_number, date AS failure_date
    FROM drive_days
    WHERE failure = 1
)
SELECT
    d.serial_number,
    d.model,
    f.failure_date,
    d.date,
    (f.failure_date - d.date)  AS days_before_failure,
    d.smart_5_raw, d.smart_187_raw, d.smart_188_raw, d.smart_194_raw,
    d.smart_197_raw, d.smart_198_raw, d.smart_199_raw
FROM drive_days d
JOIN failures f USING (serial_number)
WHERE d.date BETWEEN f.failure_date - 30 AND f.failure_date;


-- 5) Fleet baseline per model: what "normal" looks like for HEALTHY drives
--    on their most recent day. The agent compares a failed drive against this.
--    Agent tool: get_fleet_baseline(model).
CREATE OR REPLACE VIEW v_fleet_baseline AS
SELECT
    model,
    COUNT(*)                                                                        AS healthy_drives,
    ROUND(AVG(age_years), 2)                                                        AS avg_age_years,
    ROUND(AVG(temperature_c), 1)                                                    AS avg_temp_c,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY reallocated_sectors)               AS p95_reallocated,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY pending_sectors)                   AS p95_pending,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY reported_uncorrect)                AS p95_uncorrect,
    ROUND(100.0 * AVG((COALESCE(reallocated_sectors, 0) > 0)::int), 2)              AS pct_with_reallocated,
    ROUND(100.0 * AVG((COALESCE(pending_sectors, 0) > 0)::int), 2)                  AS pct_with_pending
FROM v_drive_summary
WHERE NOT failed
GROUP BY model;


-- 6) Which SMART warning signs were present at failure?
--    Rough failure-mode buckets an FA engineer would recognize.
CREATE OR REPLACE VIEW v_failure_signatures AS
SELECT
    serial_number,
    model,
    manufacturer,
    failure_date,
    age_years,
    CASE
        WHEN COALESCE(reallocated_sectors,0) > 0 OR COALESCE(pending_sectors,0) > 0
             OR COALESCE(offline_uncorrectable,0) > 0           THEN 'Media / surface degradation'
        WHEN COALESCE(reported_uncorrect,0) > 0                 THEN 'Uncorrectable read errors'
        WHEN COALESCE(command_timeout,0) > 0
             OR COALESCE(crc_errors,0) > 0                      THEN 'Interface / timeout'
        ELSE 'No SMART warning (sudden failure)'
    END AS failure_signature
FROM v_drive_summary
WHERE failed;
