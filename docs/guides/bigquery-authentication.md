# BigQuery Authentication Guide

This guide covers all authentication methods for connecting SQL Sentinel to Google BigQuery.

## Authentication Methods Overview

| Method | Use Case | Pros | Cons |
|--------|----------|------|------|
| **Service Account Key** | Production, CI/CD | Explicit, portable, easy to manage | Key file management required |
| **Application Default Credentials (ADC)** | Local dev, GCP environments | No key file needed, seamless in GCP | Requires gcloud CLI for local use |
| **Workload Identity** | GKE (Kubernetes) | No keys, automatic rotation | GKE-specific |

## Method 1: Service Account Key (Recommended for Most Cases)

### When to Use

- Production deployments
- CI/CD pipelines
- Docker containers
- Non-GCP environments
- When you need explicit credential control

### Setup Steps

#### Step 1: Create Service Account

```bash
# Set your project ID
PROJECT_ID="your-project-id"

# Create service account
gcloud iam service-accounts create sql-sentinel \
  --project=$PROJECT_ID \
  --display-name="SQL Sentinel" \
  --description="Service account for SQL Sentinel alerting"
```

#### Step 2: Grant Permissions

```bash
# Get service account email
SA_EMAIL="sql-sentinel@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant BigQuery Job User role (required)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.jobUser"

# Grant BigQuery Data Viewer role (required)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataViewer"
```

#### Step 3: Create and Download Key

```bash
# Create key and download
gcloud iam service-accounts keys create ~/sql-sentinel-key.json \
  --iam-account=$SA_EMAIL

# Secure the key file
chmod 600 ~/sql-sentinel-key.json
```

#### Step 4: Configure SQL Sentinel

**Option A: Environment Variable**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/sql-sentinel-key.json
```

**Option B: In Connection String**
```yaml
database:
  url: "bigquery://your-project?credentials=/path/to/sql-sentinel-key.json"
```

**Option C: Docker**
```bash
docker run -d \
  -v /path/to/sql-sentinel-key.json:/keys/sa-key.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/keys/sa-key.json \
  sqlsentinel/sqlsentinel:latest
```

### Security Best Practices

```bash
# ✅ Good - restrictive permissions
chmod 600 /path/to/service-account-key.json

# ❌ Bad - too permissive
chmod 644 /path/to/service-account-key.json

# ✅ Store keys in secrets management
# - Kubernetes Secrets
# - AWS Secrets Manager
# - HashiCorp Vault
# - Google Secret Manager

# ❌ Never commit keys to git
# Add to .gitignore:
echo "*.json" >> .gitignore
echo "!package.json" >> .gitignore  # Except package.json
```

### Key Rotation

```bash
# Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=$SA_EMAIL

# Update configuration to use new key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/new-key.json

# Test new key works
sqlsentinel run test-config.yaml --alert test_alert

# Delete old key (after confirming new one works)
gcloud iam service-accounts keys delete OLD_KEY_ID \
  --iam-account=$SA_EMAIL
```

## Method 2: Application Default Credentials (ADC)

### When to Use

- Local development
- Running in Google Cloud (GCE, Cloud Run, GKE, Cloud Functions)
- Google Cloud Shell
- Quick testing

### Setup for Local Development

```bash
# Install gcloud CLI (if not already installed)
# https://cloud.google.com/sdk/docs/install

# Login and set up ADC
gcloud auth application-default login

# Set project (optional)
gcloud config set project your-project-id
```

### Configure SQL Sentinel

**No credentials parameter needed:**
```yaml
database:
  url: "bigquery://your-project-id"
```

**Run SQL Sentinel:**
```bash
# ADC automatically used
sqlsentinel daemon alerts.yaml
```

### How ADC Works

ADC searches for credentials in this order:

1. `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. User credentials from `gcloud auth application-default login`
3. GCE/Cloud Run/GKE metadata server (when running in GCP)
4. Cloud SDK configuration

### ADC in GCP Services

When running in Google Cloud, ADC automatically uses the service account attached to the resource:

**Google Compute Engine (GCE):**
```bash
# VM uses its default service account automatically
# No configuration needed!
```

**Cloud Run:**
```bash
gcloud run deploy sql-sentinel \
  --image sqlsentinel/sqlsentinel:latest \
  --service-account sql-sentinel@your-project.iam.gserviceaccount.com
  # Service account credentials automatically available via ADC
```

**Google Kubernetes Engine (GKE):**
```yaml
# Deployment uses Workload Identity (see Method 3)
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: sql-sentinel-ksa
  # Automatically gets credentials via Workload Identity
```

## Method 3: Workload Identity (GKE Only)

### When to Use

- Running in Google Kubernetes Engine (GKE)
- Want to avoid service account keys
- Need automatic credential rotation

### Setup Steps

#### Step 1: Enable Workload Identity on GKE Cluster

```bash
# Create cluster with Workload Identity
gcloud container clusters create sql-sentinel-cluster \
  --workload-pool=$PROJECT_ID.svc.id.goog \
  --region=us-central1

# Or enable on existing cluster
gcloud container clusters update CLUSTER_NAME \
  --workload-pool=$PROJECT_ID.svc.id.goog
```

#### Step 2: Create Kubernetes Service Account

```yaml
# k8s-service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sql-sentinel-ksa
  namespace: default
```

```bash
kubectl apply -f k8s-service-account.yaml
```

#### Step 3: Create GCP Service Account (if not exists)

```bash
gcloud iam service-accounts create sql-sentinel \
  --project=$PROJECT_ID
```

#### Step 4: Allow K8s SA to Impersonate GCP SA

```bash
gcloud iam service-accounts add-iam-policy-binding \
  sql-sentinel@$PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[default/sql-sentinel-ksa]"
```

#### Step 5: Annotate K8s Service Account

```bash
kubectl annotate serviceaccount sql-sentinel-ksa \
  iam.gke.io/gcp-service-account=sql-sentinel@$PROJECT_ID.iam.gserviceaccount.com
```

#### Step 6: Deploy SQL Sentinel

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sql-sentinel
spec:
  template:
    spec:
      serviceAccountName: sql-sentinel-ksa  # Use K8s SA with Workload Identity
      containers:
      - name: sql-sentinel
        image: sqlsentinel/sqlsentinel:latest
        # No GOOGLE_APPLICATION_CREDENTIALS needed!
        # Workload Identity provides credentials automatically
```

## Comparison Matrix

| Feature | Service Account Key | ADC (Local) | ADC (GCP) | Workload Identity |
|---------|-------------------|-------------|-----------|------------------|
| **Setup Complexity** | Medium | Easy | Automatic | Complex |
| **Key Management** | Required | Not needed | Not needed | Not needed |
| **Key Rotation** | Manual | Automatic | Automatic | Automatic |
| **Works Outside GCP** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Works in Docker** | ✅ Yes | ⚠️ With gcloud | ❌ No | ❌ No |
| **Works in GKE** | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Works in CI/CD** | ✅ Yes | ⚠️ Complex | ✅ Yes (GCP CI) | ❌ No |
| **Security** | 🟡 Medium | 🟢 Good | 🟢 Good | 🟢 Excellent |

## Troubleshooting

### Error: "Could not automatically determine credentials"

**Cause:** ADC not configured

**Solution:**
```bash
# For local development
gcloud auth application-default login

# OR use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### Error: "Service account key file not found"

**Cause:** Path to key file is incorrect

**Solution:**
```bash
# Check file exists
ls -la /path/to/key.json

# Use absolute path
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/key.json

# Verify
echo $GOOGLE_APPLICATION_CREDENTIALS
```

### Error: "Permission denied: bigquery.jobs.create"

**Cause:** Service account lacks BigQuery Job User role

**Solution:**
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.jobUser"
```

### Error: "Invalid JWT: Token must be a short-lived token"

**Cause:** Using user credentials instead of service account

**Solution:**
```bash
# Create service account and use that instead
# OR refresh ADC
gcloud auth application-default login
```

### Debugging Authentication

```python
# Test script to debug authentication
from google.cloud import bigquery
from google.auth import default

# Check what credentials are being used
credentials, project = default()
print(f"Credentials type: {type(credentials)}")
print(f"Project: {project}")

# Try to create client
try:
    client = bigquery.Client(project=project, credentials=credentials)
    print(f"✅ Successfully authenticated!")

    # Test query
    query = "SELECT 1 as test"
    result = client.query(query).result()
    print(f"✅ Query successful!")
except Exception as e:
    print(f"❌ Error: {e}")
```

## Environment-Specific Examples

### Development (macOS/Linux)

```bash
# One-time setup
gcloud auth application-default login

# Use SQL Sentinel
cd ~/projects/my-alerts
sqlsentinel daemon bigquery-alerts.yaml
```

### Docker (Production)

```dockerfile
FROM sqlsentinel/sqlsentinel:latest

# Copy service account key
COPY service-account-key.json /secrets/key.json

# Set environment variable
ENV GOOGLE_APPLICATION_CREDENTIALS=/secrets/key.json

# Copy alert configuration
COPY alerts.yaml /config/alerts.yaml

# Run daemon
CMD ["sqlsentinel", "daemon", "/config/alerts.yaml"]
```

```bash
# Build and run
docker build -t my-sql-sentinel .
docker run -d my-sql-sentinel
```

### Kubernetes (Production)

```yaml
# secret.yaml - Create from key file
apiVersion: v1
kind: Secret
metadata:
  name: bigquery-key
type: Opaque
data:
  key.json: <base64-encoded-service-account-key>
---
# deployment.yaml
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
        - name: bigquery-key
          mountPath: /secrets
          readOnly: true
      volumes:
      - name: bigquery-key
        secret:
          secretName: bigquery-key
```

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/sql-sentinel.yml
name: Run BigQuery Alerts
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  run-alerts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}

      - name: Install SQL Sentinel
        run: |
          pip install sqlsentinel

      - name: Run Alerts
        env:
          GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_SA_KEY }}
        run: |
          sqlsentinel run alerts.yaml
```

## Best Practices

### ✅ DO:

- Use service accounts for production
- Rotate keys regularly (every 90 days)
- Use separate service accounts for different environments
- Grant minimum required permissions (least privilege)
- Store keys in secrets management systems
- Use Workload Identity in GKE when possible
- Monitor service account usage

### ❌ DON'T:

- Commit keys to version control
- Share keys between environments
- Use personal credentials in production
- Grant overly broad permissions (e.g., Project Owner)
- Leave old keys active after rotation
- Store keys in plain text in documentation
- Use the same key across multiple applications

## Next Steps

- [BigQuery Setup Guide](bigquery-setup.md) - Complete setup walkthrough
- [BigQuery Cost Management](bigquery-cost-management.md) - Optimize query costs
- [Example Alerts](../../examples/bigquery-alerts.yaml) - Ready-to-use templates

## Resources

- [Google Cloud Authentication Documentation](https://cloud.google.com/docs/authentication)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
