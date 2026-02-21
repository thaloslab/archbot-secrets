from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent_vault.manifest import ManifestError
from agent_vault.models import Manifest
from agent_vault.service import AgentVaultService, ProviderStatus, ProviderTestResult, ServiceError
from agent_vault.vault import VaultError

T = TypeVar("T")


class SecretWriteRequest(BaseModel):
    secret: str = Field(min_length=1)


class ManifestUpdateRequest(BaseModel):
    manifest: Manifest


class ProviderResponse(BaseModel):
    name: str
    type: str
    env_var: str | None
    vault_key: str | None
    endpoint: str | None
    priority: int | None
    has_secret: bool | None
    endpoint_reachable: bool | None


class ProviderTestResponse(BaseModel):
    provider: str
    ok: bool
    has_secret: bool | None
    endpoint_reachable: bool | None
    failures: list[str]


def create_app(service: AgentVaultService, auth_token: str) -> FastAPI:
    app = FastAPI(title="Agent Vault Local API", version="0.1.0")

    def require_write_token(request: Request) -> None:
        provided = request.headers.get("X-Agent-Vault-Token")
        if not provided or not secrets.compare_digest(provided, auth_token):
            raise HTTPException(status_code=401, detail="Unauthorized")

    def run_service_call(fn: Callable[[], T]) -> T:
        try:
            return fn()
        except ManifestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ServiceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except VaultError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return _dashboard_html(auth_token)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/providers")
    def list_providers() -> dict[str, list[ProviderResponse]]:
        statuses = run_service_call(service.list_provider_statuses)
        providers = [_provider_response(item) for item in statuses]
        return {"providers": providers}

    @app.post("/providers/{provider}/secret")
    def set_provider_secret(
        provider: str,
        payload: SecretWriteRequest,
        request: Request,
    ) -> dict[str, str]:
        require_write_token(request)
        run_service_call(lambda: service.set_provider_secret(provider, payload.secret))
        return {"status": "stored"}

    @app.delete("/providers/{provider}/secret")
    def delete_provider_secret(provider: str, request: Request) -> dict[str, bool]:
        require_write_token(request)
        deleted = run_service_call(lambda: service.delete_provider_secret(provider))
        return {"deleted": deleted}

    @app.post("/providers/{provider}/test")
    def test_provider(provider: str) -> ProviderTestResponse:
        result = run_service_call(lambda: service.test_provider(provider))
        return _test_response(result)

    @app.get("/manifest")
    def get_manifest() -> dict[str, Any]:
        manifest = run_service_call(service.load_manifest)
        return {"manifest": manifest.model_dump(mode="json")}

    @app.put("/manifest")
    def update_manifest(payload: ManifestUpdateRequest, request: Request) -> dict[str, str]:
        require_write_token(request)
        run_service_call(lambda: service.save_manifest(payload.manifest))
        return {"status": "updated"}

    return app


def _provider_response(status: ProviderStatus) -> ProviderResponse:
    return ProviderResponse(
        name=status.name,
        type=status.provider_type,
        env_var=status.env_var,
        vault_key=status.vault_key,
        endpoint=status.endpoint,
        priority=status.priority,
        has_secret=status.has_secret,
        endpoint_reachable=status.endpoint_reachable,
    )


def _test_response(result: ProviderTestResult) -> ProviderTestResponse:
    return ProviderTestResponse(
        provider=result.provider,
        ok=result.ok,
        has_secret=result.has_secret,
        endpoint_reachable=result.endpoint_reachable,
        failures=list(result.failures),
    )


def _dashboard_html(auth_token: str) -> str:
    token_json = json.dumps(auth_token)
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Agent Vault Dashboard</title>
    <style>
      :root {
        color-scheme: light;
        --bg-main: #f2f6fa;
        --bg-accent: #c7ecf2;
        --bg-secondary: #d6dff9;
        --surface: rgba(255, 255, 255, 0.86);
        --surface-strong: #ffffff;
        --line: #d4dde9;
        --line-strong: #bec9da;
        --text: #10243d;
        --text-muted: #4b6180;
        --accent: #1d6fd7;
        --accent-strong: #085fca;
        --ok: #227f4a;
        --warn: #b27700;
        --danger: #b0373c;
        --shadow: 0 16px 30px rgba(16, 36, 61, 0.08);
      }

      :root[data-theme="dark"] {
        color-scheme: dark;
        --bg-main: #3a4151;
        --bg-accent: #495165;
        --bg-secondary: #2f3644;
        --surface: rgba(50, 58, 73, 0.86);
        --surface-strong: #41495b;
        --line: #55607a;
        --line-strong: #67728d;
        --text: #edf2fb;
        --text-muted: #b2bdd2;
        --accent: #8fa9db;
        --accent-strong: #7d99cf;
        --ok: #a9d49e;
        --warn: #e4c07b;
        --danger: #ef9fa7;
        --shadow: 0 20px 40px rgba(13, 17, 24, 0.4);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
        color: var(--text);
        background:
          radial-gradient(1200px 540px at 5% -5%, var(--bg-accent), transparent 65%),
          radial-gradient(900px 420px at 100% 0%, var(--bg-secondary), transparent 58%),
          var(--bg-main);
      }

      .wrap {
        max-width: 1220px;
        margin: 0 auto;
        padding: 22px 16px 36px;
      }

      .hero {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--surface);
        backdrop-filter: blur(16px);
        box-shadow: var(--shadow);
      }

      .title {
        margin: 0;
        font-size: clamp(1.5rem, 2.5vw, 2.1rem);
        letter-spacing: 0.02em;
      }

      .subtitle {
        margin: 6px 0 0;
        color: var(--text-muted);
        font-size: 0.95rem;
      }

      .hero-actions {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .theme-state {
        font-size: 0.82rem;
        color: var(--text-muted);
      }

      .layout {
        display: grid;
        gap: 16px;
        grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr);
      }

      .panel {
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 16px;
        background: var(--surface);
        backdrop-filter: blur(16px);
        box-shadow: var(--shadow);
      }

      .panel-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
      }

      .panel-title {
        margin: 0;
        font-size: 1.1rem;
        letter-spacing: 0.02em;
      }

      .controls {
        display: flex;
        gap: 8px;
      }

      .table-shell {
        border: 1px solid var(--line);
        border-radius: 14px;
        overflow: hidden;
        background: var(--surface-strong);
      }

      table {
        width: 100%;
        border-collapse: collapse;
      }

      th,
      td {
        text-align: left;
        padding: 12px 10px;
        border-bottom: 1px solid var(--line);
        vertical-align: top;
      }

      th {
        font-size: 0.77rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
      }

      tr:last-child td {
        border-bottom: none;
      }

      .provider-name {
        display: block;
        font-weight: 600;
      }

      .provider-meta {
        display: block;
        color: var(--text-muted);
        font-size: 0.77rem;
        margin-top: 2px;
      }

      .status-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        min-width: 72px;
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid var(--line-strong);
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .status-ok {
        border-color: color-mix(in srgb, var(--ok) 42%, var(--line) 58%);
        color: var(--ok);
      }

      .status-warn {
        border-color: color-mix(in srgb, var(--warn) 42%, var(--line) 58%);
        color: var(--warn);
      }

      .status-missing {
        border-color: color-mix(in srgb, var(--danger) 42%, var(--line) 58%);
        color: var(--danger);
      }

      .row-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 7px;
      }

      button {
        appearance: none;
        border: 1px solid var(--line-strong);
        border-radius: 11px;
        padding: 8px 11px;
        background: transparent;
        color: var(--text);
        cursor: pointer;
        font-weight: 600;
        letter-spacing: 0.01em;
      }

      button:hover {
        border-color: var(--accent);
      }

      button:disabled {
        opacity: 0.55;
        cursor: default;
      }

      button.primary {
        background: var(--accent);
        border-color: var(--accent);
        color: #ffffff;
      }

      button.primary:hover {
        background: var(--accent-strong);
        border-color: var(--accent-strong);
      }

      button.danger {
        color: var(--danger);
      }

      #status {
        margin-top: 12px;
        min-height: 44px;
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: var(--surface-strong);
        white-space: pre-wrap;
        font-size: 0.91rem;
      }

      #status[data-level="success"] {
        border-color: color-mix(in srgb, var(--ok) 55%, var(--line) 45%);
      }

      #status[data-level="error"] {
        border-color: color-mix(in srgb, var(--danger) 55%, var(--line) 45%);
      }

      textarea {
        width: 100%;
        min-height: 480px;
        resize: vertical;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: var(--surface-strong);
        color: var(--text);
        padding: 12px;
        font-size: 0.86rem;
        line-height: 1.4;
        font-family: "JetBrains Mono", "Fira Code", "SFMono-Regular", "Menlo", monospace;
      }

      .manifest-note {
        margin: 0 0 10px;
        color: var(--text-muted);
        font-size: 0.84rem;
      }

      @media (max-width: 1040px) {
        .layout {
          grid-template-columns: 1fr;
        }

        textarea {
          min-height: 340px;
        }
      }

      @media (max-width: 700px) {
        .hero {
          align-items: flex-start;
          flex-direction: column;
        }

        .hero-actions {
          width: 100%;
          justify-content: space-between;
        }

        th,
        td {
          padding: 10px 8px;
        }
      }
    </style>
  </head>
  <body>
    <main class="wrap">
      <header class="hero">
        <div>
          <h1 class="title">Agent Vault Control Panel</h1>
          <p class="subtitle">Manage providers, rotate secrets, and edit manifest metadata from one local UI.</p>
        </div>
        <div class="hero-actions">
          <span class="theme-state" id="theme-state">Theme: auto</span>
          <button id="theme-toggle" type="button">Switch theme</button>
        </div>
      </header>

      <section class="layout">
        <article class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Providers</h2>
            <div class="controls">
              <button id="refresh-providers" type="button">Refresh</button>
            </div>
          </div>

          <div class="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Type</th>
                  <th>Secret</th>
                  <th>Endpoint</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="providers-body"></tbody>
            </table>
          </div>
          <div id="status" data-level="info">Loading dashboard...</div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <h2 class="panel-title">Manifest</h2>
            <div class="controls">
              <button id="refresh-manifest" type="button">Reload</button>
              <button class="primary" id="save-manifest" type="button">Save</button>
            </div>
          </div>
          <p class="manifest-note">Only metadata is stored here. Secret values stay in your OS key vault.</p>
          <textarea id="manifest-json" spellcheck="false" aria-label="Manifest JSON"></textarea>
        </article>
      </section>
    </main>

    <script>
      const authToken = __AUTH_TOKEN__;
      const THEME_STORAGE_KEY = "agent-vault-theme";
      const rootEl = document.documentElement;
      const providersBody = document.getElementById("providers-body");
      const statusEl = document.getElementById("status");
      const manifestEl = document.getElementById("manifest-json");
      const refreshProvidersBtn = document.getElementById("refresh-providers");
      const refreshManifestBtn = document.getElementById("refresh-manifest");
      const saveManifestBtn = document.getElementById("save-manifest");
      const themeToggleBtn = document.getElementById("theme-toggle");
      const themeStateEl = document.getElementById("theme-state");
      const darkPreference = window.matchMedia("(prefers-color-scheme: dark)");

      function getInitialTheme() {
        const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
        if (stored === "light" || stored === "dark") {
          return stored;
        }
        return darkPreference.matches ? "dark" : "light";
      }

      function applyTheme(theme) {
        rootEl.setAttribute("data-theme", theme);
        themeStateEl.textContent = `Theme: ${theme}`;
        themeToggleBtn.textContent = theme === "dark" ? "Use light mode" : "Use dark mode";
      }

      function setTheme(theme) {
        applyTheme(theme);
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
      }

      function toggleTheme() {
        const current = rootEl.getAttribute("data-theme") || "light";
        setTheme(current === "dark" ? "light" : "dark");
      }

      function setStatus(message, level = "info") {
        statusEl.textContent = message;
        statusEl.setAttribute("data-level", level);
      }

      async function apiRequest(path, options = {}) {
        const response = await fetch(path, options);
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(body.detail || "Request failed");
        }
        return body;
      }

      function statusBadge(text, variant) {
        const span = document.createElement("span");
        span.className = `status-badge ${variant}`;
        span.textContent = text;
        return span;
      }

      function withBusy(button, label, fn) {
        return async () => {
          const previous = button.textContent;
          button.disabled = true;
          button.textContent = label;
          try {
            await fn();
          } finally {
            button.disabled = false;
            button.textContent = previous;
          }
        };
      }

      function endpointSummary(provider) {
        if (!provider.endpoint) {
          return "-";
        }
        if (provider.endpoint_reachable === true) {
          return `${provider.endpoint} (ok)`;
        }
        if (provider.endpoint_reachable === false) {
          return `${provider.endpoint} (down)`;
        }
        return provider.endpoint;
      }

      function createProviderCell(provider) {
        const td = document.createElement("td");
        const name = document.createElement("span");
        name.className = "provider-name";
        name.textContent = provider.name;
        td.appendChild(name);
        if (provider.vault_key || provider.env_var) {
          const meta = document.createElement("span");
          meta.className = "provider-meta";
          const parts = [];
          if (provider.vault_key) parts.push(`vault: ${provider.vault_key}`);
          if (provider.env_var) parts.push(`env: ${provider.env_var}`);
          meta.textContent = parts.join(" | ");
          td.appendChild(meta);
        }
        return td;
      }

      async function loadProviders() {
        const data = await apiRequest("/providers");
        providersBody.innerHTML = "";

        if (!data.providers.length) {
          const emptyRow = document.createElement("tr");
          const emptyCell = document.createElement("td");
          emptyCell.colSpan = 5;
          emptyCell.textContent = "No providers configured in manifest.";
          emptyRow.appendChild(emptyCell);
          providersBody.appendChild(emptyRow);
          return;
        }

        for (const provider of data.providers) {
          const tr = document.createElement("tr");
          tr.appendChild(createProviderCell(provider));

          const typeTd = document.createElement("td");
          typeTd.appendChild(statusBadge(provider.type || "unknown", "status-warn"));
          tr.appendChild(typeTd);

          const secretTd = document.createElement("td");
          if (provider.has_secret === true) {
            secretTd.appendChild(statusBadge("present", "status-ok"));
          } else if (provider.has_secret === false) {
            secretTd.appendChild(statusBadge("missing", "status-missing"));
          } else {
            secretTd.appendChild(statusBadge("n/a", "status-warn"));
          }
          tr.appendChild(secretTd);

          const endpointTd = document.createElement("td");
          endpointTd.textContent = endpointSummary(provider);
          tr.appendChild(endpointTd);

          const actionsTd = document.createElement("td");
          const actions = document.createElement("div");
          actions.className = "row-actions";

          const setBtn = document.createElement("button");
          setBtn.className = "primary";
          setBtn.textContent = "Set / Rotate";
          setBtn.addEventListener(
            "click",
            withBusy(setBtn, "Saving...", async () => {
              const secret = window.prompt(`Enter secret for ${provider.name}`);
              if (secret === null) return;
              if (!secret.trim()) {
                setStatus("Secret cannot be empty", "error");
                return;
              }
              await apiRequest(`/providers/${encodeURIComponent(provider.name)}/secret`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "X-Agent-Vault-Token": authToken
                },
                body: JSON.stringify({ secret })
              });
              setStatus(`Secret stored for ${provider.name}`, "success");
              await loadProviders();
            })
          );
          actions.appendChild(setBtn);

          const delBtn = document.createElement("button");
          delBtn.className = "danger";
          delBtn.textContent = "Delete";
          delBtn.addEventListener(
            "click",
            withBusy(delBtn, "Deleting...", async () => {
              const confirmed = window.confirm(`Delete secret for ${provider.name}?`);
              if (!confirmed) return;
              const result = await apiRequest(`/providers/${encodeURIComponent(provider.name)}/secret`, {
                method: "DELETE",
                headers: {
                  "X-Agent-Vault-Token": authToken
                }
              });
              setStatus(
                result.deleted
                  ? `Secret deleted for ${provider.name}`
                  : `No secret found for ${provider.name}`,
                result.deleted ? "success" : "info"
              );
              await loadProviders();
            })
          );
          actions.appendChild(delBtn);

          const testBtn = document.createElement("button");
          testBtn.textContent = "Test";
          testBtn.addEventListener(
            "click",
            withBusy(testBtn, "Testing...", async () => {
              const result = await apiRequest(`/providers/${encodeURIComponent(provider.name)}/test`, {
                method: "POST"
              });
              if (result.ok) {
                setStatus(`Provider test succeeded: ${provider.name}`, "success");
              } else {
                const details = result.failures.length ? result.failures.join(", ") : "unknown failure";
                setStatus(`Provider test failed: ${provider.name} (${details})`, "error");
              }
              await loadProviders();
            })
          );
          actions.appendChild(testBtn);

          actionsTd.appendChild(actions);
          tr.appendChild(actionsTd);
          providersBody.appendChild(tr);
        }
      }

      async function loadManifest() {
        const data = await apiRequest("/manifest");
        manifestEl.value = JSON.stringify(data.manifest, null, 2);
      }

      async function refreshProviders() {
        try {
          await loadProviders();
          setStatus("Provider list refreshed", "info");
        } catch (error) {
          setStatus(error.message, "error");
        }
      }

      refreshProvidersBtn.addEventListener("click", refreshProviders);
      themeToggleBtn.addEventListener("click", toggleTheme);

      darkPreference.addEventListener("change", () => {
        if (!window.localStorage.getItem(THEME_STORAGE_KEY)) {
          applyTheme(darkPreference.matches ? "dark" : "light");
        }
      });

      refreshManifestBtn.addEventListener("click", async () => {
        try {
          await loadManifest();
          setStatus("Manifest reloaded", "info");
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      saveManifestBtn.addEventListener(
        "click",
        withBusy(saveManifestBtn, "Saving...", async () => {
          try {
            const parsed = JSON.parse(manifestEl.value);
            await apiRequest("/manifest", {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                "X-Agent-Vault-Token": authToken
              },
              body: JSON.stringify({ manifest: parsed })
            });
            setStatus("Manifest saved", "success");
            await loadProviders();
          } catch (error) {
            setStatus(error.message, "error");
          }
        })
      );

      async function init() {
        applyTheme(getInitialTheme());
        try {
          await loadManifest();
          await loadProviders();
          setStatus("Dashboard ready", "success");
        } catch (error) {
          setStatus(error.message, "error");
        }
      }

      init();
    </script>
  </body>
</html>
""".replace("__AUTH_TOKEN__", token_json)
