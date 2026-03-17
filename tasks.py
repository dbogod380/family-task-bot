from __future__ import annotations
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import Task, User, get_session
from helpers import upsert_user, render_task, next_recurrence, update_streak
from i18n import t, day_label
from nlp import parse_task
from roles import get_role, get_admin_ids, is_group
from settings import maybe_prompt_timezone

logger = logging.getLogger(__name__)


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("/add dentist tomorrow 3pm")
        return

    if is_group(update):
        role = await get_role(context, update.effective_chat.id, update.effective_user.id)
        if role == "kid":
            with get_session() as s:
                lang = upsert_user(s, update.effective_user).language
            await update.message.reply_text(t(lang, "kid_no_create"))
            return

    task_text = " ".join(context.args)
    status_msg = await update.message.reply_text("🤔")

    # Reply-to-assign: replying to someone assigns the task to them
    reply_assignee_id = None
    replied_msg = update.message.reply_to_message
    if replied_msg and replied_msg.from_user and not replied_msg.from_user.is_bot:
        with get_session() as s:
            reply_assignee_id = upsert_user(s, replied_msg.from_user).telegram_id

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang, tz = user.language, user.timezone

        try:
            parsed = parse_task(task_text, tz)
        except Exception as exc:
            logger.warning("parse_task failed: %s", exc)
            parsed = {
                "title": task_text, "due_date": None,
                "assignee_username": None, "is_recurring": False, "recur_interval": None,
            }

        assignee_id = reply_assignee_id
        if not assignee_id and parsed.get("assignee_username"):
            row = s.query(User).filter_by(username=parsed["assignee_username"]).first()
            if row:
                assignee_id = row.telegram_id

        due_utc = None
        if parsed.get("due_date"):
            try:
                dt = datetime.fromisoformat(parsed["due_date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo(tz))
                due_utc = dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            except Exception as exc:
                logger.warning("Bad due_date %r: %s", parsed["due_date"], exc)

        task = Task(
            creator_id=user.telegram_id,
            assignee_id=assignee_id,
            chat_id=update.effective_chat.id,
            title=parsed["title"],
            due_date=due_utc,
            is_recurring=bool(parsed.get("is_recurring")),
            recur_interval=parsed.get("recur_interval"),
        )
        s.add(task)
        s.flush()

        line = render_task(s, task, tz)
        if reply_assignee_id:
            line += t(lang, "reply_assigned")
        notify_id = assignee_id if assignee_id != user.telegram_id else None
        task_id = task.id

    await status_msg.edit_text(t(lang, "task_added", task=line), parse_mode="Markdown")
    await maybe_prompt_timezone(update, lang, tz)

    if notify_id:
        with get_session() as s:
            assignee = s.get(User, notify_id)
            task_obj = s.get(Task, task_id)
            if assignee and task_obj:
                a_line = render_task(s, task_obj, assignee.timezone)
        creator_name = update.effective_user.username or update.effective_user.first_name
        try:
            await context.bot.send_message(
                notify_id,
                t(assignee.language, "assigned_notify", creator=creator_name, task=a_line),
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.warning("Could not notify assignee %s: %s", notify_id, exc)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        q = s.query(Task).filter(
            or_(Task.creator_id == user.telegram_id, Task.assignee_id == user.telegram_id),
            Task.is_done == False,
        )
        if is_group(update):
            q = q.filter(Task.chat_id == update.effective_chat.id)
        tasks = q.order_by(Task.due_date.asc().nullslast()).all()
        if not tasks:
            await update.message.reply_text(t(user.language, "no_pending"))
            return
        lines = [t(user.language, "pending_hdr")] + [
            render_task(s, task, user.timezone) for task in tasks
        ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        q = s.query(Task).filter(
            or_(Task.creator_id == user.telegram_id, Task.assignee_id == user.telegram_id)
        )
        if is_group(update):
            q = q.filter(Task.chat_id == update.effective_chat.id)
        tasks = q.order_by(Task.is_done.asc(), Task.due_date.asc().nullslast()).all()
        if not tasks:
            await update.message.reply_text(t(user.language, "no_tasks"))
            return
        lines = [t(user.language, "all_hdr")] + [
            render_task(s, task, user.timezone) for task in tasks
        ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        now_local = datetime.now(ZoneInfo(user.timezone))
        start_utc = now_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        end_utc = start_utc + timedelta(days=7)

        q = s.query(Task).filter(
            or_(Task.creator_id == user.telegram_id, Task.assignee_id == user.telegram_id),
            Task.is_done == False,
            Task.due_date != None,
            Task.due_date >= start_utc,
            Task.due_date < end_utc,
        )
        if is_group(update):
            q = q.filter(Task.chat_id == update.effective_chat.id)
        tasks = q.order_by(Task.due_date.asc()).all()
        if not tasks:
            await update.message.reply_text(t(lang, "week_empty"))
            return

        by_day: dict[str, list[str]] = defaultdict(list)
        day_order: list[str] = []
        for task in tasks:
            local_dt = task.due_date.replace(tzinfo=ZoneInfo("UTC")).astimezone(
                ZoneInfo(user.timezone)
            )
            label = day_label(lang, local_dt)
            if label not in by_day:
                day_order.append(label)
            by_day[label].append(render_task(s, task, user.timezone))

        lines = [t(lang, "week_hdr")]
        for label in day_order:
            lines.append(f"\n📅 *{label}*")
            lines.extend(by_day[label])

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("/done <task_id>")
        return
    try:
        task_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text("/done <task_id>")
        return

    # Read task state before the async role check
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        task = s.get(Task, task_id)
        if not task:
            await update.message.reply_text(t(lang, "not_found"))
            return
        if task.creator_id != user.telegram_id and task.assignee_id != user.telegram_id:
            await update.message.reply_text(t(lang, "no_access"))
            return
        if task.pending_review:
            await update.message.reply_text(t(lang, "already_pending", id=task_id))
            return

        task_chat_id = task.chat_id
        task_title = task.title
        task_line = render_task(s, task, user.timezone)
        admin_ids = get_admin_ids(s, task_chat_id)
        assignee_id = task.assignee_id or task.creator_id
        is_recurring = task.is_recurring
        recur_interval = task.recur_interval
        due_date = task.due_date
        creator_id = task.creator_id

    # Async role check happens outside the session
    needs_review = False
    if is_group(update):
        assignee_role = await get_role(context, task_chat_id, assignee_id)
        needs_review = assignee_role == "kid"

    if needs_review:
        with get_session() as s:
            s.get(Task, task_id).pending_review = True

        await update.message.reply_text(t(lang, "pending_review_sent"))

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"verify:approve:{task_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"verify:reject:{task_id}"),
        ]])
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    admin_id,
                    t(lang, "verify_request",
                      name=update.effective_user.first_name, id=task_id, task=task_line),
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except Exception as exc:
                logger.warning("Could not notify admin %s: %s", admin_id, exc)
    else:
        with get_session() as s:
            task = s.get(Task, task_id)
            user = s.get(User, update.effective_user.id)
            task.is_done = True
            update_streak(user, user.timezone)
            if is_recurring and due_date and recur_interval:
                next_due = next_recurrence(due_date, recur_interval)
                if next_due:
                    s.add(Task(
                        creator_id=creator_id, assignee_id=assignee_id,
                        chat_id=task_chat_id, title=task_title,
                        due_date=next_due, is_recurring=True, recur_interval=recur_interval,
                    ))
            streak_part = t(lang, "done_streak", n=user.streak) if user.streak >= 2 else ""

        await update.message.reply_text(t(lang, "done", id=task_id, streak=streak_part))


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("/delete <task_id>")
        return
    try:
        task_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text("/delete <task_id>")
        return

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        task = s.get(Task, task_id)
        if not task:
            await update.message.reply_text(t(lang, "not_found"))
            return
        task_creator_id = task.creator_id

    if is_group(update):
        role = await get_role(context, update.effective_chat.id, update.effective_user.id)
        if role != "admin":
            await update.message.reply_text(t(lang, "no_perm_delete"))
            return
    elif task_creator_id != update.effective_user.id:
        await update.message.reply_text(t(lang, "not_creator"))
        return

    with get_session() as s:
        task = s.get(Task, task_id)
        if task:
            s.delete(task)

    await update.message.reply_text(t(lang, "deleted", id=task_id))


async def cmd_deleteall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        lang = upsert_user(s, update.effective_user).language

    if is_group(update):
        role = await get_role(context, update.effective_chat.id, update.effective_user.id)
        if role != "admin":
            await update.message.reply_text(t(lang, "no_perm_deleteall"))
            return

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        tasks = s.query(Task).filter(Task.creator_id == user.telegram_id).all()
        count = len(tasks)
        if not count:
            await update.message.reply_text(t(lang, "nothing_to_delete"))
            return
        for task in tasks:
            s.delete(task)

    await update.message.reply_text(t(lang, "deleted_all", count=count))
