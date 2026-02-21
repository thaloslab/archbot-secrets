# MVP Technology Stack

## Objectives

- Cross-platform native secret storage
- Minimal dependencies
- Fast CLI developer UX
- Strong defaults for validation and testability

## Stack Decisions

| Layer | Choice | Why this choice | Alternative considered |
|---|---|---|---|
| Runtime | Python 3.12 | Portable, mature keyring ecosystem, quick iteration | Go |
| CLI | Typer | Type-hint based command definitions, excellent ergonomics | Click |
| Console UX | Rich | Clear error/status rendering | Plain stdout |
| Local API | FastAPI | Typed local endpoints with low boilerplate | Flask |
| Local server | Uvicorn | Lightweight ASGI server for localhost dashboard | Hypercorn |
| Secrets backend | keyring | Native integration with macOS/Windows/Linux stores | Direct `security`/`secret-tool` wrappers |
| Validation | Pydantic v2 | Strict schema validation and clear errors | attrs/dataclasses |
| Testing | pytest | Standard ecosystem + fixtures + monkeypatch support | unittest |
| Linting | Ruff | Fast all-in-one lint and formatting checks | flake8 + isort |
| Type-checking | mypy | Static checks for API boundaries | pyright |
| Packaging & envs | Poetry | Dependency/groups management and centrally managed virtualenvs | PEP 621 + pip |
| CI | GitHub Actions | Simple pipeline for lint/type/test | Local-only scripts |

## Dependency Policy

MVP keeps dependencies intentionally small:

- Runtime deps: `typer`, `rich`, `keyring`, `pydantic`, `fastapi`, `uvicorn`
- Dev deps: `pytest`, `pytest-cov`, `ruff`, `mypy`

Avoid adding:

- ORM/database
- background daemon frameworks
- telemetry SDKs

## OS Compatibility Expectations

- macOS: Keychain via `keyring`
- Windows: Credential Manager via `keyring`
- Linux: Secret Service/libsecret via `keyring`

## Production Hardening Path

1. Add encrypted local cache for short-lived session tokens
2. Add provider-specific rotation adapters
3. Add optional centralized backend adapter
4. Add signed release process and binary packaging
