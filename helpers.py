from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import ReplyKeyboardMarkup

from db import Task, User

_KEYBOARDS: dict[str, ReplyKeyboardMarkup] = {
    "en": ReplyKeyboardMarkup(
        [["📋 Tasks", "📅 This Week"], ["🛒 Shopping", "🔥 Streak"], ["❓ Help"]],
        resize_keyboard=True,
    ),
    "ru": ReplyKeyboardMarkup(
        [["📋 Задачи", "📅 Неделя"], ["🛒 Покупки", "🔥 Серия"], ["❓ Помощь"]],
        resize_keyboard=True,
    ),
}

BUTTON_MAP: dict[str, str] = {
    "📋 Tasks": "list",     "📋 Задачи": "list",
    "📅 This Week": "week", "📅 Неделя": "week",
    "🛒 Shopping": "shopping", "🛒 Покупки": "shopping",
    "🔥 Streak": "streak",  "🔥 Серия": "streak",
    "❓ Help": "help",       "❓ Помощь": "help",
}


def main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return _KEYBOARDS.get(lang, _KEYBOARDS["en"])


def upsert_user(session, tg_user) -> User:
    user = session.get(User, tg_user.id)
    auto_lang = "ru" if (tg_user.language_code or "").startswith("ru") else "en"
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "User",
            language=auto_lang,
        )
        session.add(user)
    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name or user.first_name
    return user


def render_task(session, task: Task, viewer_tz: str = "UTC") -> str:
    if task.pending_review:
        icon = "🔍"
    elif task.is_done:
        icon = "✅"
    else:
        icon = "⏳"
    assignee_label = ""
    if task.assignee_id:
        assignee = session.get(User, task.assignee_id)
        if assignee:
            name = assignee.username or assignee.first_name
            assignee_label = f" → @{name}"
    if task.due_date:
        local_dt = task.due_date.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(viewer_tz))
        due_str = local_dt.strftime("%b %d %H:%M")
    else:
        due_str = "no deadline"
    recur_str = " 🔄" if task.is_recurring else ""
    return f"{icon} [#{task.id}] {task.title}{assignee_label} — {due_str}{recur_str}"


def next_recurrence(due_date: datetime, interval: str) -> datetime | None:
    delta = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
    }
    return due_date + delta[interval] if interval in delta else None


def update_streak(user: User, user_tz: str) -> None:
    today = datetime.now(ZoneInfo(user_tz)).date()
    if user.last_completed is None or user.last_completed < today - timedelta(days=1):
        user.streak = 1
    elif user.last_completed == today - timedelta(days=1):
        user.streak += 1
    if user.last_completed != today:
        user.last_completed = today
