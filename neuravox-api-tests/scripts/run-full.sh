#!/bin/bash

# Run full workflow test
# Usage: ./run-full.sh [dev|staging|prod]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

echo -e "${YELLOW}Running Neuravox API full workflow test in ${ENV} environment...${NC}\n"

# Create test data directory if it doesn't exist
mkdir -p test-data

# Check for test audio file
if [ ! -f "test-data/sample.wav" ]; then
    echo -e "${RED}Error: test-data/sample.wav not found!${NC}"
    echo -e "${RED}Full workflow requires a sample audio file for testing.${NC}"
    echo -e "${YELLOW}Please add a WAV audio file at: test-data/sample.wav${NC}"
    exit 1
fi

# Display test info
echo -e "${BLUE}Test Configuration:${NC}"
echo -e "  Environment: ${ENV}"
echo -e "  API URL: $(grep base_url $ENV_FILE | cut -d'=' -f2)"
echo -e "  Test file: test-data/sample.wav"
echo -e ""

# Run full workflow test
echo -e "${YELLOW}Executing full workflow test...${NC}"
echo -e "${YELLOW}This will test: Auth → Upload → Job Creation → Status Check${NC}\n"

# Add timestamp variable for unique names
export timestamp=$(date +%s)

if OUTPUT=$(hurl --variables-file "$COMMON_FILE" \
                --variables-file "$ENV_FILE" \
                --variable "timestamp=$timestamp" \
                --test \
                --color \
                --verbose \
                --retry 3 \
                --retry-interval 1000 \
                hurl/workflows/full-workflow.hurl 2>&1); then
    echo "$OUTPUT"
    # Extract test statistics
    REQUESTS=$(echo "$OUTPUT" | grep "Executed requests:" | grep -o '[0-9]\+' | head -1)
    DURATION=$(echo "$OUTPUT" | grep "Duration:" | grep -o '[0-9]\+' | head -1)
    
    echo -e "\n${GREEN}✓ Full workflow test passed!${NC}"
    echo -e "${GREEN}Results: ${REQUESTS:-7} requests executed successfully${NC}"
    echo -e "${GREEN}Duration: ${DURATION:-0} ms${NC}"
    echo -e "${GREEN}All API operations completed successfully.${NC}"
    exit 0
else
    echo "$OUTPUT"
    
    # Extract test statistics from failed output
    REQUESTS=$(echo "$OUTPUT" | grep "Executed requests:" | grep -o '[0-9]\+' | head -1)
    FAILED=$(echo "$OUTPUT" | grep "Failed files:" | grep -o '[0-9]\+' | head -1)
    
    echo -e "\n${RED}✗ Full workflow test failed!${NC}"
    echo -e "${RED}Results: ${REQUESTS:-0} requests executed, ${FAILED:-1} test(s) failed${NC}"
    echo -e "${RED}Check the logs above for details.${NC}"
    exit 1
fi