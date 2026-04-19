import os
from dotenv import load_dotenv

load_dotenv()
import discord
from discord import app_commands
from github_client import commit_post
import buffer as buf
import image_cache
import draft_cache

LLM_BACKEND = os.getenv("LLM_BACKEND", "claude").lower()

if LLM_BACKEND == "ollama":
    from ollama_client import generate_draft
    print(f"LLM backend: ollama ({os.getenv('OLLAMA_MODEL', 'llama3.2')} @ {os.getenv('OLLAMA_HOST', 'http://localhost:11434')})")
else:
    from claude_client import generate_draft
    print(f"LLM backend: claude ({os.getenv('CLAUDE_MODEL', 'claude-opus-4-5')})")

BLOG_CHANNEL_ID = int(os.getenv("BLOG_CHANNEL_ID"))


class BlogBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands zsynchronizowane.")

    async def on_ready(self):
        entries = buf.load()
        print(f"Bot gotowy: {self.user} (bufor: {len(entries)} wpisów)")


client = BlogBot()


# ── Listener na zwykłe wiadomości (bufor notatek) ─────────────────────────────

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != BLOG_CHANNEL_ID:
        return
    if message.content.startswith("/"):
        return

    entry = {
        "author": str(message.author.display_name),
        "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M"),
        "text": message.content.strip(),
        "images": []
    }
    for att in message.attachments:
        if any(att.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
            try:
                await image_cache.fetch_and_save(att.url, att.filename)
                entry["images"].append({"filename": att.filename, "url": att.url})
                await message.add_reaction("🖼️")
            except Exception as e:
                await message.add_reaction("⚠️")
                print(f"Nie udało się pobrać zdjęcia {att.filename}: {e}")

    buf.append(entry)
    draft_cache.clear()  # nowa notatka unieważnia poprzedni draft
    await message.add_reaction("✅")


# ── Slash commands ─────────────────────────────────────────────────────────────

@client.tree.command(name="blog-help", description="Pokazuje dostepne komendy i workflow")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Blog Bot — dostepne komendy**\n\n"
        "`/blog-help` — ta wiadomosc\n"
        "`/blog-raw` — podglad surowych notatek z bufora (bez zdjec)\n"
        "`/blog-status` — ile notatek i zdjec czeka w buforze\n"
        "`/blog-draft` — generuje podglad posta (nic nie commituje)\n"
        "`/blog-publish` — commituje draft z podgladu na branch `drafts` i otwiera PR\n"
        "`/blog-clear` — czysci bufor bez publikowania\n\n"
        "**Workflow:**\n"
        "1. Wrzucaj wiadomosci i zdjecia na ten kanal — bot zbiera je w buforze\n"
        "2. `/blog-draft` — sprawdz jak bedzie wygladal post\n"
        "3. `/blog-publish` — opublikuj dokladnie ten draft (bez ponownego generowania)\n\n"
        "> Nowa wiadomosc po `/blog-draft` uniewa\u017cnia draft — trzeba go wygenerowac ponownie.\n\n"
        "**Styl pisania:**\n"
        "Profil stylu trzymany jest w `blog_context.md`. Odswiezysz go skryptem:\n"
        "`python learn_style.py` (analizuje posty z `_posts/` i nadpisuje profil)",
        ephemeral=True,
    )


@client.tree.command(name="blog-draft", description="Generuje draft posta z zebranych notatek (podglad, nic nie commituje)")
async def slash_draft(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await _handle_draft(interaction, publish=False)


@client.tree.command(name="blog-publish", description="Commituje post i zdjecia do GitHub (branch drafts) i otwiera PR")
async def slash_publish(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await _handle_draft(interaction, publish=True)


@client.tree.command(name="blog-status", description="Ile notatek i zdjec czeka w buforze")
async def slash_status(interaction: discord.Interaction):
    entries = buf.load()
    if not entries:
        await interaction.response.send_message("Bufor pusty. Wrzuc cos przed draftem.")
        return
    count_imgs = sum(len(e["images"]) for e in entries)
    first_ts = entries[0]["timestamp"]
    last_ts = entries[-1]["timestamp"]
    await interaction.response.send_message(
        f"📦 W buforze: **{len(entries)}** wpisow, **{count_imgs}** zdjec.\n"
        f"🗓️ Zakres: {first_ts} → {last_ts}\n"
        f"Uzyj `/blog-draft` zeby podejrzec lub `/blog-publish` zeby commitowac."
    )


@client.tree.command(name="blog-clear", description="Czysci bufor notatek bez publikowania")
async def slash_clear(interaction: discord.Interaction):
    entries = buf.load()
    count = len(entries)
    imgs = image_cache.clear_all()
    buf.clear()
    draft_cache.clear()
    await interaction.response.send_message(f"🗑️ Bufor wyczyszczony ({count} wpisów, {imgs} zdjęć).")


# ── Wspólna logika draft/publish ───────────────────────────────────────────────

async def _handle_draft(interaction: discord.Interaction, publish: bool):
    entries = buf.load()
    if not entries:
        await interaction.followup.send("Bufor pusty — najpierw wrzuc jakies notatki.")
        return

    cached = draft_cache.load() if publish else None
    if cached:
        md_content, slug, images = cached
    else:
        if publish:
            await interaction.followup.send(
                "⚠️ Brak zapisanego draftu — generowalem od nowa. "
                "Nastepnym razem uzyj `/blog-draft` przed publikowaniem."
            )
        try:
            md_content, slug, images = await generate_draft(entries)
        except Exception as e:
            await interaction.followup.send(f"❌ Blad LLM ({LLM_BACKEND}): {e}")
            return
        if not publish:
            draft_cache.save(md_content, slug, images)

    if publish:
        try:
            commit_url, pr_url = await commit_post(md_content, slug, images)
            buf.clear()
            image_cache.clear_all()
            await interaction.followup.send(
                f"✅ Scommitowano na branch `drafts`!\n"
                f"📝 PR do review: {pr_url}\n"
                f"🔗 Commit: {commit_url}\n\n"
                f"Bufor wyczyszczony."
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Blad GitHub API: {e}")
    else:
        fname = f"{slug}.md"

        try:
            fpath = f"/tmp/{fname}"
            # check if /tmp exists
            if not os.path.exists("/tmp"):
                fpath = f"{fname}"
        except FileNotFoundError:
            fpath = f"{fname}"
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(md_content)
        await interaction.followup.send(
            "📝 Draft (podglad, nic nie zapisano):",
            file=discord.File(fpath)
        )
        if images:
            await interaction.followup.send(
                f"🖼️ Zdjecia ({len(images)} szt.) zostana scommitowane przy `/blog-publish` pod:\n"
                + "\n".join(f"  `assets/images/{img['filename']}`" for img in images)
            )


client.run(os.getenv("DISCORD_TOKEN"))
