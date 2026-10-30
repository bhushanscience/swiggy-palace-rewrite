import asyncio
import logging
import os

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
)

import db
from config import BOT_TOKEN, PORT
from handlers import (
    start, admin_command, setpaymentinfo_command, setcharge_command, callback_router,
    photo_router, text_router, cancel, help_command
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("swiggy_palace")

async def health(_request):
    return JSONResponse({"status": "ok", "service": "swiggy-palace"})

async def home(_request):
    return PlainTextResponse("Swiggy Palace bot is running.\nHealth: /health")

web_app = Starlette(routes=[
    Route("/", home),
    Route("/health", health),
])

async def run():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it in Render environment variables.")

    await db.init_db()
    telegram_app = Application.builder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("admin", admin_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("cancel", cancel))
    telegram_app.add_handler(CommandHandler("setpaymentinfo", setpaymentinfo_command))
    telegram_app.add_handler(CommandHandler("setcharge", setcharge_command))
    telegram_app.add_handler(CallbackQueryHandler(callback_router))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    async with telegram_app:
        await telegram_app.start()
        if telegram_app.updater is None:
            raise RuntimeError("Telegram updater is unavailable.")
        await telegram_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        log.info("Swiggy Palace polling started.")

        server = uvicorn.Server(
            uvicorn.Config(web_app, host="0.0.0.0", port=PORT, log_level="info")
        )
        try:
            await server.serve()
        finally:
            if telegram_app.updater.running:
                await telegram_app.updater.stop()
            await telegram_app.stop()
            log.info("Swiggy Palace stopped.")

if __name__ == "__main__":
    asyncio.run(run())
