import os
from pathlib import Path
import anthropic
from prompts import build_system_prompt, build_user_prompt, postprocess_md

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")

_DEBUG_PROMPT = Path(__file__).parent / "debug_prompt.md"


_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def generate_draft(entries: list) -> tuple[str, str, list]:
    """Zwraca (markdown_content, filename_slug, images_list)."""
    system_prompt = build_system_prompt()
    user_prompt, images = build_user_prompt(entries)

    _DEBUG_PROMPT.write_text(
        f"# SYSTEM\n\n{system_prompt}\n\n# USER\n\n{user_prompt}", encoding="utf-8"
    )

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    md, filename_slug = postprocess_md(response.content[0].text)
    return md, filename_slug, images
