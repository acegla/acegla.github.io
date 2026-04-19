import os
from pathlib import Path

# W Dockerze DATA_DIR=/app/data (volume), lokalnie obok skryptów
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent))
DATA_DIR.mkdir(parents=True, exist_ok=True)
