# Blog Bot

Discord bot do tworzenia postów Jekyll z notatek i zdjęć.

## Szybki start

### 1. Discord — utwórz bota

1. Wejdź na [discord.com/developers/applications](https://discord.com/developers/applications)
2. **New Application** → nadaj nazwę
3. Zakładka **Bot** → **Add Bot** → skopiuj token → wklej jako `DISCORD_TOKEN`
4. Na tej samej stronie włącz: **Message Content Intent** (pod Privileged Gateway Intents)
5. Zakładka **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Read Messages/View Channels`, `Send Messages`, `Read Message History`, `Attach Files`, `Add Reactions`
6. Skopiuj wygenerowany URL → otwórz w przeglądarce → dodaj bota do swojego serwera

### 2. Discord — włącz tryb deweloperski i skopiuj ID kanału

Ustawienia Discorda → Zaawansowane → **Tryb dewelopera: ON**  
Prawym na kanał `#blog-input` → **Copy Channel ID** → wklej jako `BLOG_CHANNEL_ID`

### 3. GitHub — utwórz token

1. GitHub → Settings → Developer Settings → **Fine-grained tokens** → Generate new token
2. Repository access: tylko Twoje repo bloga
3. Permissions → Repository permissions → **Contents: Read and write**
4. Skopiuj token → `GITHUB_TOKEN`

### 4. Konfiguracja

```bash
cp .env.example .env
# uzupełnij .env swoimi wartościami
```

### 5. Uruchomienie

**Przez Docker (zalecane):**
```bash
docker compose up -d --build
docker compose logs -f  # sprawdź czy działa
```

**Lokalnie (dev):**
```bash
pip install -r requirements.txt
python bot.py
```

---

## Aktualizacja (po zmianach w kodzie)

```bash
git pull
docker compose up -d --build
docker compose logs -f  # upewnij się że bot wystartował
```

`docker compose down` bez `-v` nie usuwa danych (bufora, zdjęć) — volume `blog-bot-data` zostaje.  
`docker compose down -v` usuwa wszystko łącznie z danymi — **nie używaj** chyba że chcesz reset.

---

## Użytkowanie

Wejdź na kanał `#blog-input` (lub jak go nazwałeś) i wrzucaj wiadomości — bot zbiera je w persystentnym buforze (`buffer.json`).

| Komenda | Opis |
|---|---|
| `/blog-help` | Lista komend i workflow |
| `/blog-status` | Ile notatek i zdjęć czeka w buforze |
| `/blog-raw` | Podgląd surowych notatek z bufora (bez zdjęć) |
| `/blog-draft` | Generuje podgląd posta przez LLM (nic nie commituje) |
| `/blog-publish` | Commituje **dokładnie ten draft** na branch `drafts` i otwiera PR |
| `/blog-clear` | Czyści bufor bez publikowania |

**Workflow:**
1. Wrzucaj wiadomości i zdjęcia przez kilka dni
2. `/blog-draft` — sprawdź efekt
3. `/blog-publish` — opublikuj (używa wygenerowanego draftu, nie generuje ponownie)

> Nowa wiadomość po `/blog-draft` unieważnia draft — wygeneruj go ponownie przed publishem.

---

## Struktura repo Jekyll (oczekiwana)

```
_posts/
  2024-01-15-tytul-posta.md    ← bot tworzy tutaj
assets/
  images/
    IMG_1234.jpg                ← bot uploaduje tutaj
```

Upewnij się że ścieżka `assets/images/` istnieje w repo (dodaj `.gitkeep` jeśli pusta).

---

## Styl pisania

Bot używa profilu stylu z `blog_context.md` przy każdym generowaniu draftu.  
Odśwież go po dodaniu nowych postów do `_posts/`:

```bash
python learn_style.py
# opcje: --posts-dir ../../_posts --max-posts 15 --dry-run
```

---

## Backend LLM

Domyślnie Claude (Anthropic API). Możesz przełączyć na lokalny Ollama:

```env
LLM_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

## Znane ograniczenia

- Zdjęcia z Discorda są dostępne przez ~24h po usunięciu wiadomości — publishuj przed wyczyszczeniem kanału.
