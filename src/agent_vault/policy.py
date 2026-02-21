from __future__ import annotations

from agent_vault.models import Manifest


class PolicyError(RuntimeError):
    pass


def resolve_provider(manifest: Manifest, explicit_provider: str | None) -> str:
    if explicit_provider:
        if explicit_provider not in manifest.providers:
            raise PolicyError(f"Unknown provider: {explicit_provider}")
        return explicit_provider

    ranked = sorted(
        manifest.providers.items(),
        key=lambda item: item[1].priority if item[1].priority is not None else 10_000,
    )
    if not ranked:
        raise PolicyError("No providers configured")
    return ranked[0][0]
