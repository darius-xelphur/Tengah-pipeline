import requests # type: ignore
import pandas as pd # type: ignore
import time
import io
import os
from dotenv import load_dotenv # type: ignore
from google.cloud import bigquery
from google.oauth2 import service_account # type: ignore

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

API_KEY    = os.getenv("DATA_GOV_API_KEY")
DATASET_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
BASE_URL   = "https://api-open.data.gov.sg/v1/public/api/datasets"
PROJECT_ID = "tengah-analytics"
DATASET    = "raw"
TABLE      = "hdb_resale_transactions"
KEY_PATH   = "tengah-analytics-5ec133554c9a.json"
HEADERS    = {"x-api-key": API_KEY}

# ── Credentials ───────────────────────────────────────────────────────────────
credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

# ── Step 1: Initiate Download ─────────────────────────────────────────────────
def initiate_download():
    print("Step 1: Initiating download...")
    url = f"{BASE_URL}/{DATASET_ID}/initiate-download"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("code") != 0:
        raise ValueError(f"Initiate download failed: {data}")

    print("✓ Download initiated successfully")
    return data["data"]["url"]  # polling URL not needed — direct URL returned

# ── Step 2: Poll Until Ready ──────────────────────────────────────────────────
def poll_download():
    print("Step 2: Polling for download readiness...")
    url = f"{BASE_URL}/{DATASET_ID}/poll-download"

    for attempt in range(20):  # max ~2 minutes
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        data = response.json()
        status = data["data"].get("status")
        print(f"  Attempt {attempt + 1}: {status}")

        if status == "DOWNLOAD_SUCCESS":
            download_url = data["data"]["url"]
            print("✓ File ready")
            return download_url
        elif status == "ERROR":
            raise ValueError(f"Poll download failed: {data}")

        time.sleep(6)

    raise TimeoutError("File not ready after maximum polling attempts")

# ── Step 3: Download CSV ──────────────────────────────────────────────────────
def download_csv(download_url):
    print("Step 3: Downloading CSV...")
    response = requests.get(download_url, timeout=120)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))
    print(f"✓ Downloaded {len(df):,} rows, {len(df.columns)} columns")
    return df

# ── Step 4: Validate ──────────────────────────────────────────────────────────
def validate(df):
    print("\nStep 4: Validating data...")

    if len(df) == 0:
        raise ValueError("Empty dataframe — aborting load")

    required_cols = ["month", "town", "flat_type", "resale_price"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    null_prices = df["resale_price"].isna().sum()
    if null_prices > 0:
        print(f"  ⚠ Warning: {null_prices} rows with null resale_price")

    print(f"✓ Validation passed — {len(df):,} rows")
    return df

# ── Step 5: Load to BigQuery ──────────────────────────────────────────────────
def load_to_bigquery(df):
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    print(f"\nStep 5: Loading to BigQuery → {table_ref}...")

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()

    table = client.get_table(table_ref)
    print(f"✓ Loaded {table.num_rows:,} rows to {table_ref}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("HDB Resale Transactions — Raw Ingestion")
    print("=" * 60)

    initiate_download()          # Step 1 — trigger the job
    download_url = poll_download()  # Step 2 — wait until ready
    df = download_csv(download_url) # Step 3 — pull CSV into pandas
    df = validate(df)            # Step 4 — quality checks
    load_to_bigquery(df)         # Step 5 — land in BigQuery raw layer

    print("\n✓ Pipeline complete!")