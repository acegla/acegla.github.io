import anthropic
import os
import re
import unicodedata
from datetime import date

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BLOG_LANG = os.getenv("BLOG_LANG", "pl")  # "pl" lub "en"

SYSTEM_PROMPT = f"""Jesteś asystentem blogera. Tworzysz posty w formacie Jekyll Markdown.

Język bloga: {BLOG_LANG}

Zasady:
- Generuj TYLKO plik Markdown, zero komentarzy od siebie
- Front matter: title, date, categories, tags, layout: post
- Tytuł: zwięzły, przyciągający uwagę
- Treść: przetwarzaj surowe notatki w spójny, naturalny post — nie przepisuj dosłownie
- Styl: osobisty, nieformliany, autentyczny — nie korporacyjny
- Zdjęcia wstaw w odpowiednich miejscach: ![opis](/assets/images/NAZWA_PLIKU)
- Na końcu zostaw slug w komentarzu HTML: <!-- slug: twoj-slug -->
"""


def build_prompt(entries: list) -> tuple[str, list]:
    """Buduje prompt i zbiera listę zdjęć ze wszystkich wpisów."""
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
{"".join(lines)}
--- KONIEC NOTATEK ---

Zdjęcia dostępne (użyj ich w odpowiednich miejscach w treści):
{chr(10).join(f'- {img["filename"]}' for img in all_images) if all_images else "(brak zdjęć)"}

Pamiętaj o komentarzu <!-- slug: ... --> na końcu pliku.
"""
    return prompt, all_images


def extract_slug(md: str) -> str:
    """Wyciąga slug z komentarza HTML lub generuje z tytułu."""
    match = re.search(r"<!--\s*slug:\s*([a-z0-9-]+)\s*-->", md)
    if match:
        return match.group(1)

    # fallback: wyciągnij title z front matter
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


async def generate_draft(entries: list) -> tuple[str, str, list]:
    """
    Zwraca (markdown_content, slug, images_list).
    images_list to lista dict z kluczami filename, url.
    """
    prompt, images = build_prompt(entries)

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    md = response.content[0].text.strip()

    # Usuń ewentualne backtick fences jeśli model je dodał
    md = re.sub(r"^```(?:markdown)?\n?", "", md)
    md = re.sub(r"\n?```$", "", md)

    slug = extract_slug(md)
    today = date.today().isoformat()
    filename_slug = f"{today}-{slug}"

    # Upewnij się że slug w komentarzu jest aktualny
    if "<!-- slug:" not in md:
        md += f"\n\n<!-- slug: {slug} -->"

    return md, filename_slug, images
