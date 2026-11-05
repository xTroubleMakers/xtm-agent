import os
import asyncio
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4.1-flash:free")
FALLBACK_MODELS = [
    m.strip() for m in os.getenv("OPENROUTER_FALLBACK_MODELS", "").split(",") if m.strip()
]
MODEL = DEFAULT_MODEL  # model aktif, dipakai oleh /start dan /model

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "Kamu adalah asisten AI yang membantu, akurat, dan ringkas.")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("agent")

# Riwayat percakapan per chat (in-memory). Untuk produksi, ganti ke Redis/SQLite.
history: dict[int, list[dict]] = {}


async def _call_model(client: httpx.AsyncClient, model: str, messages: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("SITE_URL", "https://github.com"),
        "X-Title": os.getenv("SITE_NAME", "xtm-agent"),
    }
    payload = {"model": model, "messages": messages, "temperature": 0.7}
    resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)

    # free tier sering kena rate limit -> tunggu lalu coba sekali lagi
    if resp.status_code == 429:
        await asyncio.sleep(3)
        resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)

    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def ask_openrouter(messages: list[dict]) -> str:
    chain = [MODEL] + [m for m in FALLBACK_MODELS if m != MODEL]
    last_err: Exception | None = None

    async with httpx.AsyncClient(timeout=90) as client:
        for model in chain:
            try:
                return await _call_model(client, model, messages)
            except httpx.HTTPStatusError as e:
                last_err = e
                log.warning("Model %s gagal (HTTP %s), coba berikutnya", model, e.response.status_code)
            except Exception as e:  # timeout, koneksi, dll.
                last_err = e
                log.warning("Model %s error: %s", model, e)

    raise last_err or RuntimeError("Semua model gagal")


def chunk_text(text: str, size: int = 4000) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def send_long(update: Update, text: str) -> None:
    for part in chunk_text(text):
        await update.message.reply_text(part)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history.pop(update.effective_chat.id, None)
    await update.message.reply_text(
        "Halo! Saya agent AI berbasis OpenRouter.\n"
        f"Model aktif: `{MODEL}`\n\n"
        "Kirim pertanyaan apa saja.\n"
        "/reset - hapus riwayat percakapan\n"
        "/model - lihat model aktif\n"
        "/model2 <id> - ganti model",
        parse_mode="Markdown",
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history.pop(update.effective_chat.id, None)
    await update.message.reply_text("Riwayat percakapan dihapus.")


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Model aktif: `{MODEL}`", parse_mode="Markdown")


async def cmd_setmodel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global MODEL
    if not context.args:
        await update.message.reply_text("Format: /model2 deepseek/deepseek-v4.1-flash:free")
        return
    MODEL = context.args[0].strip()
    await update.message.reply_text(f"Model diganti ke: `{MODEL}`", parse_mode="Markdown")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text

    msgs = history.setdefault(chat_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    msgs.append({"role": "user", "content": user_text})

    # batasi panjang riwayat
    if len(msgs) > MAX_HISTORY + 1:
        msgs[:] = [msgs[0]] + msgs[-MAX_HISTORY:]

    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

    try:
        reply = await ask_openrouter(msgs)
    except httpx.HTTPStatusError as e:
        log.error("OpenRouter HTTP %s: %s", e.response.status_code, e.response.text[:500])
        msgs.pop()
        await update.message.reply_text("Terjadi kesalahan pada penyedia model. Coba lagi sebentar.")
        return
    except Exception:
        log.exception("OpenRouter call failed")
        msgs.pop()
        await update.message.reply_text("Maaf, gagal menghubungi model AI.")
        return

    msgs.append({"role": "assistant", "content": reply})
    await send_long(update, reply)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Unhandled error", exc_info=context.error)


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("model2", cmd_setmodel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)
    log.info("Bot berjalan dengan model %s", MODEL)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
