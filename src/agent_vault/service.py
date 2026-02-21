from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from agent_vault.manifest import load_manifest, write_manifest
from agent_vault.models import Manifest, ProviderConfig
from agent_vault.policy import resolve_provider
from agent_vault.vault import delete_secret, get_secret, has_secret, set_secret


class ServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    name: str
    provider_type: str
    env_var: str | None
    vault_key: str | None
    endpoint: str | None
    priority: int | None
    has_secret: bool | None
    endpoint_reachable: bool | None


@dataclass(frozen=True, slots=True)
class ProviderTestResult:
    provider: str
    has_secret: bool | None
    endpoint_reachable: bool | None
    failures: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


@dataclass(frozen=True, slots=True)
class RunContext:
    provider: str
    injected_env: dict[str, str]


def default_manifest() -> Manifest:
    return Manifest(
        version="2026.1",
        identity="primary-dev-node",
        providers={
            "openai_pro": ProviderConfig(
                vault_key="api.openai.com/pro_key",
                env_var="OPENAI_API_KEY",
                type="upstream",
                priority=1,
            ),
            "openrouter": ProviderConfig(
                vault_key="api.openrouter.ai/default",
                env_var="OPENROUTER_API_KEY",
                type="gateway",
                endpoint="https://openrouter.ai/api/v1",
                priority=2,
            ),
            "local_ollama": ProviderConfig(
                type="local",
                endpoint="http://localhost:11434",
                priority=10,
            ),
        },
    )


class AgentVaultService:
    def __init__(self, manifest_path: Path, service_name: str) -> None:
        self._manifest_path = manifest_path
        self._service_name = service_name

    def init_manifest(self) -> bool:
        if self._manifest_path.exists():
            return False

        write_manifest(self._manifest_path, default_manifest())
        return True

    def load_manifest(self) -> Manifest:
        return load_manifest(self._manifest_path)

    def save_manifest(self, manifest: Manifest) -> None:
        write_manifest(self._manifest_path, manifest)

    def list_provider_statuses(self) -> list[ProviderStatus]:
        manifest = self.load_manifest()
        statuses: list[ProviderStatus] = []
        for provider_name, config in manifest.providers.items():
            has_provider_secret: bool | None = None
            if config.vault_key:
                has_provider_secret = has_secret(self._service_name, config.vault_key)

            endpoint_reachable: bool | None = None
            if config.endpoint:
                endpoint_reachable = self._is_endpoint_reachable(config.endpoint)

            statuses.append(
                ProviderStatus(
                    name=provider_name,
                    provider_type=config.type,
                    env_var=config.env_var,
                    vault_key=config.vault_key,
                    endpoint=config.endpoint,
                    priority=config.priority,
                    has_secret=has_provider_secret,
                    endpoint_reachable=endpoint_reachable,
                )
            )

        return sorted(
            statuses,
            key=lambda status: (
                status.priority if status.priority is not None else 10_000,
                status.name,
            ),
        )

    def set_provider_secret(self, provider: str, secret: str) -> None:
        if not secret.strip():
            raise ServiceError("Secret cannot be empty")

        config = self._provider_config(provider)
        if not config.vault_key:
            raise ServiceError(f"Provider has no vault_key: {provider}")

        set_secret(self._service_name, config.vault_key, secret)

    def delete_provider_secret(self, provider: str) -> bool:
        config = self._provider_config(provider)
        if not config.vault_key:
            raise ServiceError(f"Provider has no vault_key: {provider}")
        return delete_secret(self._service_name, config.vault_key)

    def test_provider(self, provider: str) -> ProviderTestResult:
        config = self._provider_config(provider)
        failures: list[str] = []

        secret_status: bool | None = None
        if config.vault_key:
            secret_status = has_secret(self._service_name, config.vault_key)
            if not secret_status:
                failures.append("missing secret")

        endpoint_status: bool | None = None
        if config.endpoint:
            endpoint_status = self._is_endpoint_reachable(config.endpoint)
            if not endpoint_status:
                failures.append("endpoint unreachable")

        return ProviderTestResult(
            provider=provider,
            has_secret=secret_status,
            endpoint_reachable=endpoint_status,
            failures=tuple(failures),
        )

    def build_run_context(self, provider_override: str | None) -> RunContext:
        manifest = self.load_manifest()
        chosen = resolve_provider(manifest, provider_override)
        config = manifest.providers[chosen]

        injected_env: dict[str, str] = {}
        if config.env_var and config.vault_key:
            injected_env[config.env_var] = get_secret(self._service_name, config.vault_key)

        return RunContext(provider=chosen, injected_env=injected_env)

    def _provider_config(self, provider: str) -> ProviderConfig:
        manifest = self.load_manifest()
        config = manifest.providers.get(provider)
        if config is None:
            raise ServiceError(f"Provider not found: {provider}")
        return config

    @staticmethod
    def _is_endpoint_reachable(endpoint: str) -> bool:
        parsed = urlparse(endpoint)
        host = parsed.hostname
        if not host:
            return False

        port = parsed.port
        if port is None:
            if parsed.scheme in {"https", "wss"}:
                port = 443
            elif parsed.scheme in {"http", "ws"}:
                port = 80
            else:
                return False
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False
