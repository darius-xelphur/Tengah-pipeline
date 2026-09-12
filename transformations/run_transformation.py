"""
Run a SQL transformation file against BigQuery.

Usage:
    python3 transformations/run_transformation.py staging_hdb_resale.sql
"""

import sys
import os
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account # type: ignore

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID = "tengah-analytics"
KEY_PATH   = "tengah-analytics-5ec133554c9a.json"
SQL_DIR    = Path(__file__).parent

# ── Credentials ───────────────────────────────────────────────────────────────
credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
client = bigquery.Client(project=PROJECT_ID, credentials=credentials)


def run_sql_file(filename):
    """Read a .sql file and execute it as a BigQuery script."""
    sql_path = SQL_DIR / filename

    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    print(f"Running: {filename}")
    sql = sql_path.read_text()

    job = client.query(sql)
    job.result()  # blocks until the script finishes

    # Multi-statement scripts report stats per child job
    print(f"✓ Completed — job id: {job.job_id}")
    if job.num_dml_affected_rows is not None:
        print(f"  Rows affected: {job.num_dml_affected_rows:,}")

    return job


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 transformations/run_transformation.py <filename.sql>")
        print("\nAvailable files:")
        for f in sorted(SQL_DIR.glob("*.sql")):
            print(f"  {f.name}")
        sys.exit(1)

    run_sql_file(sys.argv[1])