# API Testing Examples

## Prerequisites

1. **Start the API**:
   ```bash
   python main.py
   ```

2. **Ensure you have a `.env` file** with at least one LLM provider configured:
   ```bash
   # Example .env
   DEFAULT_LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_MODEL=gpt-3.5-turbo
   ```

---

## Test 1: Simple Health Check

```bash
curl http://127.0.0.1:8000/health
```

**Expected Response**:
```json
{"status": "healthy"}
```

---

## Test 2: Check Available Providers

```bash
curl http://127.0.0.1:8000/llm/providers
```

**Expected Response**:
```json
{
  "openai": true,
  "anthropic": false,
  "ollama": false
}
```

---

## Test 3: LLM Completion (Minimal - Uses Defaults)

This test uses whatever is configured in your `.env` file.

```bash
curl -X POST http://127.0.0.1:8000/llm/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain what a SIEM is in one sentence."
  }'
```

**Expected Response**:
```json
{
  "content": "A SIEM (Security Information and Event Management) is a system that collects, analyzes, and correlates security data from multiple sources to detect threats and security incidents.",
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 35,
    "total_tokens": 50
  }
}
```

---

## Test 4: LLM Completion (Specify Provider & Model)

```bash
curl -X POST http://127.0.0.1:8000/llm/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the three main types of security controls?",
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

**Expected Response**:
```json
{
  "content": "The three main types of security controls are:\n1. Administrative controls - policies and procedures\n2. Technical controls - firewalls, encryption, access controls\n3. Physical controls - locks, guards, cameras",
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 45,
    "total_tokens": 65
  }
}
```

---

## Test 5: LLM Completion with System Message

```bash
curl -X POST http://127.0.0.1:8000/llm/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is incident response?",
    "system_message": "You are a cybersecurity expert training SOC analysts. Be concise and practical.",
    "max_tokens": 200
  }'
```

---

## Test 6: List Content Policies

```bash
curl http://127.0.0.1:8000/content-policy/policies
```

**Expected Response**:
```json
{
  "defensive": {
    "description": "Defensive security only - no offensive techniques, exploit code, or attack methods",
    "allowed_categories": [
      "Security monitoring and detection",
      "Incident response procedures",
      ...
    ],
    "blocked_categories": [
      "Exploit code or payloads",
      ...
    ]
  },
  "educational": { ... },
  "advanced": { ... },
  "unrestricted": { ... }
}
```

---

## Test 7: Check Content Safety (Safe Content)

```bash
curl -X POST http://127.0.0.1:8000/content-policy/check \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Configure your firewall to block unauthorized access on port 22.",
    "policy": {
      "level": "defensive",
      "description": "Defensive only",
      "allowed_categories": ["Security controls"],
      "blocked_categories": ["Exploit code"]
    }
  }'
```

**Expected Response**:
```json
{
  "is_safe": true,
  "policy_level": "defensive",
  "violations": [],
  "message": "Content is appropriate for defensive security training..."
}
```

---

## Test 8: Check Content Safety (Unsafe Content)

```bash
curl -X POST http://127.0.0.1:8000/content-policy/check \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Here is the exploit code to gain unauthorized root access...",
    "policy": {
      "level": "defensive",
      "description": "Defensive only",
      "allowed_categories": ["Security monitoring"],
      "blocked_categories": ["Exploit code", "Attack methods"]
    }
  }'
```

**Expected Response**:
```json
{
  "is_safe": false,
  "policy_level": "defensive",
  "violations": ["Exploit code", "Unauthorized access methods"],
  "message": "Content contains exploit code which is blocked by the defensive policy..."
}
```

---

## Common Issues and Solutions

### Issue 1: "OpenAI API key is required"

**Solution**: Make sure your `.env` file has the API key:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

### Issue 2: "The model `string` does not exist"

**Problem**: You're sending `"model": "string"` (the literal word "string")

**Solution**: Either:
- Omit the `model` field to use the default
- Specify a real model: `"model": "gpt-3.5-turbo"`

**Correct Examples**:
```json
// Option 1: Use defaults
{
  "prompt": "Test prompt"
}

// Option 2: Specify real model
{
  "prompt": "Test prompt",
  "model": "gpt-3.5-turbo"
}
```

### Issue 3: 500 Internal Server Error

**Check**:
1. Is the API running? (`python main.py`)
2. Is your API key valid?
3. Check API logs for detailed error
4. Test with minimal request first (just `prompt`)

---

## Using the Test Script

Run all tests at once:
```bash
./test_api.sh
```

This will test:
1. Health endpoint
2. Provider availability
3. Content policies
4. LLM completion (various configurations)
5. Content safety checks

---

## Testing with Python

```python
import requests

# Test LLM completion
response = requests.post(
    "http://127.0.0.1:8000/llm/complete",
    json={
        "prompt": "What is a firewall?",
        "max_tokens": 100
    }
)

print(response.json())
```

---

## OpenAPI/Swagger UI

For interactive testing, visit:
```
http://127.0.0.1:8000/docs
```

**IMPORTANT**: When using the Swagger UI:
- Don't use the example values (they're placeholders)
- Either leave optional fields empty or provide real values
- The "Try it out" button lets you modify the request

---

## Valid Model Names

### OpenAI
- `gpt-4-turbo-preview`
- `gpt-4`
- `gpt-3.5-turbo`

### Anthropic
- `claude-3-5-sonnet-20241022`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`

### Ollama (requires local Ollama)
- `llama3`
- `llama2`
- `mistral`
- `mixtral`

---

Last Updated: 2025-10-31
