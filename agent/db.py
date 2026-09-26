import os
import psycopg                         # Postgres library (you used it on Day 1)
from psycopg.rows import dict_row      # makes each row come back as a dict

from dotenv import load_dotenv   # a tool that reads the .env file


load_dotenv()                     # load .env into environment variables

def run_query(sql, params=None, max_rows=200):
    """Run a read-only SQL query and return a list of dicts (at most max_rows)."""
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=5) as conn:
        conn.read_only = True
        rows = conn.execute(sql, params).fetchmany(max_rows)
    return rows

