#!/usr/bin/env python3
"""
Analizuje posty z _posts/ i zapisuje profil stylu do blog_context.md.

Użycie:
    python learn_style.py
    python learn_style.py --posts-dir ../../_posts --max-posts 15
    python learn_style.py --dry-run   # tylko wyświetla, nie zapisuje
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
_DEBUG_PROMPT = Path(__file__).parent / "debug_prompt_learn.md"

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_POSTS_DIR = REPO_ROOT / "_posts"
CONTEXT_FILE = SCRIPT_DIR / "blog_context.md"

ANALYSIS_PROMPT = """Przeanalizuj poniższe posty na bloga i napisz ZWIĘZŁY profil stylu autora.

Profil ma służyć jako instrukcja dla modelu językowego który będzie pisał przyszłe posty.
Pisz go w drugiej osobie, do modelu (np. "Autor pisze...", "Używaj...", "Unikaj...").

Struktura odpowiedzi — DOKŁADNIE ten format (markdown, bez dodatkowych sekcji):

## O blogu
<!-- 2-3 zdania: czego dotyczy blog, jaka jest jego tematyka -->

## Głos i styl
<!-- Jak autor pisze: ton, długość zdań, czy jest bezpośredni, humor, emocjonalność -->

## Typowe tematy
<!-- Lista konkretnych kategorii i tematów które pojawiają się w postach -->

## Charakterystyczne zwroty i zabiegi
<!-- Konkretne wzorce: czy używa list, nawiasów, emotikonów, ironii, przypisów, itp. -->

## Czego unikać
<!-- Na podstawie postów: co byłoby "nie w stylu" autora -->

## Przykładowe frazy / ton
<!-- 3-5 krótkich cytatów lub parafraz które oddają styl autora -->

---

POSTY DO ANALIZY:

{posts}
"""


def strip_front_matter(content: str) -> str:
    """Usuwa YAML front matter z początku pliku."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content.strip()


def load_posts(posts_dir: Path, max_posts: int) -> list[dict]:
    files = sorted(posts_dir.glob("*.md"), reverse=True)[:max_posts]
    posts = []
    for f in files:
        raw = f.read_text(encoding="utf-8")
        body = strip_front_matter(raw)
        if len(body) < 100:
            continue
        posts.append({"filename": f.name, "body": body})
    return posts


def build_analysis_prompt(posts: list[dict]) -> str:
    chunks = []
    for p in posts:
        # Przytnij każdy post do ~1500 znaków żeby nie przekroczyć kontekstu
        body = p["body"]
        if len(body) > 1500:
            body = body[:1500] + "\n[...skrócono...]"
        chunks.append(f"### {p['filename']}\n\n{body}")
    return ANALYSIS_PROMPT.format(posts="\n\n---\n\n".join(chunks))


def call_claude(prompt: str) -> str:
    import anthropic
    model = os.getenv("CLAUDE_MODEL", "claude-opus-4-5")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def call_ollama(prompt: str) -> str:
    import ollama
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    client = ollama.Client(host=host)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"num_predict": 2048},
    )
    return response.message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Analizuje styl bloga i zapisuje do blog_context.md")
    parser.add_argument("--posts-dir", type=Path, default=DEFAULT_POSTS_DIR,
                        help=f"Ścieżka do katalogu z postami (domyślnie: {DEFAULT_POSTS_DIR})")
    parser.add_argument("--max-posts", type=int, default=20,
                        help="Maksymalna liczba postów do analizy (domyślnie: 20)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Wyświetl wynik bez zapisywania do pliku")
    parser.add_argument("--backend", choices=["claude", "ollama"],
                        default=os.getenv("LLM_BACKEND", "ollama").lower(),
                        help="Backend LLM (domyślnie z LLM_BACKEND lub 'ollama')")
    args = parser.parse_args()

    if not args.posts_dir.exists():
        print(f"❌ Katalog z postami nie istnieje: {args.posts_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 Wczytuję posty z: {args.posts_dir}")
    posts = load_posts(args.posts_dir, args.max_posts)
    if not posts:
        print("❌ Brak postów do analizy.", file=sys.stderr)
        sys.exit(1)
    print(f"📝 Znaleziono {len(posts)} postów do analizy.")

    prompt = build_analysis_prompt(posts)

    print(f"🤖 Analizuję styl ({args.backend})...")
    try:
        _DEBUG_PROMPT.write_text(
            f"# SYSTEM\n\n{prompt}\n\n", encoding="utf-8"
        )
        if args.backend == "ollama":
            result = call_ollama(prompt)
        else:
            result = call_claude(prompt)
    except Exception as e:
        print(f"❌ Błąd LLM: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("\n" + "=" * 60)
        print(result)
        print("=" * 60)
        print("\n[dry-run] Plik blog_context.md nie został zmieniony.")
        return

    CONTEXT_FILE.write_text(result, encoding="utf-8")
    print(f"✅ Zapisano profil stylu do: {CONTEXT_FILE}")
    print("\nPodgląd:")
    print("-" * 40)
    print(result[:600] + ("..." if len(result) > 600 else ""))


if __name__ == "__main__":
    main()
