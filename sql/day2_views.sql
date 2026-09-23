-- Day 2: chart-ready views for the Superset dashboard.
-- Run after sql/views.sql:
--   Get-Content sql\day2_views.sql | docker exec -i fa_postgres psql -U fa -d fa

-- Cache the expensive per-drive rollups so dashboard charts load fast.
-- If you ever reload the data, just rerun this whole file.
DROP MATERIALIZED VIEW IF EXISTS mv_drive_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_failure_signatures CASCADE;
CREATE MATERIALIZED VIEW mv_drive_summary AS SELECT * FROM v_drive_summary;
CREATE UNIQUE INDEX ON mv_drive_summary (serial_number);
CREATE MATERIALIZED VIEW mv_failure_signatures AS SELECT * FROM v_failure_signatures;

-- ---------------------------------------------------------------------------
-- Sampling correction.
-- load_data.py kept EVERY failed drive but only healthy_pct% of healthy drives,
-- so raw AFR is inflated. Each sampled healthy drive stands in for
-- (100 / healthy_pct) drives, so we weight it that way. Change the value below
-- if you reload with a different --healthy-pct.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS load_config CASCADE;
CREATE TABLE load_config (healthy_pct NUMERIC NOT NULL);
INSERT INTO load_config VALUES (10);

CREATE OR REPLACE VIEW v_drive_weights AS
SELECT
    s.serial_number,
    s.model,
    s.manufacturer,
    s.failed,
    s.days_observed,
    CASE WHEN s.failed THEN 1.0 ELSE 100.0 / c.healthy_pct END AS weight
FROM mv_drive_summary s
CROSS JOIN load_config c;


-- 1) Headline numbers for the KPI tiles.
CREATE OR REPLACE VIEW v_fleet_kpis AS
SELECT
    COUNT(*)                                                     AS drives_loaded,
    ROUND(SUM(weight))                                           AS est_fleet_drives,
    SUM(failed::int)                                             AS failures,
    ROUND(100.0 * SUM(failed::int) / (SUM(days_observed * weight) / 365.0), 2) AS fleet_afr_pct,
    (SELECT ROUND(100.0 * AVG((failure_signature = 'No SMART warning (sudden failure)')::int), 1)
       FROM mv_failure_signatures)                                AS pct_sudden_failures
FROM v_drive_weights;


-- 2) Corrected AFR by model (use this instead of v_failure_rate_by_model in charts).
CREATE OR REPLACE VIEW v_afr_by_model AS
SELECT
    model,
    manufacturer,
    ROUND(SUM(weight))                                                         AS est_drives,
    SUM(failed::int)                                                           AS failures,
    ROUND(SUM(days_observed * weight))                                         AS est_drive_days,
    ROUND(100.0 * SUM(failed::int) / (SUM(days_observed * weight) / 365.0), 2) AS afr_pct
FROM v_drive_weights
GROUP BY model, manufacturer
HAVING SUM(days_observed * weight) >= 20000     -- enough exposure to be meaningful
   AND SUM(failed::int) >= 2;


-- 3) Corrected AFR by manufacturer.
CREATE OR REPLACE VIEW v_afr_by_manufacturer AS
SELECT
    manufacturer,
    ROUND(SUM(weight))                                                         AS est_drives,
    SUM(failed::int)                                                           AS failures,
    ROUND(100.0 * SUM(failed::int) / (SUM(days_observed * weight) / 365.0), 2) AS afr_pct
FROM v_drive_weights
GROUP BY manufacturer;


-- 4) Failure-mode mix (for a bar or pie chart).
CREATE OR REPLACE VIEW v_failure_signature_mix AS
SELECT
    failure_signature,
    COUNT(*)                                             AS failures,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS pct_of_failures
FROM mv_failure_signatures
GROUP BY failure_signature;


-- 5) Failures per week (smoother than daily for a trend line).
CREATE OR REPLACE VIEW v_weekly_failures AS
SELECT
    DATE_TRUNC('week', date)::date   AS week_start,
    SUM(failure)                     AS failures
FROM drive_days
GROUP BY 1;


-- 6) Drill-down: SMART trend for one failed drive, in "long" format so one
--    line chart can show every attribute, filtered by serial_number.
CREATE OR REPLACE VIEW v_pre_failure_trend_long AS
SELECT serial_number, model, failure_date, date, days_before_failure, attribute, value
FROM v_pre_failure_trend
CROSS JOIN LATERAL (VALUES
    ('Reallocated sectors (5)',     smart_5_raw),
    ('Uncorrectable errors (187)',  smart_187_raw),
    ('Command timeouts (188)',      smart_188_raw),
    ('Pending sectors (197)',       smart_197_raw),
    ('Offline uncorrectable (198)', smart_198_raw),
    ('CRC errors (199)',            smart_199_raw)
) AS a(attribute, value)
WHERE value IS NOT NULL;
