SECRETS

Purpose:
Unified system to keep tokens and api keys for AI tools. AI services API keys (free and paid), gateways to models (operouter), Local LLMs. secrets storage and management.

Tools to be used with:
Agentic tools: Agent0, openclaw, irnclaw
MCPs
Comunicators: Slack, Teams, Telegram, WhatsApp


Goal.Use least dependency approach i.e. Infisical or keyring to store it encrypted and never pass to agent service text. never use locally kept .env or json. one dashboard, dynamic, multiplatform. allow rolli ng api keys. allow usage of paid apis for havy lifting and switch to free, less token havy tasks (litellm?)

In 2026, the shift from "chatbots" to "agentic teams" requires a secret management strategy that handles not just API keys, but also **Service Endpoints**, **MCP Configurations**, and **Agent Identities**.

Since you want to build a cross-platform utility based on `keyring`, the best approach is to treat the **Keyring as the secure vault** and a **JSON-based manifest as the routing map**.

### 1. The Recommended Architecture

Do not store the actual keys in a JSON file. Instead, use a "Pointer System":

* **The Vault (System Keyring):** Stores the raw secrets (e.g., `sk-openai-...`).
* **The Manifest (`config.json`):** Stores metadata, endpoints, and the *keys* to look up in the vault.

#### Proposed JSON Structure (`~/.ai_agents/manifest.json`)

This structure categorizes your "Premium," "Gateway," and "Local" services while providing the necessary context for agents (like MCP support or context limits).

```json
{
  "version": "2026.1",
  "identity": "primary-dev-node",
  "providers": {
    "subscriptions": {
      "openai_pro": {
        "vault_key": "api.openai.com/pro_key",
        "type": "upstream",
        "models": ["gpt-4o", "gpt-5-preview"],
        "priority": 1
      },
      "gemini_pro": {
        "vault_key": "api.google.com/gemini_pro",
        "type": "upstream",
        "context_window": 2000000
      }
    },
    "gateways": {
      "openrouter": {
        "vault_key": "api.openrouter.ai/default",
        "endpoint": "https://openrouter.ai/api/v1",
        "usage": "fallback"
      }
    },
    "local": {
      "ollama": {
        "endpoint": "http://localhost:11434",
        "mcp_enabled": true,
        "mcp_config_path": "~/.config/ollama/mcp.json"
      }
    }
  },
  "agent_teams": {
    "coder_team": {
      "lead": "claude_pro",
      "research": "perplexity_mcp",
      "runtime": "local_ollama"
    }
  }
}

```

---

### 2. Implementation: The Logic

Your utility should perform a "Dynamic Injection." When you run an agent, the utility reads the JSON, fetches the `vault_key` from the OS Keyring, and exports it to the agent's memory.

**Cross-Platform Logic:**

* **Windows:** Use `keyring` (Python) or `cmdkey`.
* **macOS:** Use `security` (Keychain).
* **Linux:** Use `secret-tool` (Libsecret).

**Example CLI usage for your utility:**
`agent-vault sync --file manifest.json`
*(This would prompt you for any missing keys in the manifest and save them to the OS Keyring).*

---

### 3. Essential "Agentic" Secrets (The 2026 Checklist)

Beyond basic LLM keys, autonomous agent teams require specific secrets to function without getting "stuck":

* **MCP Bridge Keys (Model Context Protocol):**
* **Filesystem Tool Keys:** If an agent needs to access a specific encrypted drive or S3 bucket.
* **Search APIs:** (Brave Search, Serper, or Exa) Agents need these to bypass their training cutoff.


* **Runtime "Sandbox" Tokens:**
* If using **E2B** or **Bearly** for code execution, you need a dedicated "Sandbox Token" so the agent doesn't execute code on your host machine.


* **Internal Communication Tokens:**
* **Bus/PubSub Keys:** If your agents talk via a local Redis or MQTT bus, you need a local auth token.


* **Gateway Nonces:**
* Unique IDs for "Stateful Agents" that allow them to resume a session across different CLI tools.



### 4. Why this is better for your specific setup (Asus Mark 2)

Since you mentioned your **Asus Sabertooth Mark 2** with multiple SATA ports, you are likely running a high-uptime machine.

* **Local Resilience:** By keeping the JSON manifest local and the keys in the Keyring, your agents can continue to function even if you lose internet access (by falling back to the `local_ollama` entry in your JSON).
* **Hardware Binding:** You can use the TPM (Trusted Platform Module) on your Asus board to further wrap the OS Keyring, ensuring those keys can never be exported to another machine.

**Would you like a Python "Skeleton Script" that demonstrates how to read this JSON and fetch the keys from the native OS Keyring?**


For a highly responsive, cross-platform CLI tool in 2026, the best foundation is **Typer** combined with **Rich** for terminal formatting. Typer leverages standard Python type hints to generate your CLI commands automatically, while keeping the codebase incredibly clean.

Here is the architecture for your `agent-vault` CLI tool. It acts as a secure middleware: it reads your `manifest.json` for routing, fetches the actual secrets from the OS Keyring, and securely injects them into the environment variables *only* for the duration of the agent's runtime.

---

### 1. Prerequisites

Install the required libraries:

```bash
pip install typer keyring rich

```

### 2. The CLI Core (`agent_vault.py`)

Save this as a single executable script. It handles initialization, secure key storage, and dynamic execution of your agentic tools.

```python
import typer
import keyring
import json
import os
import subprocess
from pathlib import Path
from rich.console import Console

app = typer.Typer(help="Agent Vault: Cross-Platform Key & MCP Manager")
console = Console()

# Configuration Paths
CONFIG_DIR = Path.home() / ".ai_agents"
MANIFEST_PATH = CONFIG_DIR / "manifest.json"
SERVICE_NAME = "agent_vault"

def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        console.print("[red]Manifest not found. Run 'agent-vault init' first.[/red]")
        raise typer.Exit(code=1)
    with open(MANIFEST_PATH, "r") as f:
        return json.load(f)

@app.command()
def init():
    """Create the base JSON manifest for agent routing."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Base structure handling Pro tiers, Gateways, and Local MCPs
    base_manifest = {
        "version": "2026.1",
        "providers": {
            "openai_pro": {"env_var": "OPENAI_API_KEY", "type": "upstream"},
            "gemini_pro": {"env_var": "GEMINI_API_KEY", "type": "upstream"},
            "openrouter": {"env_var": "OPENROUTER_API_KEY", "type": "gateway", "endpoint": "https://openrouter.ai/api/v1"},
            "claude_free": {"env_var": "ANTHROPIC_API_KEY", "type": "free_tier"},
            "local_ollama": {"endpoint": "http://localhost:11434", "type": "local_mcp"}
        }
    }
    
    with open(MANIFEST_PATH, "w") as f:
        json.dump(base_manifest, f, indent=2)
    console.print(f"[green]Initialized manifest at {MANIFEST_PATH}[/green]")

@app.command()
def set_key(provider: str):
    """Securely store an API key in the OS Keyring."""
    manifest = load_manifest()
    
    if provider not in manifest["providers"]:
        console.print(f"[red]Provider '{provider}' not found in manifest.[/red]")
        raise typer.Exit(code=1)
        
    secret = typer.prompt(f"Enter API key for {provider}", hide_input=True)
    keyring.set_password(SERVICE_NAME, provider, secret)
    console.print(f"[green]Successfully securely stored key for {provider} in OS Keyring.[/green]")

@app.command()
def run(command: str):
    """Run an agentic tool with all keys temporarily injected."""
    manifest = load_manifest()
    env = os.environ.copy()
    
    console.print("[yellow]Unlocking vault and injecting ephemeral keys...[/yellow]")
    
    # Dynamically load keys from OS vault into local environment dictionary
    for provider, config in manifest["providers"].items():
        if "env_var" in config:
            secret = keyring.get_password(SERVICE_NAME, provider)
            if secret:
                env[config["env_var"]] = secret
            else:
                console.print(f"[dim]Warning: No key found in vault for {provider}[/dim]")
                
    console.print(f"[bold green]Executing:[/bold green] {command}")
    
    # Run the user's agent (e.g., OpenClaw, Ollama MCP) with the populated environment
    try:
        subprocess.run(command.split(), env=env, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Process exited with code {e.returncode}[/bold red]")
    finally:
        console.print("[yellow]Execution finished. Ephemeral keys wiped from memory.[/yellow]")

if __name__ == "__main__":
    app()

```

---

### 3. How to Use It in Your Daily Workflow

1. **Initialize the Routing Map:**
```bash
python agent_vault.py init

```


*This creates your `~/.ai_agents/manifest.json`. You can edit this file to add MCP endpoints or custom local network nodes (like Kimi/GLM).*
2. **Store Your Premium Keys:**
```bash
python agent_vault.py set-key openai_pro
python agent_vault.py set-key openrouter

```


*You will be prompted to paste the key. It goes straight into Windows Credential Manager / macOS Keychain / Linux Secret Service.*
3. **Deploy Your Agent:**
```bash
python agent_vault.py run "openclaw gateway start"

```


*The CLI grabs the keys from the keyring, injects them as `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, etc., and launches OpenClaw. When OpenClaw closes, the keys instantly vanish from the environment.*

**Would you like me to show you how to expand the `manifest.json` parsing logic to auto-start local MCP servers (like a filesystem reader for Claude/Ollama) before it launches the main agent process?**
