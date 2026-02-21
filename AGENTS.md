# Project Context: Agent Vault MVP
You are working on `Agent Vault`, a local-first secrets manager for agentic AI tooling. 

## Tech Stack & Tooling
- **Language:** Python 3.12
- **CLI Framework:** Typer
- **Terminal UX:** Rich
- **Validation:** Pydantic v2
- **Secrets Backend:** `keyring`
- **Package Manager:** Poetry. **STRICT RULE:** `virtualenvs.in-project` is set to `false`. Do not ever create or attempt to use an in-project `.venv` folder.

## Development Workflow
Do not run raw `pytest` or `ruff` commands. Always use the Makefile:
- Run tests: `make test` (pytest + pytest-cov)
- Run linting: `make lint` (Ruff)
- Run type checking: `make typecheck` (mypy)

## Architectural & Security Directives
When writing or refactoring code for this project, you must adhere to these security constraints:
1. **Zero Plaintext:** Never write raw secret values to `manifest.json` or `.env` files. The manifest stores pointers; the OS keyring stores secrets.
2. **Ephemeral Injection:** In `runner.py`, secrets must only be injected into the child process environment. Ensure the parent shell remains completely clean.
3. **API Integrity:** In `api.py` (FastAPI), maintain deterministic error mapping: `ManifestError` and `ServiceError` map to HTTP 400; `VaultError` maps to HTTP 500. 
4. **Auth Gating:** Any mutating API endpoint (POST, PUT, DELETE) MUST be protected by validating the `X-Agent-Vault-Token` using constant-time comparison.
