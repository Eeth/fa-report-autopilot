import os
import psycopg                         # Postgres library (you used it on Day 1)
from psycopg.rows import dict_row      # makes each row come back as a dict

from dotenv import load_dotenv   # a tool that reads the .env file


load_dotenv()                     # load .env into environment variables

# with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
#     rows = conn.execute("SELECT COUNT(*) AS n FROM drive_days").fetchall()

#     print(rows)    # [{'n': 3079458}]


def run_query(sql, params=None, max_rows=200):
    """Run a read-only SQL query and return a list of dicts (at most max_rows)."""
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
        conn.read_only = True
        rows = conn.execute(sql, params).fetchmany(max_rows)
    return rows


if __name__ == "__main__":
    print(run_query("SELECT COUNT(*) AS n FROM drive_days"))
    print(run_query("SELECT serial_number, model FROM mv_drive_summary WHERE failed LIMIT %s", (3,)))
    print(run_query("DELETE FROM drive_days"))   # this SHOULD fail