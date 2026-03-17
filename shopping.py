from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import ShoppingItem, get_session
from helpers import upsert_user
from i18n import t


def shopping_ui(items: list, lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    if not items:
        return t(lang, "shopping_empty"), None
    lines = [t(lang, "shopping_hdr")]
    buttons = []
    for item in items:
        icon = "✅" if item.is_checked else "🔲"
        lines.append(f"{icon} {item.text}")
        buttons.append([InlineKeyboardButton(
            f"{icon} {item.text}", callback_data=f"shop_toggle:{item.id}"
        )])
    buttons.append([InlineKeyboardButton(
        t(lang, "shop_clear_btn"), callback_data=f"shop_clear:{items[0].chat_id}"
    )])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        lang = upsert_user(s, update.effective_user).language

    if not context.args:
        await update.message.reply_text(t(lang, "buy_usage"))
        return

    item_text = " ".join(context.args)
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        s.add(ShoppingItem(
            chat_id=update.effective_chat.id,
            text=item_text,
            added_by=user.telegram_id,
        ))

    await update.message.reply_text(t(lang, "buy_added", item=item_text), parse_mode="Markdown")


async def cmd_shopping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        items = (
            s.query(ShoppingItem)
            .filter_by(chat_id=chat_id)
            .order_by(ShoppingItem.is_checked.asc(), ShoppingItem.created_at.asc())
            .all()
        )
        text, keyboard = shopping_ui(items, lang)

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
