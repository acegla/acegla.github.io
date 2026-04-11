import os
import ollama
from prompts import build_system_prompt, build_user_prompt, postprocess_md

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

_client = ollama.AsyncClient(host=OLLAMA_HOST)


async def generate_draft(entries: list) -> tuple[str, str, list]:
    """Zwraca (markdown_content, filename_slug, images_list)."""
    system_prompt = build_system_prompt()
    user_prompt, images = build_user_prompt(entries)

    response = await _client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"num_predict": 4096},
    )

    md, filename_slug = postprocess_md(response.message.content)
    return md, filename_slug, images
