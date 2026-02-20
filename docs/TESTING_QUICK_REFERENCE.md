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

**OpenAI**: `gpt-4-turbo-preview`, `gpt-4`, `gpt-3.5-turbo`  
**Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`  
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

- Full examples: `test_examples.md`
- Bug fixes: `FIXES.md`
- Setup guide: `QUICKSTART.md`
