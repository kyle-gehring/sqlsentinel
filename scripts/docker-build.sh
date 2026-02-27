#!/bin/bash
# SQL Sentinel - Docker Build Script
# Builds and tags Docker images for SQL Sentinel

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-kgehring/sqlsentinel}"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SQL Sentinel - Docker Build${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image Name: ${IMAGE_NAME}"
echo "Version: ${VERSION}"
echo "Build Date: ${BUILD_DATE}"
echo "Git Commit: ${GIT_COMMIT}"
echo ""

# Measure start time
START_TIME=$(date +%s)

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VERSION="${VERSION}" \
  --build-arg GIT_COMMIT="${GIT_COMMIT}" \
  -t "${IMAGE_NAME}:${VERSION}" \
  -t "${IMAGE_NAME}:${GIT_COMMIT}" \
  -f Dockerfile \
  .

# Measure end time
END_TIME=$(date +%s)
BUILD_DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}✓ Build completed successfully!${NC}"
echo ""

# Display image information
echo -e "${YELLOW}Image Information:${NC}"
IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Size}}")
echo "  Size: ${IMAGE_SIZE}"
echo "  Duration: ${BUILD_DURATION}s"
echo ""

# Display image layers
echo -e "${YELLOW}Image Layers:${NC}"
docker history "${IMAGE_NAME}:${VERSION}" --human --no-trunc | head -10
echo ""

# Display tags
echo -e "${YELLOW}Tagged Images:${NC}"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""

# Optional: Run quick validation
if [ "${QUICK_TEST}" = "true" ]; then
  echo -e "${YELLOW}Running quick validation test...${NC}"
  docker run --rm "${IMAGE_NAME}:${VERSION}" sqlsentinel --version
  echo -e "${GREEN}✓ Quick test passed${NC}"
  echo ""
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Image: ${IMAGE_NAME}:${VERSION}"
echo "Size: ${IMAGE_SIZE}"
echo "Build Time: ${BUILD_DURATION}s"
echo "Commit: ${GIT_COMMIT}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  Test: ./scripts/docker-test.sh"
echo "  Push: docker push ${IMAGE_NAME}:${VERSION}"
echo ""
