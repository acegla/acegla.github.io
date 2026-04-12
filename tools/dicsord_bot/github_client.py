import base64
import os
import aiohttp
from datetime import date
import image_cache

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # "username/blog-repo"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_DRAFT_BRANCH = os.getenv("GITHUB_DRAFT_BRANCH", "drafts")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

BASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents"


async def get_file_sha(session: aiohttp.ClientSession, path: str, branch: str = None) -> str | None:
    """Pobiera SHA istniejącego pliku (potrzebne do aktualizacji)."""
    async with session.get(
        f"{BASE_URL}/{path}",
        headers=HEADERS,
        params={"ref": branch or GITHUB_DRAFT_BRANCH}
    ) as r:
        if r.status == 200:
            data = await r.json()
            return data.get("sha")
        return None


async def put_file(
    session: aiohttp.ClientSession,
    path: str,
    content_bytes: bytes,
    commit_message: str,
    sha: str | None = None,
    branch: str = None
) -> dict:
    """Commituje plik do GitHub. Tworzy lub aktualizuje."""
    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_bytes).decode(),
        "branch": branch or GITHUB_DRAFT_BRANCH
    }
    if sha:
        payload["sha"] = sha

    async with session.put(
        f"{BASE_URL}/{path}",
        headers=HEADERS,
        json=payload
    ) as r:
        if r.status not in (200, 201):
            text = await r.text()
            raise Exception(f"GitHub PUT failed ({r.status}): {text}")
        return await r.json()


async def download_discord_image(session: aiohttp.ClientSession, url: str) -> bytes:
    """Pobiera obrazek z CDN Discorda."""
    async with session.get(url) as r:
        if r.status != 200:
            raise Exception(f"Nie mogę pobrać zdjęcia z Discorda: {url} ({r.status})")
        return await r.read()


async def ensure_draft_branch_exists(session: aiohttp.ClientSession) -> None:
    """
    Tworzy branch GITHUB_DRAFT_BRANCH jeśli nie istnieje.
    Bazuje na HEAD brancha GITHUB_BRANCH (main/master).
    """
    # Sprawdź czy draft branch już istnieje
    async with session.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/{GITHUB_DRAFT_BRANCH}",
        headers=HEADERS
    ) as r:
        if r.status == 200:
            return  # już istnieje

    # Pobierz SHA HEAD brancha bazowego
    async with session.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/{GITHUB_BRANCH}",
        headers=HEADERS
    ) as r:
        if r.status != 200:
            raise Exception(f"Nie mogę pobrać SHA brancha {GITHUB_BRANCH}: {await r.text()}")
        data = await r.json()
        base_sha = data["object"]["sha"]

    # Utwórz branch
    async with session.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs",
        headers=HEADERS,
        json={"ref": f"refs/heads/{GITHUB_DRAFT_BRANCH}", "sha": base_sha}
    ) as r:
        if r.status not in (200, 201):
            raise Exception(f"Nie mogę utworzyć brancha {GITHUB_DRAFT_BRANCH}: {await r.text()}")
        print(f"  ✓ Utworzono branch '{GITHUB_DRAFT_BRANCH}' z {GITHUB_BRANCH}")


async def commit_post(md_content: str, slug: str, images: list) -> str:
    """
    Commituje post MD + wszystkie zdjęcia do brancha GITHUB_DRAFT_BRANCH.
    Branch jest tworzony automatycznie jeśli nie istnieje.
    Zwraca URL commita i URL PR.
    """
    today = date.today().isoformat()
    post_path = f"_posts/{slug}.md"
    commit_url = None

    async with aiohttp.ClientSession() as session:

        # 0. Upewnij się że draft branch istnieje
        await ensure_draft_branch_exists(session)

        # 1. Commituj zdjęcia
        for img in images:
            img_path = f"assets/images/{img['filename']}"
            print(f"Uploading {img_path}...")
            try:
                # Preferuj lokalny cache, fallback na Discord CDN
                if image_cache.is_cached(img["filename"]):
                    img_bytes = image_cache.read(img["filename"])
                else:
                    print(f"  ⚠ Brak w cache, próbuję Discord CDN (może być wygasłe)...")
                    img_bytes = await download_discord_image(session, img["url"])

                sha = await get_file_sha(session, img_path)
                await put_file(
                    session,
                    img_path,
                    img_bytes,
                    f"blog: add image {img['filename']} for {today}",
                    sha,
                    branch=GITHUB_DRAFT_BRANCH
                )
                print(f"  ✓ {img_path}")
            except Exception as e:
                print(f"  ✗ {img_path}: {e}")

        # 2. Commituj post MD
        print(f"Uploading {post_path}...")
        sha = await get_file_sha(session, post_path)
        result = await put_file(
            session,
            post_path,
            md_content.encode("utf-8"),
            f"blog: add post {slug}",
            sha,
            branch=GITHUB_DRAFT_BRANCH
        )
        commit_url = result["commit"]["html_url"]
        print(f"  ✓ {post_path}")

        # 3. Utwórz PR jeśli nie istnieje dla tego brancha
        pr_url = await ensure_pull_request(session, slug)

    return commit_url, pr_url


async def ensure_pull_request(session: aiohttp.ClientSession, slug: str) -> str:
    """
    Tworzy PR z GITHUB_DRAFT_BRANCH → GITHUB_BRANCH jeśli jeszcze nie ma otwartego.
    Zwraca URL PR.
    """
    # Sprawdź czy jest już otwarty PR dla tego brancha
    async with session.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers=HEADERS,
        params={"state": "open", "head": f"{GITHUB_REPO.split('/')[0]}:{GITHUB_DRAFT_BRANCH}"}
    ) as r:
        pulls = await r.json()
        if pulls:
            return pulls[0]["html_url"]  # już istnieje

    # Utwórz nowy PR
    async with session.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers=HEADERS,
        json={
            "title": f"Blog draft: {slug}",
            "head": GITHUB_DRAFT_BRANCH,
            "base": GITHUB_BRANCH,
            "body": "Draft wygenerowany przez blog bota. Przejrzyj i zmerguj gdy gotowe."
        }
    ) as r:
        if r.status in (200, 201):
            data = await r.json()
            return data["html_url"]
        # PR mógł już istnieć (race condition) — nie rzucaj błędu
        return f"https://github.com/{GITHUB_REPO}/pulls"
