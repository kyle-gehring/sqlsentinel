#!/bin/bash
# SQL Sentinel - Health Validation Script
# Validates health of a running SQL Sentinel deployment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="${CONTAINER_NAME:-sqlsentinel}"
CONFIG_PATH="${CONFIG_PATH:-/app/config/alerts.yaml}"
TIMEOUT="${TIMEOUT:-10}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SQL Sentinel - Health Validation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if container exists
echo -e "${YELLOW}Checking container status...${NC}"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo -e "${RED}✗ Container '${CONTAINER_NAME}' is not running${NC}"
  echo ""
  echo "Available containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
  exit 1
fi
echo -e "${GREEN}✓ Container is running${NC}"
echo ""

# Get container info
CONTAINER_STATUS=$(docker inspect "${CONTAINER_NAME}" --format='{{.State.Status}}')
CONTAINER_HEALTH=$(docker inspect "${CONTAINER_NAME}" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
CONTAINER_UPTIME=$(docker inspect "${CONTAINER_NAME}" --format='{{.State.StartedAt}}')

echo -e "${YELLOW}Container Information:${NC}"
echo "  Name: ${CONTAINER_NAME}"
echo "  Status: ${CONTAINER_STATUS}"
echo "  Health: ${CONTAINER_HEALTH}"
echo "  Started: ${CONTAINER_UPTIME}"
echo ""

# Run health check command
echo -e "${YELLOW}Running health check...${NC}"
if docker exec "${CONTAINER_NAME}" sqlsentinel healthcheck "${CONFIG_PATH}" --output text; then
  echo -e "${GREEN}✓ Health check passed${NC}"
  HEALTH_STATUS="healthy"
else
  echo -e "${RED}✗ Health check failed${NC}"
  HEALTH_STATUS="unhealthy"
fi
echo ""

# Check logs for errors
echo -e "${YELLOW}Checking recent logs for errors...${NC}"
ERROR_COUNT=$(docker logs "${CONTAINER_NAME}" --tail 100 2>&1 | grep -i "error" | wc -l || echo 0)

if [ "${ERROR_COUNT}" -eq 0 ]; then
  echo -e "${GREEN}✓ No errors in recent logs${NC}"
else
  echo -e "${YELLOW}⚠ Found ${ERROR_COUNT} error(s) in recent logs${NC}"
  echo ""
  echo "Recent errors (last 5):"
  docker logs "${CONTAINER_NAME}" --tail 100 2>&1 | grep -i "error" | tail -5
fi
echo ""

# Get metrics if available
echo -e "${YELLOW}Checking metrics...${NC}"
if docker exec "${CONTAINER_NAME}" sqlsentinel metrics --output text 2>/dev/null; then
  echo -e "${GREEN}✓ Metrics available${NC}"
else
  echo -e "${YELLOW}⚠ Metrics command not available or no data${NC}"
fi
echo ""

# Check disk usage
echo -e "${YELLOW}Checking disk usage...${NC}"
DISK_INFO=$(docker exec "${CONTAINER_NAME}" df -h / 2>/dev/null | tail -1 | awk '{print $5}')
echo "  Root filesystem: ${DISK_INFO} used"

if [[ "${DISK_INFO}" =~ ([0-9]+)% ]]; then
  DISK_PERCENT="${BASH_REMATCH[1]}"
  if [ "${DISK_PERCENT}" -lt 80 ]; then
    echo -e "${GREEN}✓ Disk usage is healthy${NC}"
  elif [ "${DISK_PERCENT}" -lt 90 ]; then
    echo -e "${YELLOW}⚠ Disk usage is high (${DISK_PERCENT}%)${NC}"
  else
    echo -e "${RED}✗ Disk usage is critical (${DISK_PERCENT}%)${NC}"
  fi
fi
echo ""

# Check memory usage
echo -e "${YELLOW}Checking memory usage...${NC}"
MEMORY_INFO=$(docker stats "${CONTAINER_NAME}" --no-stream --format "{{.MemUsage}}" 2>/dev/null || echo "N/A")
echo "  Memory: ${MEMORY_INFO}"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "${HEALTH_STATUS}" = "healthy" ] && [ "${ERROR_COUNT}" -eq 0 ]; then
  echo -e "${GREEN}✓ All checks passed - system is healthy${NC}"
  EXIT_CODE=0
elif [ "${HEALTH_STATUS}" = "healthy" ] && [ "${ERROR_COUNT}" -gt 0 ]; then
  echo -e "${YELLOW}⚠ System is running but has errors in logs${NC}"
  EXIT_CODE=1
else
  echo -e "${RED}✗ System is unhealthy${NC}"
  EXIT_CODE=2
fi

echo ""
echo -e "${BLUE}Troubleshooting commands:${NC}"
echo "  View logs: docker logs ${CONTAINER_NAME} -f"
echo "  Exec shell: docker exec -it ${CONTAINER_NAME} /bin/bash"
echo "  Restart: docker restart ${CONTAINER_NAME}"
echo ""

exit ${EXIT_CODE}
