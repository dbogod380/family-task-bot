from __future__ import annotations
import logging

from telegram import Update
from telegram.ext import ContextTypes

from db import GroupMember, User, get_session
from helpers import upsert_user
from i18n import t

logger = logging.getLogger(__name__)


def is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup")


async def get_role(context, chat_id: int, user_id: int) -> str:
    """Return user's role in a group. Checks DB first, then Telegram admin status."""
    with get_session() as s:
        member = s.query(GroupMember).filter_by(chat_id=chat_id, user_id=user_id).first()
        if member:
            return member.role
    try:
        cm = await context.bot.get_chat_member(chat_id, user_id)
        if cm.status in ("administrator", "creator"):
            return "admin"
    except Exception:
        pass
    return "member"


def get_admin_ids(session, chat_id: int) -> list[int]:
    """Return telegram_ids of all admins stored for this group."""
    return [
        m.user_id
        for m in session.query(GroupMember).filter_by(chat_id=chat_id, role="admin").all()
    ]


async def cmd_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_group(update):
        await update.message.reply_text("This command only works in groups.")
        return

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language

    caller_role = await get_role(context, update.effective_chat.id, update.effective_user.id)
    if caller_role != "admin":
        await update.message.reply_text(t(lang, "role_not_admin"))
        return

    valid_roles = ("admin", "member", "kid")
    if len(context.args) < 2 or context.args[1].lower() not in valid_roles:
        await update.message.reply_text(t(lang, "role_usage"))
        return

    target_username = context.args[0].lstrip("@")
    new_role = context.args[1].lower()

    with get_session() as s:
        target = s.query(User).filter_by(username=target_username).first()
        if not target:
            await update.message.reply_text(t(lang, "role_user_not_found"))
            return
        member = s.query(GroupMember).filter_by(
            chat_id=update.effective_chat.id, user_id=target.telegram_id
        ).first()
        if member:
            member.role = new_role
        else:
            s.add(GroupMember(
                chat_id=update.effective_chat.id,
                user_id=target.telegram_id,
                role=new_role,
            ))

    await update.message.reply_text(
        t(lang, "role_set", username=target_username, role=new_role),
        parse_mode="Markdown",
    )


async def cmd_roles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_group(update):
        await update.message.reply_text("This command only works in groups.")
        return

    chat_id = update.effective_chat.id
    role_icons = {"admin": "👑", "member": "👤", "kid": "🧒"}

    with get_session() as s:
        user = upsert_user(s, update.effective_user)
        lang = user.language
        members = s.query(GroupMember).filter_by(chat_id=chat_id).all()
        if not members:
            await update.message.reply_text(t(lang, "roles_empty"))
            return
        lines = [t(lang, "roles_hdr")]
        for m in members:
            u = s.get(User, m.user_id)
            if u:
                name = f"@{u.username}" if u.username else u.first_name
                lines.append(f"{role_icons.get(m.role, '👤')} {name} — {m.role}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
