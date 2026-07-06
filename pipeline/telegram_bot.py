"""
pipeline/telegram_bot.py — Telegram interface for etsy-pipeline.

Commands:
  /generate      — generate + describe 1 collection, send preview
  /generate 3    — generate N collections
  /publish       — publish all unpublished pairs to Etsy drafts
  /status        — show published/total counts
  /help          — list commands

Run from project root: python3 pipeline/telegram_bot.py
"""
import json
import logging
import os
import sys
import traceback
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.run_all import generate_and_describe, publish_unpublished
from pipeline.describe.describe import collect_used_names

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("TELEGRAM_OWNER_ID", "0"))

if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN missing in .env")
    sys.exit(1)


def _only_owner(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        logging.info(f"Message from user ID: {uid}")
        if OWNER_ID and uid != OWNER_ID:
            await update.message.reply_text("Not authorized.")
            return
        await func(update, context)
    return wrapper


def _status_text() -> str:
    products = Path("products")
    total = published = unpublished = 0
    pub_cats = []

    for desc in sorted(products.rglob("description.json")):
        total += 1
        pub = desc.parent / "published.json"
        if pub.exists():
            published += 1
            name = json.loads(pub.read_text()).get("cat_name", "?")
            pub_cats.append(name)
        else:
            unpublished += 1

    lines = [f"{total} par totalt — {published} på Etsy, {unpublished} venter"]
    if pub_cats:
        lines.append(f"Publisert: {', '.join(pub_cats[-9:])}")
    used = collect_used_names()
    lines.append(f"{len(used)} unike kattunger laget")
    return "\n".join(lines)


@_only_owner
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "etsy-pipeline:\n\n"
        "/generate — lag 1 collection (bilder + beskrivelse)\n"
        "/generate 3 — lag N collections\n"
        "/publish — send ventende collections til Etsy drafts\n"
        "/status — vis oversikt\n"
        "/help — denne meldingen"
    )


@_only_owner
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_status_text())


@_only_owner
async def cmd_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = 1
    if context.args:
        try:
            count = max(1, min(int(context.args[0]), 10))
        except ValueError:
            await update.message.reply_text("Bruk: /generate [antall, maks 10]")
            return

    await update.message.reply_text(f"Genererer {count} collection(s)...")

    try:
        collection_dirs = generate_and_describe(count)

        lines = []
        for col_dir in collection_dirs:
            lines.append(f"\n{col_dir.name}:")
            for pair_dir in sorted(col_dir.glob("pair-*")):
                desc_file = pair_dir / "description.json"
                if desc_file.exists():
                    meta = json.loads(desc_file.read_text())
                    lines.append(f"  {meta.get('cat_name', '?')} — {meta['title'][:45]}...")

        preview = "\n".join(lines)
        await update.message.reply_text(
            f"Ferdig!\n{preview}\n\nSend /publish for å laste opp til Etsy."
        )
    except Exception:
        await update.message.reply_text(f"Feil:\n{traceback.format_exc()[-500:]}")


@_only_owner
async def cmd_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Publiserer til Etsy drafts...")

    try:
        results = publish_unpublished()
        if not results:
            await update.message.reply_text("Ingen upubliserte collections funnet.")
            return

        lines = []
        for r in results:
            lines.append(f"{r.get('cat_name', '?')} → {r['url']}")

        await update.message.reply_text(
            f"{len(results)} listing(s) lastet opp som draft:\n\n" + "\n".join(lines)
        )
    except Exception:
        await update.message.reply_text(f"Feil:\n{traceback.format_exc()[-500:]}")


def main():
    if not OWNER_ID:
        print(
            "ADVARSEL: TELEGRAM_OWNER_ID ikke satt.\n"
            "Send /start til @userinfobot og legg TELEGRAM_OWNER_ID=<id> i .env\n"
        )

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("start",    cmd_help))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("publish",  cmd_publish))

    print("etsy-pipeline er klar. Trykk Ctrl+C for å stoppe.")
    app.run_polling()


if __name__ == "__main__":
    main()
