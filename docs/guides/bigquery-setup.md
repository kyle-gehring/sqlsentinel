# BigQuery Setup Guide

This guide walks you through setting up SQL Sentinel to work with Google BigQuery.

## Prerequisites

- Google Cloud Platform (GCP) account
- A GCP project with BigQuery API enabled
- BigQuery datasets you want to monitor
- SQL Sentinel installed (`poetry install`)

## Quick Start

### 1. Enable BigQuery API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** > **Library**
4. Search for "BigQuery API"
5. Click **Enable**

### 2. Create Service Account

1. Go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Enter details:
   - **Name**: `sql-sentinel`
   - **Description**: `Service account for SQL Sentinel alerting`
4. Click **Create and Continue**
5. Grant roles:
   - **BigQuery Job User** (required - to run queries)
   - **BigQuery Data Viewer** (required - to read data)
6. Click **Continue** > **Done**

### 3. Create and Download Key

1. Click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Choose **JSON** format
5. Click **Create** (key file downloads automatically)
6. **Save this file securely** - it contains credentials

### 4. Configure SQL Sentinel

Create an alerts configuration file (e.g., `my-bigquery-alerts.yaml`):

```yaml
database:
  # Format: bigquery://PROJECT_ID/DATASET
  url: "bigquery://my-gcp-project"

alerts:
  - name: "data_freshness_check"
    description: "Alert if no new data in last 24 hours"
    enabled: true
    query: |
      SELECT
        CASE
          WHEN MAX(updated_at) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
          THEN 'ALERT'
          ELSE 'OK'
        END as status,
        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(updated_at), HOUR) as actual_value,
        24 as threshold
      FROM `my-gcp-project.my_dataset.my_table`
    schedule: "0 */6 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

### 5. Set Environment Variables

```bash
# Path to your service account key file
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional: Set project ID explicitly (can also be in connection URL)
export BIGQUERY_PROJECT_ID=my-gcp-project
```

### 6. Run Alerts

```bash
# Test a single alert
sqlsentinel run my-bigquery-alerts.yaml --alert data_freshness_check

# Run all alerts
sqlsentinel run my-bigquery-alerts.yaml

# Run as daemon (continuous monitoring)
sqlsentinel daemon my-bigquery-alerts.yaml
```

## Connection String Format

### Basic Format

```
bigquery://PROJECT_ID/DATASET?credentials=/path/to/key.json&location=US
```

### Components

- `PROJECT_ID` - Your GCP project ID (required)
- `DATASET` - Default dataset for queries (optional)
- `credentials` - Path to service account JSON key (optional if using ADC)
- `location` - BigQuery location (optional, default: US)

### Examples

```yaml
# Minimal (uses Application Default Credentials)
database:
  url: "bigquery://my-project"

# With default dataset
database:
  url: "bigquery://my-project/analytics"

# With explicit credentials
database:
  url: "bigquery://my-project?credentials=/keys/sa.json"

# With location
database:
  url: "bigquery://my-project?location=EU"

# Full specification
database:
  url: "bigquery://my-project/analytics?credentials=/keys/sa.json&location=US"
```

## Authentication Methods

### Method 1: Service Account Key File (Recommended for Production)

**Pros:**
- Explicit credentials
- Works in any environment
- Easy to manage permissions
- Portable across systems

**Setup:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**In YAML:**
```yaml
database:
  url: "bigquery://project?credentials=/path/to/key.json"
```

### Method 2: Application Default Credentials (ADC)

**Pros:**
- No key file management
- Works seamlessly in GCP environments
- Good for local development

**Setup:**
```bash
# One-time setup
gcloud auth application-default login

# Use in YAML
database:
  url: "bigquery://my-project"  # No credentials parameter needed
```

**Best for:**
- Local development
- Running in Google Cloud (GCE, Cloud Run, GKE)
- Cloud Shell

## Required Permissions

Your service account needs these IAM roles:

### Minimum Required

- **BigQuery Job User** (`roles/bigquery.jobUser`)
  - Allows running queries
  - Required for all operations

- **BigQuery Data Viewer** (`roles/bigquery.dataViewer`)
  - Allows reading table data
  - Required for running SELECT queries

### Optional (for specific features)

- **BigQuery Metadata Viewer** (`roles/bigquery.metadataViewer`)
  - For schema validation alerts
  - For accessing INFORMATION_SCHEMA

- **BigQuery Resource Viewer** (`roles/bigquery.resourceViewer`)
  - For cost monitoring queries
  - For accessing INFORMATION_SCHEMA.JOBS

### Granting Permissions

**Option 1: Console**
1. Go to **IAM & Admin** > **IAM**
2. Find your service account
3. Click **Edit** (pencil icon)
4. Click **Add Another Role**
5. Select the required roles
6. Click **Save**

**Option 2: gcloud CLI**
```bash
# Set variables
PROJECT_ID="my-gcp-project"
SA_EMAIL="sql-sentinel@my-project.iam.gserviceaccount.com"

# Grant BigQuery Job User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.jobUser"

# Grant BigQuery Data Viewer
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataViewer"
```

## Testing Your Setup

### Test 1: Simple Query

```bash
# Create test file: test-bigquery.yaml
cat > test-bigquery.yaml <<EOF
database:
  url: "bigquery://my-project"

alerts:
  - name: "test_connection"
    description: "Test BigQuery connection"
    enabled: true
    query: |
      SELECT
        'OK' as status,
        1 as actual_value,
        1 as threshold
    schedule: "* * * * *"
    notify:
      - channel: email
        recipients: ["test@example.com"]
EOF

# Run test
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
sqlsentinel run test-bigquery.yaml --alert test_connection
```

### Test 2: Query Public Dataset

```bash
# Test with BigQuery public data
cat > test-public-data.yaml <<EOF
database:
  url: "bigquery://my-project"

alerts:
  - name: "test_public_data"
    description: "Query BigQuery public dataset"
    enabled: true
    query: |
      SELECT
        'OK' as status,
        COUNT(*) as actual_value,
        0 as threshold
      FROM \`bigquery-public-data.usa_names.usa_1910_current\`
      WHERE year = 2020
      LIMIT 10
    schedule: "* * * * *"
    notify:
      - channel: email
        recipients: ["test@example.com"]
EOF

sqlsentinel run test-public-data.yaml --alert test_public_data
```

## Troubleshooting

### Error: "Connection string cannot be empty"

**Cause:** Database URL not set or invalid

**Solution:**
```yaml
database:
  url: "bigquery://your-project-id"  # Make sure this is set!
```

### Error: "Service account key file not found"

**Cause:** Credentials path is incorrect or file doesn't exist

**Solution:**
```bash
# Check file exists
ls -la /path/to/service-account.json

# Fix path
export GOOGLE_APPLICATION_CREDENTIALS=/correct/path/to/key.json
```

### Error: "Failed to load Application Default Credentials"

**Cause:** ADC not configured and no service account key provided

**Solution:**
```bash
# Option 1: Use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Option 2: Configure ADC
gcloud auth application-default login
```

### Error: "403 Permission denied"

**Cause:** Service account lacks required permissions

**Solution:**
1. Go to **IAM & Admin** > **IAM**
2. Find your service account
3. Add roles:
   - `BigQuery Job User`
   - `BigQuery Data Viewer`

### Error: "404 Not found: Dataset PROJECT:DATASET"

**Cause:** Dataset doesn't exist or service account can't access it

**Solution:**
1. Verify dataset exists in BigQuery console
2. Grant service account access to the dataset
3. Check project ID and dataset name in query

### Query runs but returns no results

**Cause:** Query syntax might be specific to BigQuery

**Solution:**
- Use backticks for table references: `` `project.dataset.table` ``
- Use BigQuery SQL syntax (Standard SQL)
- Test query in BigQuery console first

## Best Practices

### 1. Use Fully Qualified Table Names

```sql
-- Good
FROM `my-project.my_dataset.my_table`

-- Also good (if default dataset specified in connection URL)
FROM `my_table`

-- Avoid (may be ambiguous)
FROM my_table
```

### 2. Limit Query Scope

```sql
-- Add WHERE clauses to reduce data scanned
WHERE date >= CURRENT_DATE() - 7  -- Last 7 days only

-- Use LIMIT for testing
LIMIT 1000
```

### 3. Use Partitioning and Clustering

```sql
-- Query partitioned tables efficiently
WHERE partition_date = CURRENT_DATE()

-- Use clustered columns in WHERE/GROUP BY
WHERE clustered_column = 'value'
```

### 4. Store Credentials Securely

```bash
# Good - restricted permissions
chmod 600 /path/to/service-account.json

# Bad - world-readable
chmod 644 /path/to/service-account.json
```

### 5. Monitor Query Costs

See [BigQuery Cost Management Guide](bigquery-cost-management.md) for details on monitoring and optimizing query costs.

## Example Deployments

### Docker Deployment

```bash
docker run -d \
  -v $(pwd)/alerts.yaml:/config/alerts.yaml \
  -v $(pwd)/sa-key.json:/keys/sa-key.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/keys/sa-key.json \
  sqlsentinel/sqlsentinel:latest \
  daemon /config/alerts.yaml
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bigquery-credentials
type: Opaque
data:
  key.json: <base64-encoded-service-account-key>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sql-sentinel
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: sql-sentinel
        image: sqlsentinel/sqlsentinel:latest
        env:
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /secrets/key.json
        volumeMounts:
        - name: credentials
          mountPath: /secrets
          readOnly: true
        - name: config
          mountPath: /config
      volumes:
      - name: credentials
        secret:
          secretName: bigquery-credentials
      - name: config
        configMap:
          name: sql-sentinel-config
```

### Cloud Run Deployment

```bash
gcloud run deploy sql-sentinel \
  --image sqlsentinel/sqlsentinel:latest \
  --service-account sql-sentinel@my-project.iam.gserviceaccount.com \
  --set-env-vars "CONFIG_FILE=gs://my-bucket/alerts.yaml"
```

## Next Steps

- [BigQuery Cost Management](bigquery-cost-management.md) - Optimize query costs
- [Example Alerts](../../examples/bigquery-alerts.yaml) - Ready-to-use alert templates
- [Authentication Guide](bigquery-authentication.md) - Detailed auth configuration

## Resources

- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [BigQuery SQL Reference](https://cloud.google.com/bigquery/docs/reference/standard-sql)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [IAM Roles for BigQuery](https://cloud.google.com/bigquery/docs/access-control)
