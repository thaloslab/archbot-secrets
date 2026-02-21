from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from agent_vault.models import Manifest


class ManifestError(RuntimeError):
    pass


def load_manifest(path: Path) -> Manifest:
    if not path.exists():
        raise ManifestError(f"Manifest not found at {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid JSON in manifest: {exc}") from exc

    try:
        return Manifest.model_validate(data)
    except ValidationError as exc:
        raise ManifestError(f"Manifest validation failed: {exc}") from exc


def write_manifest(path: Path, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
