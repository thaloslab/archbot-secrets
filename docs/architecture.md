# Architecture Overview

## Components

- CLI entrypoint: command parsing and output rendering
- Shared service layer: manifest/provider operations reused by CLI and API
- Manifest service: load and validate routing metadata
- Vault service: read/write secrets from OS key vault
- Policy engine: choose provider by priority and health
- Runner: launch child process with ephemeral env vars
- Local API server: localhost endpoints for providers/secrets/manifest
- Dashboard UI: browser-based management surface served by local API

## Runtime Sequence

1. User invokes `agent-vault run --provider X -- <command>`
2. CLI asks shared service to validate manifest and resolve provider
3. Vault layer fetches secret for provider
4. Runner injects env var into child process env map
5. Child process starts
6. Parent process exits with child code, no persistent export

## Dashboard Sequence

1. User invokes `agent-vault dashboard`
2. Local API binds to loopback (`127.0.0.1` by default)
3. CLI prints auth token for mutating API requests
4. Dashboard fetches provider and manifest data from localhost API
5. Secret writes/deletes require `X-Agent-Vault-Token`

## Trust Boundaries

- Secret values never written to manifest
- Secret values only cross process boundary to child runtime
- Logs must avoid printing secret material
- Local API is intended for loopback-only access
- Mutating API endpoints require an explicit auth token header

## Failure Handling

- Missing manifest: fail with actionable init message
- Missing provider: fail with list of known providers
- Missing key in vault: fail with prompt to run `set-key`
- Child process failure: forward exit code
