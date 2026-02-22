# Secret Lifecycle

This document describes how a secret moves through Agent Vault from initial setup to runtime use and deletion.

## Goals

- Keep raw secret values out of project files and manifests.
- Store secret values only in the OS key vault via `keyring`.
- Inject secrets into child processes only when needed at runtime.
- Expose safe status/health metadata to CLI and dashboard without returning raw secret values.

## Core Entities

- Manifest: `~/.config/ai/ai_agents/manifest.json`
- Service namespace in keyring: `agent_vault`
- Provider metadata fields:
  - `vault_key`: pointer used to read/write secret in keyring
  - `env_var`: target variable injected into child process
  - `type`, `endpoint`, `priority`: routing and health metadata

## Lifecycle Stages

### 1) Bootstrap

Command:

```bash
poetry run agent-vault init
```

What happens:

1. Creates `~/.config/ai/ai_agents/manifest.json` if missing.
2. Writes provider metadata only (no raw secrets).
3. Default manifest includes providers such as `openai_pro`, `openrouter`, and `local_ollama`.

### 2) Secret Write or Rotation

Command:

```bash
poetry run agent-vault set-key openai_pro
```

or API:

```http
POST /providers/{provider}/secret
```

What happens:

1. Service resolves provider from manifest.
2. Service validates secret is non-empty.
3. Service requires provider to have a `vault_key`.
4. Secret is written to keyring with:
   - `service = "agent_vault"`
   - `key = <provider.vault_key>`
5. API returns status only (`{"status":"stored"}`), not the secret.

### 3) Status and Health Checks

Commands/endpoints:

- `poetry run agent-vault doctor`
- `GET /providers`
- `POST /providers/{provider}/test`

What happens:

1. Agent Vault checks whether a secret exists for each provider pointer (`has_secret`).
2. For providers with endpoints, it checks network reachability (`endpoint_reachable`).
3. Results expose booleans/failures only, never raw secret values.

### 4) Runtime Consumption (Ephemeral Injection)

Command:

```bash
poetry run agent-vault run --provider openai_pro -- "<your command>"
```

What happens:

1. Provider is resolved via policy (`--provider` override or priority ordering).
2. Secret is fetched from keyring at runtime using `vault_key`.
3. Runner creates a child-process environment map and injects `env_var=<secret>`.
4. Child process starts with injected env.
5. Parent shell environment is not permanently modified.

### 5) Dashboard/API Use

Command:

```bash
poetry run agent-vault dashboard
```

What happens:

1. API binds to loopback host only.
2. CLI prints a write token for mutating API calls.
3. Dashboard reads provider/manifest data from API.
4. Secret write/delete and manifest update endpoints require `X-Agent-Vault-Token`.
5. Dashboard can show secret presence (`present`/`missing`) but cannot read the secret value.

### 6) Deletion and Revocation

Command/endpoint:

- `DELETE /providers/{provider}/secret`

What happens:

1. Service validates provider and `vault_key`.
2. Secret entry is deleted from keyring if it exists.
3. Response returns only deletion status (`{"deleted": true|false}`).

### 7) Pointer Changes and Migration Behavior

When `vault_key` changes in manifest:

1. Agent Vault treats the new pointer as a different secret location.
2. Existing secret under old pointer is not auto-migrated.
3. You must set/rotate secret again for the new `vault_key`.
4. Optional cleanup: explicitly delete the old keyring entry if no longer used.

## State Model

| State | Manifest pointer (`vault_key`) | Keyring entry | Runtime injection |
|---|---|---|---|
| Not configurable for secret | missing | n/a | no |
| Configured, missing secret | present | absent | fails when required |
| Configured, secret present | present | present | yes (if `env_var` set) |
| Rotated | present | present (new value) | yes (new value) |
| Deleted/revoked | present | absent | fails when required |

## Failure Modes

- Missing provider: service returns `Provider not found`.
- Missing `vault_key`: secret set/delete operations fail for that provider.
- Missing keyring entry on read: runtime fails with vault error.
- Keyring backend error: surfaced as `VaultError` (API maps to `500`).
- Invalid manifest JSON/schema: surfaced as `ManifestError` (API maps to `400`).

## Security Properties

- Raw secret values are never stored in manifest files.
- API/dashboard do not expose read-secret endpoints.
- Mutating API endpoints are token-protected.
- Runtime injection is scoped to child process execution.
- Intended deployment is local loopback only, not internet-exposed.
