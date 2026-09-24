from db import run_query

def get_fleet_baseline(model):
    row = run_query("SELECT * FROM v_fleet_baseline WHERE model = %s", (model,))
    if not row:
        return {"error": f"No data for model {model}"}
    return row[0]

def get_drive_history(serial_number):
    drive_summary = run_query("SELECT * FROM mv_drive_summary WHERE serial_number = %s", (serial_number,))
    if not drive_summary:
        return {"error": f"No data for serial number {serial_number}"}
    pre_failure_trend = run_query("SELECT * FROM v_pre_failure_trend WHERE serial_number = %s ORDER BY date", (serial_number,))
    

    return {
        "drive_summary": drive_summary[0],
        "pre_failure_trend": pre_failure_trend,
    }

def run_sql(query): #Function to run any query
    try:
        result = run_query(query)
    except Exception as e:
        return {"error": str(e)}
    return result


if __name__ == "__main__":
    # print(get_fleet_baseline("TOSHIBA MG07ACA14TEY"))   # a dict, not a list
    # print(get_fleet_baseline("FAKE-MODEL"))             # error dict
    print(get_drive_history("1050A006F9RG"))            # summary + 6 trend days
    # print(get_drive_history("NOT-REAL"))                # error dict
    # print(run_sql("SELECT * FROM not_a_table"))         # error dict (the AI made a mistake)