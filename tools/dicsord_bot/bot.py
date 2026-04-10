import discord
from discord import app_commands
import os
from dotenv import load_dotenv
from claude_client import generate_draft
from github_client import commit_post

load_dotenv()

BLOG_CHANNEL_ID = int(os.getenv("BLOG_CHANNEL_ID"))

pending_messages = []


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
        print(f"Bot gotowy: {self.user}")


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
            entry["images"].append({"filename": att.filename, "url": att.url})

    pending_messages.append(entry)
    await message.add_reaction("✅")


# ── Slash commands ─────────────────────────────────────────────────────────────

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
    if not pending_messages:
        await interaction.response.send_message("Bufor pusty. Wrzuc cos przed draftem.")
        return
    count_imgs = sum(len(e["images"]) for e in pending_messages)
    await interaction.response.send_message(
        f"📦 W buforze: **{len(pending_messages)}** wpisow, **{count_imgs}** zdjec.\n"
        f"Uzyj `/blog-draft` zeby podejrzec lub `/blog-publish` zeby commitowac."
    )


@client.tree.command(name="blog-clear", description="Czysci bufor notatek bez publikowania")
async def slash_clear(interaction: discord.Interaction):
    pending_messages.clear()
    await interaction.response.send_message("🗑️ Bufor wyczyszczony.")


# ── Wspólna logika draft/publish ───────────────────────────────────────────────

async def _handle_draft(interaction: discord.Interaction, publish: bool):
    if not pending_messages:
        await interaction.followup.send("Bufor pusty — najpierw wrzuc jakies notatki.")
        return

    try:
        md_content, slug, images = await generate_draft(pending_messages)
    except Exception as e:
        await interaction.followup.send(f"❌ Blad Claude API: {e}")
        return

    if publish:
        try:
            commit_url, pr_url = await commit_post(md_content, slug, images)
            pending_messages.clear()
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
        fpath = f"/tmp/{fname}"
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
