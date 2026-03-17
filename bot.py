from __future__ import annotations
import os
import logging

from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from db import init_db
from callbacks import callback_handler
from jobs import job_send_reminders, job_morning_digest
from tasks import cmd_add, cmd_list, cmd_all, cmd_week, cmd_done, cmd_delete, cmd_deleteall
from shopping import cmd_buy, cmd_shopping
from settings import cmd_start, cmd_help, cmd_timezone, cmd_lang, cmd_streak
from settings import handle_location, handle_button_text
from roles import cmd_role, cmd_roles

load_dotenv()

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_BUTTON_PATTERN = (
    r"^(📋 Tasks|📋 Задачи|📅 This Week|📅 Неделя"
    r"|🛒 Shopping|🛒 Покупки|🔥 Streak|🔥 Серия|❓ Help|❓ Помощь)$"
)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    init_db()
    logger.info("Database initialized.")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("add",       cmd_add))
    app.add_handler(CommandHandler("list",      cmd_list))
    app.add_handler(CommandHandler("all",       cmd_all))
    app.add_handler(CommandHandler("week",      cmd_week))
    app.add_handler(CommandHandler("done",      cmd_done))
    app.add_handler(CommandHandler("delete",    cmd_delete))
    app.add_handler(CommandHandler("deleteall", cmd_deleteall))
    app.add_handler(CommandHandler("timezone",  cmd_timezone))
    app.add_handler(CommandHandler("lang",      cmd_lang))
    app.add_handler(CommandHandler("streak",    cmd_streak))
    app.add_handler(CommandHandler("buy",       cmd_buy))
    app.add_handler(CommandHandler("shopping",  cmd_shopping))
    app.add_handler(CommandHandler("role",      cmd_role))
    app.add_handler(CommandHandler("roles",     cmd_roles))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(_BUTTON_PATTERN), handle_button_text))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Background jobs
    app.job_queue.run_repeating(job_send_reminders, interval=60, first=10)
    app.job_queue.run_repeating(job_morning_digest, interval=60, first=15)

    logger.info("Bot running…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
