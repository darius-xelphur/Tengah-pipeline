from google.cloud import bigquery
from google.oauth2 import service_account # type: ignore

# Load credentials
credentials = service_account.Credentials.from_service_account_file(
    "tengah-analytics-5ec133554c9a.json"
)

# Connect to BigQuery
client = bigquery.Client(
    project="tengah-analytics",  # Replace with your actual project ID
    credentials=credentials
)

# Test 1 - simple query
print("Running connection test...")
query = "SELECT 'Connection successful!' AS status, CURRENT_TIMESTAMP() AS ts"
result = client.query(query).result()
for row in result:
    print(f"✓ {row.status} at {row.ts}")

# Test 2 - verify your datasets exist
print("\nChecking datasets...")
datasets = list(client.list_datasets())
for dataset in datasets:
    print(f"✓ Found dataset: {dataset.dataset_id}")

print("\nAll checks passed — you're ready to build!")