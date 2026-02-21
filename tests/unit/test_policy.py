from agent_vault.models import Manifest, ProviderConfig
from agent_vault.policy import resolve_provider


def test_resolve_by_priority() -> None:
    manifest = Manifest(
        version="2026.1",
        providers={
            "b": ProviderConfig(type="upstream", priority=2),
            "a": ProviderConfig(type="upstream", priority=1),
        },
    )

    assert resolve_provider(manifest, None) == "a"
