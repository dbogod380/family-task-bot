from __future__ import annotations
from datetime import datetime

_DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "start": "👋 Hi {name}!\n\nI'm your family task & reminder bot.\n\nTry: /add call dentist tomorrow 3pm\nOr /help for all commands.",
        "share_location": "📍 Share your location so I can set your timezone automatically:",
        "tz_auto": "✅ Timezone set to *{tz}*",
        "tz_manual": "✅ Timezone set to `{tz}`",
        "tz_fail": "❌ Unknown timezone: `{tz}`\nTry: Europe/London, America/New_York",
        "parsing": "🤔 Parsing…",
        "task_added": "✅ Task added!\n\n{task}",
        "assigned_notify": "📌 New task from @{creator}:\n\n{task}",
        "reply_assigned": " _(assigned from reply)_",
        "no_pending": "🎉 No pending tasks!",
        "no_tasks": "No tasks yet.",
        "pending_hdr": "📋 *Pending tasks:*\n",
        "all_hdr": "📋 *All tasks:*\n",
        "week_hdr": "📅 *Tasks this week:*\n",
        "week_empty": "No tasks this week 🎉",
        "done": "✅ Task #{id} done!{streak}",
        "done_streak": " 🔥 {n}-day streak!",
        "no_access": "You don't have access to this task.",
        "not_found": "Task not found.",
        "not_creator": "Task not found or you didn't create it.",
        "deleted": "🗑️ Task #{id} deleted.",
        "deleted_all": "🗑️ Deleted {count} task(s).",
        "nothing_to_delete": "No tasks to delete.",
        "reminder_private": "⏰ *Reminder:* {title}",
        "reminder_group": "⏰ *Reminder* for {mention}: {title}",
        "buy_usage": "Usage: /buy <item>",
        "buy_added": "🛒 Added: *{item}*",
        "shopping_empty": "🛒 Shopping list is empty.",
        "shopping_hdr": "🛒 *Shopping list:*",
        "shop_clear_btn": "🗑️ Clear checked",
        "shop_cleared": "✅ Cleared checked items.",
        "streak_show": "🔥 *{name}'s streak:* {n} day(s) in a row!",
        "streak_none": "No streak yet — complete a task to start one!",
        "digest": "☀️ *Good morning, {name}!*\n\nYour tasks for today:\n{tasks}",
        "digest_empty": "☀️ *Good morning, {name}!*\n\nNo tasks today. Enjoy! 🎉",
        "lang_set": "✅ Language set to English.",
        "lang_unknown": "Unknown language. Use: /lang en  or  /lang ru",
        "role_set": "✅ @{username} is now *{role}*.",
        "role_not_admin": "❌ Only admins can set roles.",
        "role_usage": "Usage: /role @username admin|member|kid",
        "role_user_not_found": "❌ User not found. They need to /start the bot first.",
        "roles_hdr": "👥 *Group roles:*",
        "roles_empty": "No roles set yet. Use /role @username admin|member|kid",
        "pending_review_sent": "⏳ Marked as done! Waiting for admin approval.",
        "already_pending": "⏳ Task #{id} is already waiting for review.",
        "verify_request": "🔍 *{name}* says task #{id} is done:\n\n{task}\n\nApprove?",
        "verify_approved": "✅ Task #{id} approved by admin!",
        "verify_approved_notify": "✅ Your task was approved: *{title}*",
        "verify_rejected_admin": "❌ Task #{id} rejected.",
        "verify_rejected_notify": "❌ Your task was rejected: *{title}*\n\nTry again when it's really done.",
        "no_perm_delete": "❌ Only admins can delete tasks in this group.",
        "no_perm_deleteall": "❌ Only admins can delete all tasks in this group.",
        "kid_no_create": "❌ Kids can't create tasks. Ask an admin to add one for you.",
        "help": (
            "📋 *Commands*\n\n"
            "*Tasks*\n"
            "/add `<task>` — Add a task (plain English)\n"
            "/list — Pending tasks\n"
            "/all — All tasks\n"
            "/week — This week's tasks\n"
            "/done `<id>` — Mark complete\n"
            "/delete `<id>` — Delete a task\n"
            "/deleteall — Delete all your tasks\n\n"
            "*Shopping*\n"
            "/buy `<item>` — Add to shopping list\n"
            "/shopping — Show shopping list\n\n"
            "*Roles (groups)*\n"
            "/role `@user admin|member|kid` — Assign role\n"
            "/roles — Show group roles\n\n"
            "*You*\n"
            "/streak — Your completion streak\n"
            "/timezone `<tz>` — Set timezone\n"
            "/lang `en|ru` — Set language\n"
            "/help — This message\n\n"
            "_Tip: Reply to someone's message with /add to assign the task to them._"
        ),
    },
    "ru": {
        "start": "👋 Привет, {name}!\n\nЯ бот для семейных задач и напоминаний.\n\nПопробуй: /add позвонить врачу завтра в 15:00\nИли /help для списка команд.",
        "share_location": "📍 Поделитесь геолокацией для определения часового пояса:",
        "tz_auto": "✅ Часовой пояс определён: *{tz}*",
        "tz_manual": "✅ Часовой пояс установлен: `{tz}`",
        "tz_fail": "❌ Неизвестный часовой пояс: `{tz}`\nПример: Europe/Moscow, Europe/London",
        "parsing": "🤔 Разбираю…",
        "task_added": "✅ Задача добавлена!\n\n{task}",
        "assigned_notify": "📌 Новая задача от @{creator}:\n\n{task}",
        "reply_assigned": " _(назначено из ответа)_",
        "no_pending": "🎉 Нет текущих задач!",
        "no_tasks": "Задач пока нет.",
        "pending_hdr": "📋 *Текущие задачи:*\n",
        "all_hdr": "📋 *Все задачи:*\n",
        "week_hdr": "📅 *Задачи на неделю:*\n",
        "week_empty": "Задач на эту неделю нет 🎉",
        "done": "✅ Задача #{id} выполнена!{streak}",
        "done_streak": " 🔥 Серия {n} дн.!",
        "no_access": "У вас нет доступа к этой задаче.",
        "not_found": "Задача не найдена.",
        "not_creator": "Задача не найдена или вы не её автор.",
        "deleted": "🗑️ Задача #{id} удалена.",
        "deleted_all": "🗑️ Удалено задач: {count}.",
        "nothing_to_delete": "Нет задач для удаления.",
        "reminder_private": "⏰ *Напоминание:* {title}",
        "reminder_group": "⏰ *Напоминание* для {mention}: {title}",
        "buy_usage": "Использование: /buy <товар>",
        "buy_added": "🛒 Добавлено: *{item}*",
        "shopping_empty": "🛒 Список покупок пуст.",
        "shopping_hdr": "🛒 *Список покупок:*",
        "shop_clear_btn": "🗑️ Удалить отмеченные",
        "shop_cleared": "✅ Отмеченные товары удалены.",
        "streak_show": "🔥 *Серия {name}:* {n} дн. подряд!",
        "streak_none": "Серии нет — выполните задачу, чтобы начать!",
        "digest": "☀️ *Доброе утро, {name}!*\n\nВаши задачи на сегодня:\n{tasks}",
        "digest_empty": "☀️ *Доброе утро, {name}!*\n\nЗадач на сегодня нет. Хорошего дня! 🎉",
        "lang_set": "✅ Язык установлен: русский.",
        "lang_unknown": "Неизвестный язык. Используй: /lang en  или  /lang ru",
        "role_set": "✅ @{username} теперь *{role}*.",
        "role_not_admin": "❌ Только администраторы могут назначать роли.",
        "role_usage": "Использование: /role @username admin|member|kid",
        "role_user_not_found": "❌ Пользователь не найден. Им нужно написать /start боту.",
        "roles_hdr": "👥 *Роли в группе:*",
        "roles_empty": "Роли ещё не назначены. Используйте /role @username admin|member|kid",
        "pending_review_sent": "⏳ Отмечено как выполненное! Ждём подтверждения от администратора.",
        "already_pending": "⏳ Задача #{id} уже ожидает проверки.",
        "verify_request": "🔍 *{name}* говорит, что задача #{id} выполнена:\n\n{task}\n\nПодтвердить?",
        "verify_approved": "✅ Задача #{id} подтверждена!",
        "verify_approved_notify": "✅ Ваша задача подтверждена: *{title}*",
        "verify_rejected_admin": "❌ Задача #{id} отклонена.",
        "verify_rejected_notify": "❌ Ваша задача отклонена: *{title}*\n\nПопробуйте ещё раз, когда выполните её.",
        "no_perm_delete": "❌ Только администраторы могут удалять задачи в этой группе.",
        "no_perm_deleteall": "❌ Только администраторы могут удалять все задачи в этой группе.",
        "kid_no_create": "❌ Дети не могут создавать задачи. Попросите администратора.",
        "help": (
            "📋 *Команды*\n\n"
            "*Задачи*\n"
            "/add `<задача>` — Добавить задачу\n"
            "/list — Текущие задачи\n"
            "/all — Все задачи\n"
            "/week — Задачи на неделю\n"
            "/done `<id>` — Отметить выполненной\n"
            "/delete `<id>` — Удалить задачу\n"
            "/deleteall — Удалить все ваши задачи\n\n"
            "*Покупки*\n"
            "/buy `<товар>` — Добавить в список покупок\n"
            "/shopping — Показать список покупок\n\n"
            "*Роли (группы)*\n"
            "/role `@user admin|member|kid` — Назначить роль\n"
            "/roles — Роли в группе\n\n"
            "*Настройки*\n"
            "/streak — Ваша серия выполнений\n"
            "/timezone `<tz>` — Часовой пояс\n"
            "/lang `en|ru` — Язык\n"
            "/help — Это сообщение\n\n"
            "_Совет: Ответьте на сообщение командой /add, чтобы назначить задачу автору._"
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in STRINGS else "en"
    text = STRINGS[lang].get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def day_label(lang: str, dt: datetime) -> str:
    days = _DAYS_RU if lang == "ru" else _DAYS_EN
    months = _MONTHS_RU if lang == "ru" else _MONTHS_EN
    return f"{days[dt.weekday()]}, {dt.day} {months[dt.month - 1]}"
