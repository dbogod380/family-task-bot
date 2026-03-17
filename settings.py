from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes
from timezonefinder import TimezoneFinder

from db import get_session
from helpers import upsert_user, main_keyboard, BUTTON_MAP
from i18n import t

_tf = TimezoneFinder()


async def _send_tz_prompt(update: Update, lang: str) -> None:
    """Send the location-share keyboard to ask the user for their timezone."""
    await update.message.reply_text(
        t(lang, "share_location"),
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Share my location", request_location=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )


async def maybe_prompt_timezone(update: Update, lang: str, user_tz: str) -> None:
    """In private chat, nudge users who still have UTC to set their timezone."""
    if user_tz == "UTC" and update.effective_chat.type == "private":
        await _send_tz_prompt(update, lang)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        needs_tz = user.timezone == "UTC"

    await update.message.reply_text(
        t(lang, "start", name=update.effective_user.first_name),
        reply_markup=main_keyboard(lang),
    )
    # Only prompt for location in private chat — location buttons are confusing in groups
    is_private = update.effective_chat.type == "private"
    if needs_tz and is_private:
        await _send_tz_prompt(update, lang)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loc = update.message.location
    tz_name = _tf.timezone_at(lat=loc.latitude, lng=loc.longitude)

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        if tz_name:
            user.timezone = tz_name

    if tz_name:
        await update.message.reply_text(
            t(lang, "tz_auto", tz=tz_name),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            t(lang, "tz_fail", tz="?"),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        lang = upsert_user(s, update.effective_user).language
    await update.message.reply_text(t(lang, "help"), parse_mode="Markdown")


async def cmd_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        lang = upsert_user(s, update.effective_user).language

    if not context.args:
        await update.message.reply_text(
            "Usage: /timezone <tz>\nExamples: Europe/London, America/New_York, Asia/Tokyo"
        )
        return

    tz_str = context.args[0]
    # ZoneInfoNotFoundError is a subclass of KeyError — catch both to be safe
    try:
        ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, KeyError, Exception):
        await update.message.reply_text(t(lang, "tz_fail", tz=tz_str), parse_mode="Markdown")
        return

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        user.timezone = tz_str
        s.flush()  # force the UPDATE before commit

    await update.message.reply_text(t(lang, "tz_manual", tz=tz_str), parse_mode="Markdown")


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or context.args[0].lower() not in ("en", "ru"):
        with get_session() as s:
            lang = upsert_user(s, update.effective_user).language
        await update.message.reply_text(t(lang, "lang_unknown"))
        return

    new_lang = context.args[0].lower()
    with get_session() as s:
        upsert_user(s, update.effective_user).language = new_lang

    await update.message.reply_text(t(new_lang, "lang_set"), reply_markup=main_keyboard(new_lang))


async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang, streak = user.language, user.streak

    if streak > 0:
        await update.message.reply_text(
            t(lang, "streak_show", name=update.effective_user.first_name, n=streak)
        )
    else:
        await update.message.reply_text(t(lang, "streak_none"))


async def handle_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Local imports to avoid circular dependency
    from tasks import cmd_list, cmd_week
    from shopping import cmd_shopping

    action = BUTTON_MAP.get(update.message.text)
    dispatch = {
        "list": cmd_list,
        "week": cmd_week,
        "shopping": cmd_shopping,
        "streak": cmd_streak,
        "help": cmd_help,
    }
    handler = dispatch.get(action)
    if handler:
        await handler(update, context)
