#!/bin/bash
# Test script for /health endpoint
# This script verifies that:
# 1. /health endpoint returns 200 OK
# 2. /health endpoint returns "OK" in response body
# 3. / (root) endpoint still works

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

FRONTEND_URL="${FRONTEND_URL:-http://localhost:80}"

echo "Testing nginx health endpoint configuration..."
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Test 1: /health endpoint returns 200
echo -n "Test 1: /health returns 200... "
if curl -f -s "$FRONTEND_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    exit 1
fi

# Test 2: /health returns "OK"
echo -n "Test 2: /health returns 'OK'... "
HEALTH_RESPONSE=$(curl -s "$FRONTEND_URL/health")
if [ "$HEALTH_RESPONSE" = "OK" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} (got: '$HEALTH_RESPONSE')"
    exit 1
fi

# Test 3: / still works
echo -n "Test 3: / returns 200... "
if curl -f -s "$FRONTEND_URL/" > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "To verify logging behavior:"
echo "  1. Check nginx logs: docker logs <container-name> 2>&1 | tail -20"
echo "  2. Call /health: curl $FRONTEND_URL/health"
echo "  3. Call /: curl $FRONTEND_URL/"
echo "  4. Verify only / appears in logs, not /health"
