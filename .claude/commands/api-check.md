Check the health and status of all API endpoints in the AI Tabletop World Builder.

## Instructions

0. **Activate the shared virtual environment** before running any Python commands:
   ```
   source /home/localhost/Projects/shared_venv/bin/activate
   ```

1. **Check if the API is running** by hitting the health endpoint:
   - `GET http://localhost:8000/health`
   - If not running, ask the user if they want to start it

2. **Test core endpoints** (GET requests only — safe, read-only):
   - `GET /health` — Health check
   - `GET /api/scenarios` — List scenarios
   - `GET /api/scenarios/industries` — List supported industries
   - `GET /api/settings` — Get current settings
   - `GET /api/game/sessions` — List game sessions
   - `GET /api/audit/logs` — Get audit logs
   - `GET /api/audit/compliance-report` — Get compliance report

3. **Report status for each endpoint**:
   - Status code (200, 404, 500, etc.)
   - Response time
   - Response size
   - Any errors

4. **Produce a summary table**:
   ```
   Endpoint                          Status  Time    Notes
   GET /health                       200     12ms    OK
   GET /api/scenarios                200     45ms    3 scenarios found
   GET /api/scenarios/industries     200     8ms     8 industries
   ...
   ```

5. **Flag any issues**: Slow responses (>1s), error responses, missing endpoints.

6. **Do NOT** make any POST/PUT/DELETE requests — this is a read-only health check.
