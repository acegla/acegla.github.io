import os
import anthropic
from prompts import build_system_prompt, build_user_prompt, postprocess_md

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-5")

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def generate_draft(entries: list) -> tuple[str, str, list]:
    """Zwraca (markdown_content, filename_slug, images_list)."""
    system_prompt = build_system_prompt()
    user_prompt, images = build_user_prompt(entries)

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    md, filename_slug = postprocess_md(response.content[0].text)
    return md, filename_slug, images
