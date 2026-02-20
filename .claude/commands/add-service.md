Scaffold a new service for the AI Tabletop World Builder following the existing code patterns.

## Instructions

0. **Activate the shared virtual environment** before running any Python commands:
   ```
   source /home/localhost/Projects/shared_venv/bin/activate
   ```

The user will provide a service name and description. Create the following files following the project's existing patterns:

1. **Model** (`api/models/{service_name}.py`):
   - Follow the pattern from existing models (e.g., `api/models/scenario.py`)
   - Use Pydantic BaseModel for request/response schemas
   - Include proper type annotations

2. **Service** (`api/services/{service_name}_service.py`):
   - Follow the pattern from existing services (e.g., `api/services/business_impact_service.py`)
   - Include a class-based service with clear methods
   - Include proper error handling
   - Include logging

3. **Router** (`api/routers/{service_name}.py`):
   - Follow the pattern from existing routers (e.g., `api/routers/game.py`)
   - Use FastAPI APIRouter with proper prefix and tags
   - Include proper request/response models
   - Include error handling with HTTPException

4. **Test** (`test_{service_name}.py` in project root):
   - Follow the pattern from existing tests (e.g., `test_business_impact.py`)
   - Use pytest with proper fixtures
   - Include both happy path and error case tests
   - Aim for good coverage of the service methods

5. **Wire it up**:
   - Add the router to `api/main.py` (or `main.py`) with `app.include_router()`
   - Verify imports work

6. **Add copyright headers** to all new files.

7. **Report** what was created and any manual steps needed (e.g., adding to `requirements.txt` if new deps are needed).

## Existing patterns to follow

- Services are in `api/services/` as `{name}_service.py` with a class
- Routers are in `api/routers/` with `APIRouter(prefix="/api/{name}", tags=["{Name}"])`
- Models are in `api/models/` as Pydantic BaseModel classes
- Tests are in the project root as `test_{name}.py`
