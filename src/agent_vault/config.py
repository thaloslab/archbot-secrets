import os
from pathlib import Path

XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
CONFIG_DIR = XDG_CONFIG_HOME / "ai" / "ai_agents"
MANIFEST_PATH = CONFIG_DIR / "manifest.json"
SERVICE_NAME = "agent_vault"
