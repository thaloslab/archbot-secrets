# Local API Documentation

Agent Vault exposes a localhost API when you run:

```bash
poetry run agent-vault dashboard
```

Default base URL:

```text
http://127.0.0.1:8765
```

## Security Model

1. Server is intended for loopback usage only.
2. Read endpoints do not require a token.
3. Mutating endpoints require `X-Agent-Vault-Token`.
4. Secret values are write-only through API; values are not returned.

## Start and Export Variables

Start dashboard and copy the token printed by CLI:

```bash
poetry run agent-vault dashboard
```

Set environment variables for examples:

```bash
export AV_BASE="http://127.0.0.1:8765"
export AV_TOKEN="<token from dashboard startup>"
```

## Endpoint Summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | No | API health check |
| `GET` | `/providers` | No | Provider statuses and metadata |
| `POST` | `/providers/{provider}/secret` | Yes | Set/rotate provider secret |
| `DELETE` | `/providers/{provider}/secret` | Yes | Delete provider secret |
| `POST` | `/providers/{provider}/test` | No | Run provider checks |
| `GET` | `/manifest` | No | Read full manifest |
| `PUT` | `/manifest` | Yes | Validate and update manifest |
| `GET` | `/` | No | Built-in dashboard UI |

## Example Calls

### 1) Health

```bash
curl -s "$AV_BASE/health"
```

Example response:

```json
{"status":"ok"}
```

### 2) List Providers

```bash
curl -s "$AV_BASE/providers"
```

Example response:

```json
{
  "providers": [
    {
      "name": "openai_pro",
      "type": "upstream",
      "env_var": "OPENAI_API_KEY",
      "vault_key": "api.openai.com/pro_key",
      "endpoint": null,
      "priority": 1,
      "has_secret": true,
      "endpoint_reachable": null
    }
  ]
}
```

### 3) Set or Rotate Secret (Token Required)

```bash
curl -s -X POST "$AV_BASE/providers/openai_pro/secret" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Vault-Token: $AV_TOKEN" \
  -d '{"secret":"sk-REPLACE_ME"}'
```

Example response:

```json
{"status":"stored"}
```

### 4) Delete Secret (Token Required)

```bash
curl -s -X DELETE "$AV_BASE/providers/openai_pro/secret" \
  -H "X-Agent-Vault-Token: $AV_TOKEN"
```

Example response:

```json
{"deleted":true}
```

### 5) Test Provider

```bash
curl -s -X POST "$AV_BASE/providers/openai_pro/test"
```

Example response:

```json
{
  "provider": "openai_pro",
  "ok": true,
  "has_secret": true,
  "endpoint_reachable": null,
  "failures": []
}
```

### 6) Read Manifest

```bash
curl -s "$AV_BASE/manifest"
```

Example response:

```json
{
  "manifest": {
    "version": "2026.1",
    "identity": "primary-dev-node",
    "providers": {
      "openai_pro": {
        "vault_key": "api.openai.com/pro_key",
        "env_var": "OPENAI_API_KEY",
        "type": "upstream",
        "endpoint": null,
        "priority": 1
      }
    }
  }
}
```

### 7) Update Manifest (Token Required)

Create a payload file:

```bash
cat > manifest-update.json <<'JSON'
{
  "manifest": {
    "version": "2026.1",
    "identity": "primary-dev-node",
    "providers": {
      "openai_pro": {
        "vault_key": "api.openai.com/pro_key",
        "env_var": "OPENAI_API_KEY",
        "type": "upstream",
        "priority": 1
      },
      "openrouter": {
        "vault_key": "api.openrouter.ai/default",
        "env_var": "OPENROUTER_API_KEY",
        "type": "gateway",
        "endpoint": "https://openrouter.ai/api/v1",
        "priority": 2
      }
    }
  }
}
JSON
```

Send request:

```bash
curl -s -X PUT "$AV_BASE/manifest" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Vault-Token: $AV_TOKEN" \
  -d @manifest-update.json
```

Example response:

```json
{"status":"updated"}
```

## Common Error Responses

Unauthorized write call:

```json
{"detail":"Unauthorized"}
```

Validation or domain error (`400`):

```json
{"detail":"Provider not found: unknown_provider"}
```

Vault backend/runtime error (`500`):

```json
{"detail":"...vault backend error..."}
```

## OpenAPI and Interactive Docs

When dashboard is running, FastAPI also exposes generated docs:

1. Swagger UI: `http://127.0.0.1:8765/docs`
2. ReDoc: `http://127.0.0.1:8765/redoc`

