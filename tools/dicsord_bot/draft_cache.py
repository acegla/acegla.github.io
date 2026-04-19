"""
Cache ostatnio wygenerowanego draftu.
Gwarantuje, że /blog-publish opublikuje dokładnie to co /blog-draft pokazał.
Cache jest unieważniany przy dodaniu nowej notatki lub wyczyszczeniu bufora.
"""

import json
from pathlib import Path

DRAFT_FILE = Path(__file__).parent / "draft_cache.json"


def save(md_content: str, slug: str, images: list) -> None:
    DRAFT_FILE.write_text(
        json.dumps({"md_content": md_content, "slug": slug, "images": images}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load() -> tuple[str, str, list] | None:
    try:
        data = json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        return data["md_content"], data["slug"], data["images"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError):
        return None


def clear() -> None:
    DRAFT_FILE.unlink(missing_ok=True)
