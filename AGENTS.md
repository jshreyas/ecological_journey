# Agent Guidelines

## Project

Ecological Journey is a self-hosted martial-arts training journal for organizing training videos, playlists, clips, technique notes, and partner activity. The UI is built with NiceGUI and Python 3.10+.

## Architecture and Key Locations

- `ui/main.py` is the application entry point. It configures NiceGUI, authentication routes, the embedded FastAPI `/api` routes, and the top-level page shell.
- `ui/pages/` contains page-level UI; reusable feature components and their state live under `ui/pages/components/`.
- `ui/data/models.py` defines persisted Bunnet/Pydantic documents. `ui/data/crud.py` owns persistence and data operations; `ui/data/auth.py` handles token-based authentication.
- `ui/utils/` contains shared UI/application helpers, including API access, user context, caching, video playback, and YouTube integration.
- `static/` contains frontend assets. `ui/scripts/` contains operational scripts.
- MongoDB is the persistence layer and Redis is used for caching. Check existing data helpers before adding another access path.
- `docs/architecture.md` and the README provide broader context, but verify implementation details in the current code: some older documentation and scripts refer to a separate top-level `api/` directory, which is not present in this checkout.

## Working in the Codebase

- Follow nearby NiceGUI page/component patterns and preserve existing navigation, authentication, and refresh behavior.
- Keep persistence and domain operations in `ui/data/`; keep reusable presentation/state logic in the relevant `ui/pages/components/` area.
- Use the existing `User` context and auth helpers for user-scoped actions. Protect write operations consistently with the existing authorization checks.
- Reuse existing cache helpers and invalidate affected keys when changing cached data.
- Update or add focused tests in `tests/` for behavior changes. UI tests commonly mock NiceGUI elements and external/data dependencies rather than requiring live services.
- Do not add secrets or assume external services are available. Use environment configuration and the existing local Docker Compose setup where needed.

## Validation and Style

- Run the focused tests for the changed behavior; the full test suite can be run with `python -m pytest -q tests/`.
- Start the local services with `docker-compose up --build` as described in the README when integration with MongoDB or Redis is needed.
- Run configured repository checks with `pre-commit run --all-files`. Individual checks can be run using the tools in `requirements-dev.txt`.
- Python formatting and lint configuration is in `pyproject.toml`, `.pre-commit-config.yaml`, and `.flake8`. Follow Black/isort and the configured 120-character line limit; do not rely on conflicting older line-length references in documentation.
- Review `docs/code-quality-setup.md` for the quality-tool overview. The legacy `scripts/lint.sh` references the absent `api/` directory, so use focused checks or pre-commit when that script fails for that reason.

## Documentation

Update the README or the relevant document under `docs/` when changing setup, architecture, or contributor workflows. Keep this file limited to guidance useful across tasks; link to detailed docs rather than duplicating them.
