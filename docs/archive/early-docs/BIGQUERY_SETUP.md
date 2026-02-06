# BigQuery Integration Test Setup

This guide will help you set up credentials to run BigQuery integration tests in the devcontainer.

## Quick Setup (Service Account - Recommended for devcontainer)

Since the devcontainer doesn't have gcloud CLI installed, the easiest approach is to use a service account key file.

### Step 1: Create a Service Account in GCP

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **IAM & Admin** > **Service Accounts**
4. Click **Create Service Account**
   - Name: `sql-sentinel-testing`
   - Description: `Service account for SQL Sentinel BigQuery integration tests`
5. Click **Create and Continue**
6. Grant these roles:
   - **BigQuery Job User** (to run queries)
   - **BigQuery Data Viewer** (to read public datasets)
7. Click **Continue** > **Done**

### Step 2: Create and Download Key

1. Click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Choose **JSON** format
5. Click **Create** (the key file will download automatically)

### Step 3: Copy Key to Workspace

**Option A: Copy file content (Recommended)**
1. Open the downloaded JSON file in a text editor
2. Copy the entire content
3. Create a new file in the workspace:
   ```bash
   nano /workspace/.bigquery_credentials.json
   ```
4. Paste the JSON content
5. Save and exit (Ctrl+X, then Y, then Enter)

**Option B: Upload file**
1. Upload the downloaded JSON file to `/workspace/.bigquery_credentials.json`
2. The file is already in `.gitignore` so it won't be committed

### Step 4: Set Environment Variables

```bash
# Your GCP Project ID (find it in GCP Console or in the JSON key file)
export BIGQUERY_PROJECT_ID=your-project-id

# Path to the credentials file
export GOOGLE_APPLICATION_CREDENTIALS=/workspace/.bigquery_credentials.json
```

### Step 5: Run the Tests

```bash
# Run all BigQuery integration tests
./test_bigquery.sh

# Or run directly with pytest
poetry run pytest tests/integration/test_bigquery_integration.py -v
```

## Alternative: Add gcloud to Devcontainer (Advanced)

If you prefer to use ADC (Application Default Credentials), you can add gcloud to the devcontainer:

1. Edit `.devcontainer/Dockerfile` to install gcloud CLI
2. Rebuild the devcontainer
3. Run `gcloud auth application-default login` inside the container

However, this is more complex and requires rebuilding the container.

## Verify Setup

Test that your credentials work:

```bash
# Should print your project ID
echo $BIGQUERY_PROJECT_ID

# Should print the path to credentials file
echo $GOOGLE_APPLICATION_CREDENTIALS

# Should show the file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

## Quick Test

Run a single simple test to verify everything works:

```bash
poetry run pytest tests/integration/test_bigquery_integration.py::TestBigQueryAdapterIntegration::test_connect_and_disconnect -v
```

If this test passes, all credentials are configured correctly!

## Security Notes

- ⚠️ **Never commit** the credentials JSON file to git
- ✅ The `.bigquery_credentials.json` file is already in `.gitignore`
- ✅ The credentials file should have restricted permissions:
  ```bash
  chmod 600 /workspace/.bigquery_credentials.json
  ```

## Troubleshooting

### Error: "Connection string cannot be empty"
- Make sure `BIGQUERY_PROJECT_ID` is set: `echo $BIGQUERY_PROJECT_ID`

### Error: "Service account key file not found"
- Make sure `GOOGLE_APPLICATION_CREDENTIALS` points to the correct file
- Verify the file exists: `ls -la $GOOGLE_APPLICATION_CREDENTIALS`

### Error: "403 Permission denied"
- Your service account needs these IAM roles:
  - BigQuery Job User
  - BigQuery Data Viewer
- Grant roles in GCP Console > IAM & Admin > IAM

### Error: "Project not found"
- Double-check your project ID is correct
- Ensure the project exists in your GCP account
- The project ID is in the downloaded JSON file under `"project_id"`

## Cost Information

- ✅ **BigQuery public datasets are free to query**
- ✅ **First 1 TB of query data processed per month is free**
- ✅ **These tests query < 1 MB of data total**
- ✅ **No cost for running these integration tests**

## Need Help?

The integration tests are in: `tests/integration/test_bigquery_integration.py`
Documentation is in: `tests/integration/README_BIGQUERY.md`
