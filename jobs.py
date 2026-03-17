from __future__ import annotations
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import Task, User, get_session
from helpers import render_task
from i18n import t

logger = logging.getLogger(__name__)


async def job_send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    now_utc = datetime.utcnow()
    window = now_utc + timedelta(minutes=2)

    with get_session() as s:
        due_tasks = (
            s.query(Task)
            .filter(
                Task.is_done == False,
                Task.pending_review == False,
                Task.reminder_sent == False,
                Task.due_date != None,
                Task.due_date <= window,
            )
            .all()
        )

        for task in due_tasks:
            target_id = task.assignee_id or task.creator_id
            target_user = s.get(User, target_id)
            lang = target_user.language if target_user else "en"
            mention = (
                f"@{target_user.username}" if (target_user and target_user.username)
                else (target_user.first_name if target_user else "")
            )

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Done", callback_data=f"done:{task.id}"),
                InlineKeyboardButton("⏰ +1h", callback_data=f"snooze1h:{task.id}"),
                InlineKeyboardButton("📅 Tomorrow", callback_data=f"snoozetom:{task.id}"),
            ]])

            sent = False
            try:
                await context.bot.send_message(
                    target_id,
                    t(lang, "reminder_private", title=task.title),
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                sent = True
            except Exception as exc:
                logger.warning("Private reminder failed #%s: %s", task.id, exc)

            is_group_chat = task.chat_id not in (task.creator_id, task.assignee_id or task.creator_id)
            if is_group_chat:
                try:
                    await context.bot.send_message(
                        task.chat_id,
                        t(lang, "reminder_group", mention=mention, title=task.title),
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )
                    sent = True
                except Exception as exc:
                    logger.warning("Group reminder failed #%s: %s", task.id, exc)

            if sent:
                task.reminder_sent = True


async def job_morning_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        users = s.query(User).all()

        for user in users:
            try:
                local_now = datetime.now(ZoneInfo(user.timezone))
                if local_now.hour != 8 or local_now.minute > 1:
                    continue

                local_date_str = local_now.strftime("%Y-%m-%d")
                if user.digest_sent_date == local_date_str:
                    continue

                today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                start_utc = today_start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                end_utc = today_end.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

                tasks = (
                    s.query(Task)
                    .filter(
                        or_(Task.creator_id == user.telegram_id, Task.assignee_id == user.telegram_id),
                        Task.is_done == False,
                        Task.due_date != None,
                        or_(
                            and_(Task.due_date >= start_utc, Task.due_date < end_utc),
                            Task.due_date < start_utc,  # overdue
                        ),
                    )
                    .order_by(Task.due_date.asc())
                    .all()
                )

                if tasks:
                    task_lines = "\n".join(render_task(s, task, user.timezone) for task in tasks)
                    msg = t(user.language, "digest", name=user.first_name, tasks=task_lines)
                else:
                    msg = t(user.language, "digest_empty", name=user.first_name)

                await context.bot.send_message(user.telegram_id, msg, parse_mode="Markdown")
                user.digest_sent_date = local_date_str

            except Exception as exc:
                logger.warning("Morning digest failed user %s: %s", user.telegram_id, exc)
