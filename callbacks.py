from __future__ import annotations
import logging
from datetime import timedelta

from telegram import Update
from telegram.ext import ContextTypes

from db import ShoppingItem, Task, User, get_session
from helpers import upsert_user, update_streak
from i18n import t
from shopping import shopping_ui

logger = logging.getLogger(__name__)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    action, payload = query.data.split(":", 1)

    if action == "shop_toggle":
        await _shop_toggle(query, int(payload))
    elif action == "shop_clear":
        await _shop_clear(query, context, int(payload))
    elif action == "verify":
        sub_action, task_id_str = payload.split(":", 1)
        await _verify(query, context, sub_action, int(task_id_str))
    else:
        await _task_action(query, action, int(payload))


# ── Shopping ──────────────────────────────────────────────────────────────────

async def _shop_toggle(query, item_id: int) -> None:
    with get_session() as s:
        item = s.get(ShoppingItem, item_id)
        if not item:
            return
        item.is_checked = not item.is_checked
        chat_id = item.chat_id
        lang = _lang_from_query(s, query)
        items = (
            s.query(ShoppingItem)
            .filter_by(chat_id=chat_id)
            .order_by(ShoppingItem.is_checked.asc(), ShoppingItem.created_at.asc())
            .all()
        )
        text, keyboard = shopping_ui(items, lang)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def _shop_clear(query, context, chat_id: int) -> None:
    with get_session() as s:
        lang = _lang_from_query(s, query)
        s.query(ShoppingItem).filter_by(chat_id=chat_id, is_checked=True).delete()
        items = (
            s.query(ShoppingItem)
            .filter_by(chat_id=chat_id)
            .order_by(ShoppingItem.created_at.asc())
            .all()
        )
        text, keyboard = shopping_ui(items, lang)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ── Verification ──────────────────────────────────────────────────────────────

async def _verify(query, context, sub_action: str, task_id: int) -> None:
    with get_session() as s:
        task = s.get(Task, task_id)
        if not task:
            await query.edit_message_text("Task not found.")
            return
        assignee_id = task.assignee_id or task.creator_id
        assignee = s.get(User, assignee_id)
        lang = assignee.language if assignee else "en"
        task_title = task.title

        if sub_action == "approve":
            task.is_done = True
            task.pending_review = False
            if assignee:
                update_streak(assignee, assignee.timezone)
            await query.edit_message_text(t(lang, "verify_approved", id=task_id))
            await _notify(context, assignee_id, t(lang, "verify_approved_notify", title=task_title))

        elif sub_action == "reject":
            task.pending_review = False
            await query.edit_message_text(t(lang, "verify_rejected_admin", id=task_id))
            await _notify(context, assignee_id, t(lang, "verify_rejected_notify", title=task_title))


# ── Reminder inline buttons ───────────────────────────────────────────────────

async def _task_action(query, action: str, task_id: int) -> None:
    with get_session() as s:
        task = s.get(Task, task_id)
        if not task:
            await query.edit_message_text("Task not found.")
            return

        if action == "done":
            task.is_done = True
            if query.from_user:
                u = upsert_user(s, query.from_user)
                update_streak(u, u.timezone)
            await query.edit_message_text(f"✅ Done: {task.title}")

        elif action == "snooze1h":
            if task.due_date:
                task.due_date += timedelta(hours=1)
            task.reminder_sent = False
            await query.edit_message_text(f"⏰ Snoozed +1h: {task.title}")

        elif action == "snoozetom":
            if task.due_date:
                task.due_date += timedelta(days=1)
            task.reminder_sent = False
            await query.edit_message_text(f"📅 Snoozed to tomorrow: {task.title}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _lang_from_query(session, query) -> str:
    if query.from_user:
        user = session.get(User, query.from_user.id)
        if user:
            return user.language
    return "en"


async def _notify(context, user_id: int, text: str) -> None:
    try:
        await context.bot.send_message(user_id, text, parse_mode="Markdown")
    except Exception as exc:
        logger.warning("Could not notify user %s: %s", user_id, exc)
