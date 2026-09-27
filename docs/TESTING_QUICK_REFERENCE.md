# Quick Testing Reference

## Start the API
```bash
python main.py
```
API runs at: http://127.0.0.1:8000  
Docs at: http://127.0.0.1:8000/docs

---

## Minimal Working Test

```bash
# Just the prompt (uses your .env defaults)
curl -X POST http://127.0.0.1:8000/llm/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is a SIEM in one sentence?"}'
```

---

## Full Test Suite

```bash
./test_api.sh
```

---

## Valid Model Names

**OpenAI**: `gpt-5.6-terra`, `gpt-6-astra`  
**Anthropic**: `claude-sonnet-5`, `claude-opus-5`  
**Ollama**: `llama3`, `mistral`, `mixtral`

---

## Common Mistakes

❌ **WRONG**: `"model": "string"`  
✅ **RIGHT**: `"model": "gpt-3.5-turbo"` or omit it

❌ **WRONG**: `"provider": "together"`  
✅ **RIGHT**: `"provider": "openai"` or `"anthropic"` or `"ollama"`

---

## Quick Checks

```bash
# Is API running?
curl http://127.0.0.1:8000/health

# Which providers are configured?
curl http://127.0.0.1:8000/llm/providers

# What policies exist?
curl http://127.0.0.1:8000/content-policy/policies
```

---

## Need More Help?

- Setup and running tests: [README.md](../README.md)
- Deployment: [DEPLOY.md](../DEPLOY.md)
