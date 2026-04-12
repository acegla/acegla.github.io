"""
Lokalny cache zdjęć z Discorda.
Pobiera i zapisuje obrazki w chwili otrzymania wiadomości,
zanim wygasną linki CDN (~24h).
"""

import aiohttp
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "images"


def ensure_dir() -> None:
    CACHE_DIR.mkdir(exist_ok=True)


def local_path(filename: str) -> Path:
    return CACHE_DIR / filename


def is_cached(filename: str) -> bool:
    return local_path(filename).exists()


async def fetch_and_save(url: str, filename: str) -> Path:
    """Pobiera zdjęcie z URL i zapisuje lokalnie. Zwraca ścieżkę."""
    ensure_dir()
    dest = local_path(filename)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status != 200:
                raise Exception(f"Nie mogę pobrać zdjęcia {filename} ({r.status})")
            dest.write_bytes(await r.read())

    return dest


def read(filename: str) -> bytes:
    """Czyta zdjęcie z lokalnego cache."""
    p = local_path(filename)
    if not p.exists():
        raise FileNotFoundError(f"Zdjęcie nie jest w cache: {filename}")
    return p.read_bytes()


def remove(filename: str) -> None:
    p = local_path(filename)
    if p.exists():
        p.unlink()


def clear_all() -> int:
    """Usuwa wszystkie zdjęcia z cache. Zwraca liczbę usuniętych."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for f in CACHE_DIR.iterdir():
        f.unlink()
        count += 1
    return count
