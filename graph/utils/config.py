from pathlib import Path

# Prompt templates
PROMPTS = {
    path.stem[len("Agents_"):]: path.read_text(encoding="utf-8")
    for path in Path("./agents").glob("Agents_*.md")
}
