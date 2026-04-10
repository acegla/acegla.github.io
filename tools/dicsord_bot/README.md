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
docker compose up -d
docker compose logs -f  # sprawdź czy działa
```

**Lokalnie (dev):**
```bash
pip install -r requirements.txt
python bot.py
```

---

## Użytkowanie

Wejdź na kanał `#blog-input` (lub jak go nazwałeś):

```
# Wrzucaj notatki przez kilka dni:
Dziś byłem w górach, widoki niesamowite. Spotkaliśmy sarny przy szlaku.
[+ załącz zdjęcia jako attachment]

Wieczorem przy ognisku — rozmowy o sensie życia i o tym dlaczego zawsze
kończy się kiełbasa zanim skończy się chleb.

# Podgląd draftu (nic nie commituje):
!blog draft

# Commit do GitHub:
!blog publish

# Ile zebrałeś:
!blog status

# Reset bufora:
!blog clear
```

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

## Dostosowanie promptu

Edytuj `SYSTEM_PROMPT` w `claude_client.py` — możesz wkleić tam przykładowe posty
ze swojego bloga jako few-shot, żeby Claude dopasował styl.

---

## Znane ograniczenia

- Bufor jest **w pamięci** — restart bota czyści zebrane notatki przed publishem.
  Rozwiązanie: użyj `!blog draft` jako backup przed restartem, albo dodaj SQLite.
- Zdjęcia z Discorda są dostępne przez ~24h po usunięciu wiadomości — publishuj przed wyczyszczeniem kanału.
