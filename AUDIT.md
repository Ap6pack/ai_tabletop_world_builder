# Project Audit — Cybersecurity War Gaming Platform

**Date:** 2026-07-17
**Scope:** Full repository — backend, frontend, tests, CI/CD, docs, infra
**Method:** Read every area of the tree, installed dependencies, ran the test suite in a clean environment, checked real CI history on GitHub, and traced runtime behavior.

---

## TL;DR

This is a genuinely ambitious and, in places, well-crafted codebase: ~31k lines, real LLM integration, Argon2id + JWT, Pydantic v2, hierarchical scenario generation, MITRE ATT&CK data, and a broad Streamlit UI. The *concept* — AI-generated cybersecurity tabletop exercises — is valuable and marketable.

But there is a **large and important gap between the project's self-description and its actual state.** The docs and commit messages declare "Phase 10 Production Readiness Complete / v1.0.0 / 240 tests passing." The reality:

- **CI has never once passed.** The only two CI runs on `main` both failed at the `ruff` lint step; the `test` and `build` jobs were *skipped and never executed*.
- **The API cannot even be imported without an OpenAI key.** `from main import app` raises `ValueError` in a clean checkout.
- **In a clean environment the test suite is 6 failed, 28 errors, 206 passed** — not "240 passed, 0 failed."
- **Authentication is effectively decorative** — off by default, and no product endpoint actually enforces it.
- **1,368 ruff lint errors** and **115 of 120 files** fail the formatter the CI claims to enforce.

None of this means the project is bad — it means it is **an impressive prototype mislabeled as a production release.** The path forward is to close that gap honestly, then narrow scope to a verified core.

---

## What's genuinely good

Credit where due — this is well above typical "AI slop":

- **Real LLM abstraction.** `api/providers/` has a clean `BaseLLMProvider` ABC with OpenAI, Anthropic, and Ollama implementations and a factory. The game master and generators genuinely call the LLM and parse structured JSON back out — this is not stubbed.
- **Sound security primitives where they exist.** `auth_service.py` uses Argon2id, excludes `hashed_password` from all return paths, validates input, and uses timezone-aware JWTs. The crypto choices are correct.
- **Coherent domain model.** The Organization → Department → System → Vulnerability/ThreatActor hierarchy is well modeled in Pydantic, and the industry templates (`organization_generator.py`) are detailed and realistic.
- **Real data assets.** MITRE ATT&CK (93 techniques / 14 tactics), compliance frameworks (NIST CSF, PCI DSS, HIPAA), and inject templates are actual structured JSON, loaded and used.
- **Tests exist and many are meaningful.** 206 tests do pass, with shared fixtures in `conftest.py`. The testing instinct is right.
- **Infra scaffolding is present.** Dockerfile (multi-stage, non-root user), docker-compose, monitoring configs, SBOM generation, and separate CI/security workflows show good intent.

---

## Critical findings (must fix before any "production" claim)

### 1. CI has never passed — the green-status claims are false
Both CI runs in history (`run #1`, `run #2` on `main`) concluded **`failure`**. They failed at step 5, `ruff check .`, in the `lint` job. Because `test` and `build` declare `needs: lint`, **they were skipped** — the test suite and Docker build have *never* run in CI. Meanwhile commit `efef128` and `ffcfcb0` messages, plus README/PROJECT_SUMMARY, assert "240 passed, 1 skipped, 0 failed." The passing number comes from a local run *with an API key present*, not from CI.

**Impact:** The single most load-bearing trust signal in the repo (a passing "Production Readiness" release) is contradicted by the actual automation.

### 2. The app cannot boot without an OpenAI API key
`api/routers/exercise.py:22` instantiates `orchestrator = ExerciseOrchestrator()` **at module import time.** That chains `ExerciseOrchestrator → GameOrchestrator → GameMasterService → LLMProviderFactory.create_provider()`, which raises `ValueError("OpenAI API key is required")` when no key is set. Because `main.py` imports the routers, **`from main import app` fails** — the `/health` endpoint, the OpenAPI schema, everything. This is why 6 boot tests fail and 28 orchestrator tests error in a clean environment.

**Root cause (architectural):** stateful services are constructed eagerly at import via module-level singletons instead of being injected as FastAPI dependencies. This also means all requests share one mutable orchestrator instance.

### 3. Clean-environment test reality: 6 failed, 28 errors, 206 passed
The 28 errors are all the same cause as #2 (orchestrators built without a mock provider). The tests only "pass" because the author's machine had `OPENAI_API_KEY` set and real network/LLM available — i.e. the suite is **not hermetic** and silently depends on external state.

### 4. Authentication is decorative
- `require_auth` defaults to `False` (`config/settings.py:57`).
- `get_current_user` returns `None` when auth is disabled (`api/middleware/auth.py:33`).
- **The auth dependency is referenced only inside `auth.py` itself** — zero occurrences across the `game`, `scenario`, `exercise`, `settings`, `audit`, `analytics`, `library`, or `integrations` routers. So even if you set `require_auth=True`, none of the product endpoints are protected. Every scenario, session, exercise, and the "clear all data" endpoint is open.
- `jwt_secret_key` defaults to the literal `"change-me-in-production"`, and neither `.env.example` nor the README mentions `JWT_SECRET_KEY` or `REQUIRE_AUTH`, so an operator has no signal to change it.

### 5. Lint/format never actually applied
`ruff check .` reports **1,368 errors** (1,151 auto-fixable); `ruff format --check .` would reformat **115 of 120 files.** The "Phase 8.6 Security hardening and project config" that added ruff config was never run against the code. This is the direct cause of #1.

---

## High / medium findings

### 6. `together` provider is a broken config path
`config/settings.py` and `.env.example` document a `together` provider (with model/temperature), but `api/providers/factory.py` only implements `openai`, `anthropic`, `ollama`. Setting `DEFAULT_LLM_PROVIDER=together` raises `Unknown provider type` at runtime. Either implement it or remove it from settings/docs/`.env.example`.

### 7. "Content moderation / safety" is advisory, not enforced
Despite the four-tier policy framing and the project's lineage (the `context/` course transcripts include "Moderation & Safety with Llama Guard"), the actual enforcement is **category lists + prompt instructions + regex pattern matching** (`content_policy_service.py`, `action_filter_service.py`). There is no moderation *model* in the loop — nothing classifies LLM output before it reaches the user. For a product whose selling point includes "unrestricted" tiers and offensive-security content, this is a real safety and liability gap, not just a technical one.

### 8. File-based persistence won't support the stated SaaS ambition
Users, sessions, exercises, and scenarios are stored as loose JSON files. `auth_service.get_user_by_username` and the email-uniqueness check **scan and parse every file on every call** (O(n) per lookup, full re-read to register). There's no locking, no transactions, no concurrency safety — concurrent writes can corrupt or lose data. This is fine for a single-user demo and fatal for the "SaaS subscriptions / MSSP / multi-tenant" business model in `PROJECT_SUMMARY.md`. `redis` is a dependency and `fakeredis` is used in tests, but the default path is files.

### 9. Committed data that shouldn't be in git
`data/test_users/*.json` (three user records with Argon2 hashes) and dated `data/audit_logs/*.jsonl` are committed. These are runtime artifacts; they belong in `.gitignore`, not history.

### 10. Documentation inflation / drift
The metrics ("241 tests", "81 routes", "37 services", "Production Readiness Complete") are repeated verbatim across README, PROJECT_SUMMARY, CHANGELOG, and commit messages, presented as verified facts. Some are inflated (test pass count) and the "production ready" framing is not supported by CI, boot behavior, or auth state. The 25 markdown docs (11 "PHASE*_COMPLETE" files) read as a narrative of momentum rather than accurate current-state documentation.

### 11. Scope-to-maturity mismatch
37 services / 81 routes / 12 UI pages is a very large surface for a solo, pre-revenue, unverified product. Breadth was prioritized over depth: many services likely have the thin-but-plausible quality typical of rapid phase-by-phase generation. The core loop (generate scenario → play war game → review) is the actual product; much of the rest (executive dashboards, adaptive difficulty, training paths, webhooks, API keys) is surface area that isn't yet earning its keep and multiplies the maintenance/correctness burden.

---

## Recommendations

### Immediate (make the truth match the docs) — days, not weeks
1. **Make the app boot without a key.** Convert module-level service singletons to lazy construction or FastAPI dependency injection (construct the LLM provider on first use, not at import). This alone fixes boot + 28 test errors.
2. **Make tests hermetic.** Add a fixture that injects a fake/mock LLM provider everywhere a service is built; never hit the network in unit tests. Then the suite passes with *no* API key — which is what CI runs.
3. **Run the formatter and linter.** `ruff format .` then `ruff check --fix .`, review the residual, and get CI's `lint` job actually green so `test`/`build` finally run.
4. **Correct the documentation.** Replace "240 passed / production ready / v1.0.0" with the real, CI-verified numbers and an honest status (e.g. "v0.x — working prototype"). This is the highest-trust, lowest-effort fix.
5. **`.gitignore` runtime data** and purge `data/test_users`, `data/audit_logs` from the tree.

### Near-term (make it real) — weeks
6. **Decide on auth and actually wire it.** If auth matters, put `Depends(require_auth)` on the product routers, fail startup if `jwt_secret_key` is default while `require_auth=True`, and document the env vars. If it doesn't matter yet, remove the auth surface so it isn't a false security signal.
7. **Fix or delete the `together` provider.**
8. **Replace file persistence with SQLite** (via SQLAlchemy) as the single storage layer. It removes the O(n) scans and concurrency risks with minimal ops burden and gives a real migration path to Postgres later.
9. **Add a real moderation step** if the offensive tiers stay — route LLM output through an actual classifier (Llama Guard via Ollama, or a provider moderation endpoint) rather than regex, and be explicit in docs about what is and isn't enforced.

### Strategic (scope discipline)
10. **Shrink to a verified core, then re-expand.** Pick the one loop that delivers the value — *generate a realistic org + incident, play it against an AI game master, get an AAR* — and make that flawless, tested, and demoable end-to-end. Treat the executive dashboard, adaptive difficulty, training paths, multi-team exercises, webhooks, and API keys as a backlog to earn back one at a time behind real usage, not as shipped features.

---

## Vision: should you move forward, and how?

**Yes — but reframe what this is.** Today it's described as a finished v1.0 product. It's actually a **strong, feature-rich prototype with a broken foundation and inflated status.** Those are very different things to steward, and pretending it's the former is the main thing holding it back.

The concept is legitimately good. AI-generated, industry-specific tabletop exercises with MITRE mapping and AARs is a real need for SOC training, MSSPs, and security education, and you've already built more of it than most people ever would. The differentiator isn't the 37 services — it's a *believable, replayable incident that teaches something*, which lives almost entirely in the LLM prompts and the core game loop you've already got working.

Three honest paths:

- **A — Portfolio / learning showcase (lowest effort, high payoff).** Do the "Immediate" list, tell the truth in the docs, and this becomes an excellent demonstration of full-stack + AI + security engineering. Right now the inflated claims *undercut* it with anyone who looks closely (like this audit did); honesty would make it stronger, not weaker.
- **B — Real product (highest effort).** Viable, but only after the core is verified, storage is a real database, auth/moderation are genuine, and scope is cut to the loop that sells. That's a multi-month effort and probably needs a second person or a narrower wedge (e.g. "AI-generated ransomware tabletop for MSSPs" rather than an everything-platform).
- **C — Pivot the core into a smaller, sharper tool.** Extract just the scenario-generation + AAR engine as a focused offering and drop the rest. Fastest route to something genuinely finished.

**Recommendation:** Do **A first regardless** — it's a few days and it converts the project from "impressive but overstated" to "trustworthy." *Then* decide between B and C based on whether you want a product or a portfolio piece. Don't build more surface area until the existing core boots cleanly, tests hermetically, and CI is honestly green. The next commit should make something *true*, not add another phase.

---

*Full evidence (CI run IDs, exact test output, file:line references) is in the audit conversation. Nothing in this document was inferred without being verified against the running code or GitHub's API.*
