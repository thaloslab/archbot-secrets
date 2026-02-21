from __future__ import annotations

import secrets
import webbrowser

import typer
from rich.console import Console

from agent_vault.config import CONFIG_DIR, MANIFEST_PATH, SERVICE_NAME
from agent_vault.manifest import ManifestError
from agent_vault.policy import PolicyError
from agent_vault.runner import RunnerError, parse_command, run_with_env
from agent_vault.service import AgentVaultService, ServiceError
from agent_vault.vault import VaultError

app = typer.Typer(help="Agent Vault: local-first secrets manager for agent runtimes")
console = Console()
vault_service = AgentVaultService(MANIFEST_PATH, SERVICE_NAME)

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@app.command("init")
def init_manifest() -> None:
    """Initialize ~/.config/ai/ai_agents/manifest.json if missing."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not vault_service.init_manifest():
        console.print(f"[yellow]Manifest already exists:[/yellow] {MANIFEST_PATH}")
        raise typer.Exit(code=0)

    console.print(f"[green]Manifest created:[/green] {MANIFEST_PATH}")


@app.command("set-key")
def set_key(provider: str) -> None:
    """Store a provider key in the OS keyring."""
    secret = typer.prompt(f"Enter secret for {provider}", hide_input=True)
    try:
        vault_service.set_provider_secret(provider, secret)
        console.print(f"[green]Secret stored for {provider}[/green]")
    except (ManifestError, ServiceError, VaultError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command("doctor")
def doctor() -> None:
    """Run basic local health checks."""
    try:
        statuses = vault_service.list_provider_statuses()
    except (ManifestError, VaultError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    failures: list[str] = []
    for status in statuses:
        if status.has_secret is False:
            failures.append(f"missing key for {status.name}")
        if status.endpoint and status.endpoint_reachable is False:
            failures.append(f"endpoint unreachable for {status.name}: {status.endpoint}")

    if failures:
        for failure in failures:
            console.print(f"[red]- {failure}[/red]")
        raise typer.Exit(code=1)

    console.print("[green]doctor checks passed[/green]")


@app.command("run")
def run_command(
    command: str = typer.Argument(..., help="Command string to execute"),
    provider: str | None = typer.Option(None, "--provider", help="Provider override"),
) -> None:
    """Run a command with ephemeral env injection."""
    try:
        run_context = vault_service.build_run_context(provider)
        code = run_with_env(parse_command(command), run_context.injected_env)
        raise typer.Exit(code=code)

    except (ManifestError, PolicyError, ServiceError, VaultError, RunnerError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command("dashboard")
def dashboard(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host (loopback only)"),
    port: int = typer.Option(8765, "--port", help="Bind port"),
    open_browser: bool = typer.Option(False, "--open-browser", help="Open dashboard in browser"),
    auth_token: str | None = typer.Option(
        None,
        "--auth-token",
        help="Optional API auth token for mutating endpoints",
    ),
) -> None:
    """Run the local dashboard and API server."""
    if host not in LOOPBACK_HOSTS:
        console.print("[red]Dashboard host must be loopback (127.0.0.1, localhost, ::1)[/red]")
        raise typer.Exit(code=1)

    token = auth_token or secrets.token_urlsafe(24)
    url = f"http://{host}:{port}"

    try:
        from agent_vault.api import create_app
        import uvicorn
    except ImportError as exc:
        console.print(f"[red]Missing dashboard dependencies: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Dashboard:[/green] {url}")
    console.print("[yellow]Use this token for write API calls (X-Agent-Vault-Token):[/yellow]")
    console.print(token)

    if open_browser:
        webbrowser.open(url, new=1, autoraise=True)

    try:
        uvicorn.run(create_app(vault_service, token), host=host, port=port, log_level="info")
    except OSError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
