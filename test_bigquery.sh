#!/bin/bash
# Quick script to run BigQuery integration tests

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}BigQuery Integration Test Runner${NC}"
echo "=================================="

# Check for project ID
if [ -z "$BIGQUERY_PROJECT_ID" ]; then
    echo -e "${RED}Error: BIGQUERY_PROJECT_ID environment variable not set${NC}"
    echo ""
    echo "Please set your GCP project ID:"
    echo "  export BIGQUERY_PROJECT_ID=your-project-id"
    echo ""
    echo "And configure authentication:"
    echo "  Option 1 (ADC): gcloud auth application-default login"
    echo "  Option 2 (Service Account): export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json"
    exit 1
fi

echo -e "${GREEN}✓ Project ID: $BIGQUERY_PROJECT_ID${NC}"

# Check for credentials
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${GREEN}✓ Using service account: $GOOGLE_APPLICATION_CREDENTIALS${NC}"
    if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo -e "${RED}Error: Credentials file not found at $GOOGLE_APPLICATION_CREDENTIALS${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Using Application Default Credentials (ADC)${NC}"
    echo "  If tests fail, run: gcloud auth application-default login"
fi

echo ""
echo "Running BigQuery integration tests..."
echo ""

# Run the tests
poetry run pytest tests/integration/test_bigquery_integration.py -v --no-cov "$@"

exit $?
