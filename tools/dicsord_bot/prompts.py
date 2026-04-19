import os
import re
import unicodedata
from datetime import date
from pathlib import Path

BLOG_LANG = os.getenv("BLOG_LANG", "pl")

# Ładuje blog_context.md z tego samego katalogu co ten plik
_CONTEXT_FILE = Path(__file__).parent / "blog_context.md"


def load_blog_context() -> str:
    if not _CONTEXT_FILE.exists():
        return ""
    text = _CONTEXT_FILE.read_text(encoding="utf-8").strip()
    return text if text else ""


def build_system_prompt() -> str:
    context = load_blog_context()
    context_section = (
        f"\n\n--- KONTEKST BLOGA ---\n{context}\n--- KONIEC KONTEKSTU ---"
        if context
        else ""
    )
    today = date.today().isoformat()
    return f"""Jesteś asystentem blogera. Tworzysz posty w formacie Jekyll Markdown.

Język bloga: {BLOG_LANG}

Zasady:
- Generuj TYLKO plik Markdown, zero komentarzy od siebie
- Front matter: title, date, categories, tags, layout: post, media_subpath: /assets/photos/{today}/
- Tytuł: zwięzły, przyciągający uwagę
- Treść: przetwarzaj surowe notatki w spójny, naturalny post — nie przepisuj dosłownie
- Styl: osobisty, nieformalny, autentyczny — nie korporacyjny, używaj formatowania które jest dostępne w markdown (np nagłówki, listy, pogrubienia, kursywy, linki, cytaty, tabele, kod, itp.)
- Zdjęcia wstaw w odpowiednich miejscach: ![opis](/NAZWA_PLIKU) — samo media_subpath ustawi folder
- Na końcu zostaw slug w komentarzu HTML: <!-- slug: twoj-slug -->{context_section}
"""


def build_user_prompt(entries: list) -> tuple[str, list]:
    """Zwraca (prompt_text, images_list)."""
    lines = []
    all_images = []

    for entry in entries:
        lines.append(f"[{entry['timestamp']}]")
        if entry["text"]:
            lines.append(entry["text"])
        if entry["images"]:
            for img in entry["images"]:
                lines.append(f"  📷 zdjęcie: {img['filename']}")
                all_images.append(img)
        lines.append("")

    prompt = f"""Poniżej surowe notatki z kilku dni. Wygeneruj post na bloga Jekyll.

--- NOTATKI ---
{"\n".join(lines)}
--- KONIEC NOTATEK ---

Zdjęcia dostępne (użyj ich w odpowiednich miejscach w treści):
{chr(10).join(f'- {img["filename"]}' for img in all_images) if all_images else "(brak zdjęć)"}

Pamiętaj o komentarzu <!-- slug: ... --> na końcu pliku.
"""
    return prompt, all_images


def extract_slug(md: str) -> str:
    match = re.search(r"<!--\s*slug:\s*([a-z0-9-]+)\s*-->", md)
    if match:
        return match.group(1)

    title_match = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", md, re.MULTILINE)
    if title_match:
        return slugify(title_match.group(1))

    return f"post-{date.today().isoformat()}"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60]


def postprocess_md(md: str) -> tuple[str, str]:
    """Czyści markdown i zwraca (md, filename_slug)."""
    md = md.strip()
    md = re.sub(r"^```(?:markdown)?\n?", "", md)
    md = re.sub(r"\n?```$", "", md)

    slug = extract_slug(md)
    today = date.today().isoformat()
    filename_slug = f"{today}-{slug}"

    if "<!-- slug:" not in md:
        md += f"\n\n<!-- slug: {slug} -->"

    return md, filename_slug
