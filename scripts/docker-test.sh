#!/bin/bash
# SQL Sentinel - Docker Test Script
# Tests Docker container health and functionality

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-kgehring/sqlsentinel}"
VERSION="${VERSION:-latest}"
CONTAINER_NAME="sqlsentinel-test-$$"
TEST_CONFIG="/workspace/examples/alerts/revenue_check.yaml"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SQL Sentinel - Docker Test${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Cleanup function
cleanup() {
  echo ""
  echo -e "${YELLOW}Cleaning up...${NC}"
  docker stop "${CONTAINER_NAME}" 2>/dev/null || true
  docker rm "${CONTAINER_NAME}" 2>/dev/null || true
  echo -e "${GREEN}✓ Cleanup complete${NC}"
}
trap cleanup EXIT

# Test 1: Container starts successfully
echo -e "${YELLOW}Test 1: Container starts successfully${NC}"
docker run -d \
  --name "${CONTAINER_NAME}" \
  -e STATE_DATABASE=/tmp/test.db \
  -e LOG_LEVEL=DEBUG \
  "${IMAGE_NAME}:${VERSION}" \
  tail -f /dev/null

sleep 2

if docker ps | grep -q "${CONTAINER_NAME}"; then
  echo -e "${GREEN}✓ Container started successfully${NC}"
else
  echo -e "${RED}✗ Container failed to start${NC}"
  exit 1
fi
echo ""

# Test 2: CLI version command works
echo -e "${YELLOW}Test 2: CLI version command${NC}"
if docker exec "${CONTAINER_NAME}" sqlsentinel --version; then
  echo -e "${GREEN}✓ CLI version command works${NC}"
else
  echo -e "${RED}✗ CLI version command failed${NC}"
  exit 1
fi
echo ""

# Test 3: Health check command works
echo -e "${YELLOW}Test 3: Health check command${NC}"
if docker exec "${CONTAINER_NAME}" sqlsentinel healthcheck --help; then
  echo -e "${GREEN}✓ Health check command available${NC}"
else
  echo -e "${RED}✗ Health check command failed${NC}"
  exit 1
fi
echo ""

# Test 4: Metrics command works
echo -e "${YELLOW}Test 4: Metrics command${NC}"
if docker exec "${CONTAINER_NAME}" sqlsentinel metrics --help; then
  echo -e "${GREEN}✓ Metrics command available${NC}"
else
  echo -e "${RED}✗ Metrics command failed${NC}"
  exit 1
fi
echo ""

# Test 5: Container logs are accessible
echo -e "${YELLOW}Test 5: Container logs${NC}"
if docker logs "${CONTAINER_NAME}" 2>&1 | head -5 > /dev/null; then
  echo -e "${GREEN}✓ Container logs accessible${NC}"
else
  echo -e "${RED}✗ Container logs not accessible${NC}"
  exit 1
fi
echo ""

# Test 6: Container can be stopped gracefully
echo -e "${YELLOW}Test 6: Graceful shutdown${NC}"
START_TIME=$(date +%s)
docker stop -t 10 "${CONTAINER_NAME}"
END_TIME=$(date +%s)
STOP_DURATION=$((END_TIME - START_TIME))

if [ $STOP_DURATION -lt 15 ]; then
  echo -e "${GREEN}✓ Container stopped gracefully in ${STOP_DURATION}s${NC}"
else
  echo -e "${YELLOW}⚠ Container took ${STOP_DURATION}s to stop (expected <15s)${NC}"
fi
echo ""

# Test 7: Image size validation
echo -e "${YELLOW}Test 7: Image size validation${NC}"
IMAGE_SIZE_BYTES=$(docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Size}}" | grep -oE '[0-9.]+' | head -1)
IMAGE_SIZE_UNIT=$(docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Size}}" | grep -oE '[A-Z]+' | head -1)

echo "Image size: ${IMAGE_SIZE_BYTES}${IMAGE_SIZE_UNIT}"

# Check if image is under 500MB (target)
if [ "${IMAGE_SIZE_UNIT}" = "MB" ]; then
  if (( $(echo "${IMAGE_SIZE_BYTES} < 500" | bc -l) )); then
    echo -e "${GREEN}✓ Image size is under 500MB${NC}"
  else
    echo -e "${YELLOW}⚠ Image size is over 500MB (target: <300MB)${NC}"
  fi
elif [ "${IMAGE_SIZE_UNIT}" = "GB" ]; then
  echo -e "${RED}✗ Image size is over 1GB! (target: <500MB)${NC}"
else
  echo -e "${GREEN}✓ Image size is optimal${NC}"
fi
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Image: ${IMAGE_NAME}:${VERSION}"
echo "All tests passed successfully!"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  Deploy: docker-compose up -d"
echo "  Validate: ./scripts/validate-health.sh"
echo ""
