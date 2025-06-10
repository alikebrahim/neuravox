#!/bin/bash

# Run smoke tests for quick health check
# Usage: ./run-smoke.sh [dev|staging|prod]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default environment
ENV="${1:-dev}"
ENV_FILE="environments/${ENV}.env"
COMMON_FILE="environments/common.env"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file $ENV_FILE not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Running Neuravox API smoke tests in ${ENV} environment...${NC}\n"

# Create test data directory if it doesn't exist
mkdir -p test-data

# Check for test audio file
if [ ! -f "test-data/sample.wav" ]; then
    echo -e "${YELLOW}Warning: test-data/sample.wav not found. Some tests may fail.${NC}"
    echo -e "${YELLOW}Please add a sample audio file for testing.${NC}\n"
fi

# Run smoke test workflow
echo -e "${YELLOW}Executing smoke test workflow...${NC}\n"

# Add timestamp variable for unique names
export timestamp=$(date +%s)

# Run the test and capture output
if OUTPUT=$(hurl --variables-file "$COMMON_FILE" \
                --variables-file "$ENV_FILE" \
                --variable "timestamp=$timestamp" \
                --test \
                --color \
                --verbose \
                hurl/workflows/smoke-test.hurl 2>&1); then
    echo "$OUTPUT"
    
    # Extract test statistics
    REQUESTS=$(echo "$OUTPUT" | grep "Executed requests:" | grep -o '[0-9]\+' | head -1)
    DURATION=$(echo "$OUTPUT" | grep "Duration:" | grep -o '[0-9]\+' | head -1)
    
    echo -e "\n${GREEN}✓ Smoke tests passed!${NC}"
    echo -e "${GREEN}Results: ${REQUESTS:-4} requests executed successfully${NC}"
    echo -e "${GREEN}Duration: ${DURATION:-0} ms${NC}"
    echo -e "${GREEN}API is healthy and responding correctly.${NC}"
    exit 0
else
    echo "$OUTPUT"
    
    # Extract test statistics from failed output
    REQUESTS=$(echo "$OUTPUT" | grep "Executed requests:" | grep -o '[0-9]\+' | head -1)
    FAILED=$(echo "$OUTPUT" | grep "Failed files:" | grep -o '[0-9]\+' | head -1)
    
    echo -e "\n${RED}✗ Smoke tests failed!${NC}"
    echo -e "${RED}Results: ${REQUESTS:-0} requests executed, ${FAILED:-1} test(s) failed${NC}"
    echo -e "${RED}Please check the API status and configuration.${NC}"
    exit 1
fi