"""Configuration loader for agent prompts and workflow settings."""

from pathlib import Path

# Resolve agents directory relative to this file's location
_AGENTS_DIR = Path(__file__).parent.parent / "agents"

# Prompt templates keyed by agent name (e.g., "plan", "code", "eval")
PROMPTS: dict[str, str] = {}
if _AGENTS_DIR.exists():
    PROMPTS = {
        path.stem[len("Agents_"):]: path.read_text(encoding="utf-8")
        for path in sorted(_AGENTS_DIR.glob("Agents_*.md"))
    }



