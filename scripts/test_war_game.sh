#!/bin/bash
# Test script for interactive war gaming

echo "=========================================="
echo "Testing Interactive War Gaming"
echo "=========================================="
echo ""

API_URL="http://127.0.0.1:8000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# First, get list of available scenarios
echo -e "${YELLOW}Step 1: List Available Scenarios${NC}"
SCENARIOS=$(curl -s "$API_URL/scenarios/list")
echo "$SCENARIOS" | jq '.[0] | {filename, name, industry}'
echo ""

# Get the first scenario filename
SCENARIO_FILE=$(echo "$SCENARIOS" | jq -r '.[0].filename')
echo -e "${BLUE}Using scenario: $SCENARIO_FILE${NC}"
echo ""

# Start a new game
echo -e "${YELLOW}Step 2: Start War Game Session${NC}"
START_RESPONSE=$(curl -s -X POST "$API_URL/game/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"scenario_filename\": \"$SCENARIO_FILE\",
    \"scenario_type\": \"incident-response\",
    \"player_role\": \"soc-analyst\",
    \"difficulty\": \"intermediate\"
  }")

echo "$START_RESPONSE" | jq '{
  session_id: .game_state.session_id,
  organization: .game_state.organization.name,
  role: .game_state.player_role,
  score: .game_state.score,
  narrative: .narrative
}'
echo ""

# Extract session ID
SESSION_ID=$(echo "$START_RESPONSE" | jq -r '.game_state.session_id')
echo -e "${BLUE}Session ID: $SESSION_ID${NC}"
echo ""

# Player takes first action
echo -e "${YELLOW}Step 3: Player Action - Check SIEM Logs${NC}"
ACTION_RESPONSE=$(curl -s -X POST "$API_URL/game/action" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"action\": \"Check SIEM logs for the source of the alert and look for any related events in the past hour\"
  }")

echo "$ACTION_RESPONSE" | jq '{
  narrative: .narrative,
  score: .game_state.score,
  time_elapsed: .game_state.time_elapsed,
  num_events: (.game_state.incident_timeline | length)
}'
echo ""

# Player takes second action
echo -e "${YELLOW}Step 4: Player Action - Investigate Affected System${NC}"
ACTION_RESPONSE2=$(curl -s -X POST "$API_URL/game/action" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"action\": \"Identify the affected system and check its current status and running processes\"
  }")

echo "$ACTION_RESPONSE2" | jq '{
  narrative: .narrative,
  score: .game_state.score,
  time_elapsed: .game_state.time_elapsed
}'
echo ""

# Get a hint
echo -e "${YELLOW}Step 5: Request a Hint${NC}"
HINT_RESPONSE=$(curl -s -X POST "$API_URL/game/hint?session_id=$SESSION_ID")
echo "$HINT_RESPONSE" | jq '.hint'
echo ""

# Get full game state
echo -e "${YELLOW}Step 6: Check Game State${NC}"
STATE=$(curl -s "$API_URL/game/state/$SESSION_ID")
echo "$STATE" | jq '{
  session_id,
  status,
  score,
  time_elapsed,
  available_tools: (.inventory.tools | keys),
  access_levels: .inventory.access_levels,
  num_events: (.incident_timeline | length)
}'
echo ""

# List all sessions
echo -e "${YELLOW}Step 7: List All Sessions${NC}"
curl -s "$API_URL/game/sessions" | jq '.sessions[] | {session_id, organization, player_role, status, score}'
echo ""

echo -e "${GREEN}=========================================="
echo "War Gaming Test Complete!"
echo "==========================================${NC}"
echo ""
echo "Session ID: $SESSION_ID"
echo "To continue playing, use the session ID with /game/action endpoint"
echo "To end the session: curl -X POST $API_URL/game/end -H 'Content-Type: application/json' -d '{\"session_id\": \"$SESSION_ID\", \"status\": \"completed\"}'"
