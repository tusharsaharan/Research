import os
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gateway.service import Gateway
from gateway.config import Settings
from gateway.schemas import ChatCompletionRequest, ChatMessage
from gateway.modules.m6_telegram.db import LogDB

token = os.environ.get("GATEWAY_TELEGRAM_TOKEN", "")
if not token:
    sys.exit("GATEWAY_TELEGRAM_TOKEN is not set (put it in backend/.env, never in code).")
groq_key = os.environ.get("GROQ_API_KEY", "") or os.environ.get("GATEWAY_CHEAP__API_KEY", "")

settings = Settings()
gw = Gateway(settings)
db = LogDB(Path(__file__).parent / "data" / "pilot.sqlite")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Namaste! 🙏 Welcome to the **Hinglish Gateway AI**.\n\n"
        "Main aapke Hindi-English (Hinglish) questions ko intelligently compress aur route karke answer karta hoon.\n\n"
        "👉 Apna koi bhi sawal bhejo! (e.g. 'binary search samjha do', 'machine learning kya hai')"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def send_message_safe(update: Update, text: str):
    max_len = 4000
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)] or [text]
    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            # Fallback to plain text if Telegram fails to parse unclosed entities like *, _, `
            await update.message.reply_text(chunk)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "anonymous"

    # Show typing indicator safely
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    except Exception:
        pass

    try:
        req = ChatCompletionRequest(
            model="cascade",
            messages=[ChatMessage(role="user", content=user_text)],
            user=user_id
        )
        resp = await gw.handle(req)
        meta = resp.x_gateway

        reply_content = resp.choices[0].message.content or ""
        if "[mock:" in reply_content:
            reply_content = (
                f"✅ Gateway processed your query!\n\n"
                f"Aapka prompt successfully compress aur analyze ho gaya hai.\n\n"
                f"📌 Telemetry Insights:\n"
                f"• Query: {user_text}\n"
                f"• Difficulty Score: {meta.difficulty_score}\n"
                f"• Conformal Bound: {meta.conformal_threshold}\n"
                f"• Routed to: {meta.model_routed} ({meta.tier} tier)\n"
                f"• Reasoning Budget: {meta.reasoning_budget} thinking tokens"
            )

        savings_tokens = meta.original_tokens - meta.compressed_tokens
        if savings_tokens > 0 and meta.original_tokens > 0:
            savings_pct = round((savings_tokens / meta.original_tokens) * 100, 1)
            comp_info = f"tokens {meta.original_tokens} → {meta.compressed_tokens} (-{savings_pct}%)"
        else:
            comp_info = f"tokens {meta.original_tokens} → {meta.compressed_tokens}"

        footer = (
            f"\n\n───────────────\n"
            f"📊 {comp_info} | routed: {meta.model_routed} ({meta.tier})"
        )
        await send_message_safe(update, reply_content + footer)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Gateway error: {str(e)}")

def main():
    print(f"==================================================")
    print(f"🚀 Hinglish Gateway Telegram Bot is STARTING...")
    print(f"🤖 Bot Username: @TusharGatewayBot")
    print(f"🔗 Bot Link: https://t.me/TusharGatewayBot")
    print(f"⚙️ Mode: {'LIVE (Connected to Groq)' if not settings.dry_run else 'DRY-RUN (Mock/Telemetry active)'}")
    print(f"📁 Database: data/pilot.sqlite")
    print(f"==================================================")
    print(f"Listening for messages from Telegram worldwide... (Press Ctrl+C to stop)")

    from telegram.request import HTTPXRequest

    t_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )
    app = ApplicationBuilder().token(token).request(t_request).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(bootstrap_retries=10, timeout=20)

if __name__ == "__main__":
    main()
