from pathlib import Path

from agent_vault.manifest import load_manifest


def test_load_manifest(tmp_path: Path) -> None:
    file = tmp_path / "manifest.json"
    file.write_text(
        '{"version":"2026.1","providers":{"p":{"type":"upstream"}}}',
        encoding="utf-8",
    )

    manifest = load_manifest(file)

    assert manifest.version == "2026.1"
    assert "p" in manifest.providers
