## Summary

<!-- What does this change and why? Link the issue it closes (e.g. "Closes #123"). -->

## How was this tested?

<!-- Commands you ran and anything you checked by hand. -->

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `python -m pytest -q` passes (SQLite; PostgreSQL too if the change touches storage)
- [ ] Model changes include an Alembic migration, and `alembic check` reports no drift
- [ ] Dependency changes update both `requirements*.in` and the regenerated lock files
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]`
- [ ] Docs (README, DEPLOY.md, `.env.example`) are updated if behavior or configuration changed
