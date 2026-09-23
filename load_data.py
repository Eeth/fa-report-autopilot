"""
Day 1 loader: Backblaze drive-stats CSVs -> Postgres.

Usage:
    python load_data.py --data-dir ./data/data_Q2_2025 --healthy-pct 10

- Keeps EVERY drive that failed during the period (all of its days).
- Keeps a random-but-repeatable sample of healthy drives (--healthy-pct),
  so a laptop can handle a full quarter. Use --healthy-pct 100 to keep all.
- Loads only the columns we need (the SMART attributes FA engineers care about),
  which also protects us from Backblaze adding/removing columns between quarters.
"""
import argparse
import glob
import os
import time

import duckdb
import psycopg

# SMART attributes most associated with drive failure
#   5   Reallocated sectors count
#   9   Power-on hours
#   187 Reported uncorrectable errors
#   188 Command timeout
#   194 Temperature (Celsius)
#   197 Current pending sector count
#   198 Offline uncorrectable sectors
#   199 UDMA CRC error count (usually cable/connection issues)
SMART_IDS = [5, 9, 187, 188, 194, 197, 198, 199]
SMART_COLS = [f"smart_{i}_raw" for i in SMART_IDS]

DEFAULT_DSN = "postgresql://fa:fa@localhost:5432/fa"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="folder containing the daily YYYY-MM-DD.csv files")
    ap.add_argument("--healthy-pct", type=int, default=10, help="percent of healthy drives to keep (1-100)")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL", DEFAULT_DSN))
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.data_dir, "**", "*.csv"), recursive=True))
    if not files:
        raise SystemExit(f"No CSV files found under {args.data_dir}")
    print(f"Found {len(files)} daily CSV files ({os.path.basename(files[0])} .. {os.path.basename(files[-1])})")

    t0 = time.time()
    con = duckdb.connect()
    smart_select = ",\n            ".join(f"TRY_CAST({c} AS BIGINT) AS {c}" for c in SMART_COLS)
    pattern = os.path.join(args.data_dir, "**", "*.csv")

    # 1) Read all CSVs (keeping only the columns we need), then keep every failed
    #    drive + a repeatable sample of healthy ones. A full quarter is ~12 GB of CSV;
    #    DuckDB streams it and never holds the whole thing in memory.
    con.execute(f"""
        CREATE TABLE sampled AS
        WITH raw AS (
            SELECT
                CAST(date AS DATE)                 AS date,
                serial_number,
                TRIM(model)                        AS model,
                TRY_CAST(capacity_bytes AS BIGINT) AS capacity_bytes,
                CAST(failure AS SMALLINT)          AS failure,
                {smart_select}
            FROM read_csv('{pattern}', union_by_name=true, header=true, all_varchar=true)
        )
        SELECT * FROM raw
        WHERE serial_number IN (SELECT serial_number FROM raw WHERE failure = 1)
           OR (hash(serial_number) % 100) < {args.healthy_pct}
    """)
    n_rows, n_drives, n_failed = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT serial_number),
               COUNT(DISTINCT serial_number) FILTER (WHERE failure = 1)
        FROM sampled
    """).fetchone()
    print(f"Read + sampled in {time.time() - t0:.1f}s: {n_rows:,} rows, {n_drives:,} drives, {n_failed:,} failed")

    # 3) Load into Postgres with COPY (fast).
    cols = ["date", "serial_number", "model", "capacity_bytes", "failure"] + SMART_COLS
    smart_ddl = ",\n        ".join(f"{c} BIGINT" for c in SMART_COLS)
    with psycopg.connect(args.dsn, autocommit=True) as pg:
        pg.execute("DROP TABLE IF EXISTS drive_days CASCADE")
        pg.execute(f"""
            CREATE TABLE drive_days (
                date            DATE    NOT NULL,
                serial_number   TEXT    NOT NULL,
                model           TEXT    NOT NULL,
                capacity_bytes  BIGINT,
                failure         SMALLINT NOT NULL,
                {smart_ddl}
            )
        """)
        t1 = time.time()
        with pg.cursor() as cur:
            with cur.copy(f"COPY drive_days ({', '.join(cols)}) FROM STDIN") as copy:
                result = con.execute(f"SELECT {', '.join(cols)} FROM sampled")
                while True:
                    batch = result.fetchmany(50_000)
                    if not batch:
                        break
                    for row in batch:
                        copy.write_row(row)
        print(f"Copied into Postgres in {time.time() - t1:.1f}s")

        pg.execute("CREATE INDEX ON drive_days (serial_number, date)")
        pg.execute("CREATE INDEX ON drive_days (model)")
        pg.execute("CREATE INDEX ON drive_days (date) WHERE failure = 1")
        pg.execute("ANALYZE drive_days")

    print(f"Done in {time.time() - t0:.1f}s total. Next: psql -f sql/views.sql")


if __name__ == "__main__":
    main()
