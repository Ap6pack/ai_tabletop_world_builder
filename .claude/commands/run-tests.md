Run the full test suite for the AI Tabletop World Builder project.

## Instructions

0. **Activate the shared virtual environment** before running any Python commands:
   ```
   source /home/localhost/Projects/shared_venv/bin/activate
   ```

1. **Run all tests** using pytest from the project root:
   ```
   python -m pytest test_*.py -v --tb=short
   ```

2. **If coverage is available** (pytest-cov installed), run with coverage:
   ```
   python -m pytest test_*.py -v --tb=short --cov=api --cov-report=term-missing
   ```

3. **Report results** including:
   - Total tests: passed / failed / skipped / errors
   - Coverage percentage (if available)
   - Any failed tests with their error messages
   - Test execution time

4. **If tests fail**, analyze the failures and suggest fixes. Check:
   - Is the API server needed? (Some tests may require `python main.py` running)
   - Are there import errors? (Missing dependencies)
   - Are there async test issues? (pytest-asyncio configuration)

5. **Test files in this project** (all in project root):
   - `test_action_filter.py` — Pre-action content filtering
   - `test_audit_log.py` — Audit logging system
   - `test_audit_api.py` — Audit API endpoints
   - `test_content_validator.py` — Post-generation validation
   - `test_business_impact.py` — Business impact calculations
   - `test_time_pressure.py` — Time pressure mechanics
   - `test_resource_manager.py` — Resource constraint system
   - `test_phase_5b_integration.py` — End-to-end integration
   - `test_violation_handler.py` — Policy violation handling
