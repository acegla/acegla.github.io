"""
Persystentny bufor notatek — zapisuje wpisy do buffer.json.
Przeżywa restarty bota, pozwala zbierać notatki przez wiele dni.
"""

import json
from pathlib import Path
from data_dir import DATA_DIR

BUFFER_FILE = DATA_DIR / "buffer.json"


def load() -> list:
    if not BUFFER_FILE.exists():
        return []
    try:
        return json.loads(BUFFER_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save(entries: list) -> None:
    BUFFER_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def append(entry: dict) -> list:
    entries = load()
    entries.append(entry)
    save(entries)
    return entries


def clear() -> None:
    save([])
