#!/bin/bash
# Test script for scenario generation

echo "=========================================="
echo "Testing Scenario Generation"
echo "=========================================="
echo ""

API_URL="http://127.0.0.1:8000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: List supported industries
echo -e "${YELLOW}Test 1: List Supported Industries${NC}"
curl -s "$API_URL/scenarios/industries" | jq .
echo ""

# Test 2: Get industry info
echo -e "${YELLOW}Test 2: Get Industry Info (Financial Services)${NC}"
curl -s "$API_URL/scenarios/industries/Financial%20Services" | jq .
echo ""

# Test 3: Generate a basic scenario
echo -e "${YELLOW}Test 3: Generate Basic Scenario (This may take 30-60 seconds...)${NC}"
echo "Generating Financial Services scenario..."
curl -s -X POST "$API_URL/scenarios/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "Financial Services",
    "size": "medium",
    "complexity": "basic",
    "num_departments": 2
  }' | jq '{
    id: .id,
    name: .name,
    industry: .industry,
    size: .size,
    security_posture: .security_posture,
    num_departments: (.departments | length),
    num_threat_actors: (.threat_actors | length),
    departments: [.departments[] | {
      name: .name,
      num_systems: (.systems | length)
    }]
  }'
echo ""

# Test 4: List saved scenarios
echo -e "${YELLOW}Test 4: List Saved Scenarios${NC}"
curl -s "$API_URL/scenarios/list" | jq .
echo ""

echo -e "${GREEN}=========================================="
echo "Testing Complete!"
echo "==========================================${NC}"
echo ""
echo "To see the full generated scenario, check: scenarios/generated/"
echo "Or use: curl http://127.0.0.1:8000/scenarios/list | jq ."
