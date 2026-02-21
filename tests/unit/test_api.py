from __future__ import annotations

from fastapi.testclient import TestClient

from agent_vault.api import create_app
from agent_vault.models import Manifest, ProviderConfig
from agent_vault.service import ProviderStatus, ProviderTestResult, ServiceError


class FakeService:
    def __init__(self) -> None:
        self.manifest = Manifest(
            version="2026.1",
            providers={
                "openai_pro": ProviderConfig(
                    type="upstream",
                    vault_key="api.openai.com/pro_key",
                )
            },
        )
        self.secret_by_provider: dict[str, str] = {}

    def list_provider_statuses(self) -> list[ProviderStatus]:
        return [
            ProviderStatus(
                name="openai_pro",
                provider_type="upstream",
                env_var="OPENAI_API_KEY",
                vault_key="api.openai.com/pro_key",
                endpoint=None,
                priority=1,
                has_secret=bool(self.secret_by_provider.get("openai_pro")),
                endpoint_reachable=None,
            )
        ]

    def set_provider_secret(self, provider: str, secret: str) -> None:
        if provider != "openai_pro":
            raise ServiceError("Provider not found")
        self.secret_by_provider[provider] = secret

    def delete_provider_secret(self, provider: str) -> bool:
        if provider != "openai_pro":
            raise ServiceError("Provider not found")
        return self.secret_by_provider.pop(provider, None) is not None

    def test_provider(self, provider: str) -> ProviderTestResult:
        if provider != "openai_pro":
            raise ServiceError("Provider not found")
        exists = bool(self.secret_by_provider.get(provider))
        failures: tuple[str, ...] = tuple() if exists else ("missing secret",)
        return ProviderTestResult(
            provider=provider,
            has_secret=exists,
            endpoint_reachable=None,
            failures=failures,
        )

    def load_manifest(self) -> Manifest:
        return self.manifest

    def save_manifest(self, manifest: Manifest) -> None:
        self.manifest = manifest


def test_mutating_endpoints_require_token() -> None:
    service = FakeService()
    client = TestClient(create_app(service, "topsecret"))

    response = client.post("/providers/openai_pro/secret", json={"secret": "abc"})

    assert response.status_code == 401


def test_set_provider_secret_with_token() -> None:
    service = FakeService()
    client = TestClient(create_app(service, "topsecret"))

    response = client.post(
        "/providers/openai_pro/secret",
        json={"secret": "abc123"},
        headers={"X-Agent-Vault-Token": "topsecret"},
    )

    assert response.status_code == 200
    assert service.secret_by_provider["openai_pro"] == "abc123"


def test_manifest_roundtrip() -> None:
    service = FakeService()
    client = TestClient(create_app(service, "topsecret"))

    payload = {
        "manifest": {
            "version": "2026.1",
            "providers": {
                "p": {"type": "upstream", "vault_key": "api.provider/p"},
            },
        }
    }
    put_response = client.put(
        "/manifest",
        json=payload,
        headers={"X-Agent-Vault-Token": "topsecret"},
    )
    get_response = client.get("/manifest")

    assert put_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["manifest"]["providers"]["p"]["vault_key"] == "api.provider/p"
