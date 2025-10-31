#!/bin/bash
# API Testing Script for Cybersecurity War Gaming Platform

echo "=========================================="
echo "Testing Cybersecurity War Gaming Platform API"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://127.0.0.1:8000"

# Test 1: Health check
echo -e "${YELLOW}Test 1: Health Check${NC}"
curl -s "$API_URL/health" | jq .
echo ""

# Test 2: Check available providers
echo -e "${YELLOW}Test 2: Check Available Providers${NC}"
curl -s "$API_URL/llm/providers" | jq .
echo ""

# Test 3: List content policies
echo -e "${YELLOW}Test 3: List Content Policies${NC}"
curl -s "$API_URL/content-policy/policies" | jq .
echo ""

# Test 4: LLM completion with defaults (using configured provider from .env)
echo -e "${YELLOW}Test 4: LLM Completion (using defaults from .env)${NC}"
curl -s -X POST "$API_URL/llm/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain what a SIEM is in one sentence."
  }' | jq .
echo ""

# Test 5: LLM completion with specific provider and model
echo -e "${YELLOW}Test 5: LLM Completion (OpenAI with GPT-3.5)${NC}"
curl -s -X POST "$API_URL/llm/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is incident response?",
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 100,
    "system_message": "You are a cybersecurity expert. Be concise."
  }' | jq .
echo ""

# Test 6: Content policy check - Safe content
echo -e "${YELLOW}Test 6: Content Policy Check (Safe Content)${NC}"
curl -s -X POST "$API_URL/content-policy/check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Configure firewall rules to block unauthorized access",
    "policy": {
      "level": "educational",
      "description": "Educational content",
      "allowed_categories": ["Security monitoring", "Incident response"],
      "blocked_categories": ["Exploit code"]
    }
  }' | jq .
echo ""

# Test 7: Content policy check - Potentially unsafe content
echo -e "${YELLOW}Test 7: Content Policy Check (Potentially Unsafe)${NC}"
curl -s -X POST "$API_URL/content-policy/check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Here is a working exploit for CVE-2024-XXXX with full shellcode...",
    "policy": {
      "level": "defensive",
      "description": "Defensive only",
      "allowed_categories": ["Security monitoring"],
      "blocked_categories": ["Exploit code", "Attack methods"]
    }
  }' | jq .
echo ""

echo -e "${GREEN}=========================================="
echo "Testing Complete!"
echo "==========================================${NC}"
