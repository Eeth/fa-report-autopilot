GET_FLEET_BASELINE = {
    "name" : "get_fleet_baseline",
    "description": (
    "Returns a summary of the HEALTHY drives of one drive model, to serve as a 'normal' "
    "baseline. Fields: healthy_drives (how many healthy drives the summary is based on), "
    "avg_age_years, avg_temp_c, p95_reallocated / p95_pending / p95_uncorrect (95th-percentile "
    "counts of reallocated sectors, pending sectors, and uncorrectable errors), "
    "pct_with_reallocated and pct_with_pending (% of healthy drives with any such sectors). "
    "Use this while writing a failure report, after calling get_drive_history (which provides "
    "the model), to show how the failed drive differs from normal drives of the same model. "
    "If healthy_drives is below 30, the baseline is less reliable: say so in the report and "
    "lower your confidence. A value of None means the model does not report that attribute. "
    "Never treat null (None) as 0."
    ),    
    "input_schema" : {
        "type": "object",
        "properties": {
            "model": {
                "type" : "string",
                "description": "Model name, e.g. 'TOSHIBA MG07ACA14TEY'. Write exactly as returned by get_drive_history"
            }
        },
        "required": ["model"],
    },
}
GET_DRIVE_HISTORY = {
    "name": "get_drive_history",
    "description": (
        "Looks up one drive by serial number. Call this FIRST when asked to write a failure "
        "report for a drive. Returns two parts: "
        "(1) drive_summary: model, manufacturer, capacity_tb, first_seen, last_seen, "
        "days_observed, failed (true/false), failure_date, age_years, and the drive's latest "
        "SMART values. Use its 'model' value when calling get_fleet_baseline. "
        "(2) pre_failure_trend: one row per day, from up to 30 days before the failure through "
        "the failure day (at most 31 rows). Each row has days_before_failure and these SMART "
        "attributes: smart_5_raw = reallocated sectors, smart_187_raw = reported uncorrectable "
        "errors, smart_188_raw = command timeouts, smart_194_raw = temperature in Celsius, "
        "smart_197_raw = pending sectors, smart_198_raw = offline uncorrectable sectors, "
        "smart_199_raw = interface CRC errors (usually a cable or connection issue). "
        "Rules: if pre_failure_trend has fewer than 31 rows, state how many days of history "
        "were available. If failed is false, the drive has not failed, pre_failure_trend will "
        "be empty, and there is no failure to analyze; say so instead of writing a report. "
        "A value of null (None) means the drive did not report that attribute; never treat it "
        "as 0. If the serial number does not exist, the tool returns an error; tell the user "
        "instead of guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "serial_number": {
                "type": "string",
                "description": "Drive serial number, e.g. '1050A006F9RG'. Use it exactly as provided by the user.",
            }
        },
        "required": ["serial_number"],
    },
}

RUN_SQL = {
    "name": "run_sql",
    "description": (
        "Runs a read-only PostgreSQL SELECT query and returns at most 200 rows. Use it only for "
        "extra comparisons that get_drive_history and get_fleet_baseline cannot answer, such as "
        "whether other drives of the same model failed the same way, or how this model's failure "
        "rate compares to others. Do not use it if those two tools already have the answer. "
        "Available views: "
        "(1) v_failure_signatures: one row per FAILED drive. Columns: serial_number, model, "
        "manufacturer, failure_date, age_years, failure_signature (one of 'Media / surface "
        "degradation', 'Uncorrectable read errors', 'Interface / timeout', 'No SMART warning "
        "(sudden failure)'). "
        "(2) v_afr_by_model: annualized failure rate per model, corrected for sampling. Columns: "
        "model, manufacturer, est_drives, failures, afr_pct. Only includes models with enough "
        "data. Always use this view for failure rates. "
        "(3) v_fleet_kpis: one row of fleet-wide totals. Columns: est_fleet_drives, failures, "
        "fleet_afr_pct, pct_sudden_failures. "
        "(4) mv_drive_summary: one row per drive (all failed drives plus a 1-in-10 sample of "
        "healthy drives, so raw counts of healthy drives are about 10x too low). Columns: "
        "serial_number, model, failed, failure_date, age_years, and the latest SMART values. "
        "Select only the columns you need, filter with WHERE, and aggregate (COUNT, AVG, GROUP BY) "
        "rather than pulling raw rows. If the query fails, the tool returns an error message; "
        "fix the query and try again at most once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A single PostgreSQL SELECT statement, e.g. "
                    "\"SELECT failure_signature, COUNT(*) AS failures FROM v_failure_signatures "
                    "WHERE model = 'TOSHIBA MG07ACA14TEY' GROUP BY failure_signature\""
                ),
            }
        },
        "required": ["query"],
    },
}

TOOLS = [GET_DRIVE_HISTORY, GET_FLEET_BASELINE, RUN_SQL]