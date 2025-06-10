#!/bin/bash

# Run all Hurl tests with proper error handling
# Usage: ./run-tests.sh [dev|staging|prod]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default environment
ENV="${1:-dev}"
ENV_FILE="environments/${ENV}.env"
COMMON_FILE="environments/common.env"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file $ENV_FILE not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Running Neuravox API tests in ${ENV} environment...${NC}\n"

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .hurl)
    
    echo -e "${YELLOW}Running: ${test_name}${NC}"
    
    if hurl --variables-file "$COMMON_FILE" --variables-file "$ENV_FILE" \
           --test --color "$test_file"; then
        echo -e "${GREEN}✓ ${test_name} passed${NC}\n"
        return 0
    else
        echo -e "${RED}✗ ${test_name} failed${NC}\n"
        return 1
    fi
}

# Track test results
total_tests=0
passed_tests=0
failed_tests=0

# Run all individual request tests
echo -e "${YELLOW}=== Running Individual Request Tests ===${NC}\n"

for category in auth system files jobs processing; do
    echo -e "${YELLOW}Testing ${category} requests:${NC}"
    
    for test_file in hurl/requests/${category}/*.hurl; do
        if [ -f "$test_file" ]; then
            ((total_tests++))
            if run_test "$test_file"; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi
        fi
    done
    echo
done

# Run workflow tests
echo -e "${YELLOW}=== Running Workflow Tests ===${NC}\n"

for workflow in hurl/workflows/*.hurl; do
    if [ -f "$workflow" ]; then
        ((total_tests++))
        if run_test "$workflow"; then
            ((passed_tests++))
        else
            ((failed_tests++))
        fi
    fi
done

# Summary
echo -e "${YELLOW}=== Test Summary ===${NC}"
echo -e "Total tests: ${total_tests}"
echo -e "${GREEN}Passed: ${passed_tests}${NC}"
echo -e "${RED}Failed: ${failed_tests}${NC}"

# Exit with appropriate code
if [ $failed_tests -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi