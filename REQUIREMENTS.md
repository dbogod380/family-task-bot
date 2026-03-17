# Family Task Bot — Requirements & Feature Specification

## 1. Overview

A Telegram bot for family task management. Members can create tasks, assign them to each other, receive automatic reminders, share a shopping list, and track completion streaks. The bot works in both private chats and family group chats.

---

## 2. Users & Registration

- Every user who sends `/start` is automatically registered.
- Language is auto-detected from the user's Telegram locale (`en` or `ru`).
- Timezone defaults to UTC. The bot prompts the user to share their GPS location on first `/start` so the timezone can be auto-detected. Users can also set it manually.
- User profile is updated (username, first name) on every interaction.

---

## 3. Role System (Groups Only)

Roles are per-group. A user may have different roles in different groups.

| Role | Assigned by | Capabilities |
|------|-------------|-------------|
| **admin** | Another admin, or Telegram group admin/creator | Full control: create, assign, delete any task; set roles; approve completions |
| **member** | Admin | Create tasks, complete own tasks; cannot delete others' tasks |
| **kid** | Admin | Can only complete tasks explicitly assigned to them; cannot create or delete tasks |

### Role assignment rules
- `/role` can only be run by a user whose role is `admin` (or who is a Telegram group administrator/creator, as a bootstrap path).
- If no explicit role is set in the database, Telegram administrator status is checked as fallback; otherwise the user is treated as `member`.

### Commands
| Command | Who | Description |
|---------|-----|-------------|
| `/role @username admin\|member\|kid` | admin only | Assign a role to a group member |
| `/roles` | any | List all role assignments in this group |

---

## 4. Task Management

### Creating tasks
- `/add <natural language description>` — NLP parses the title, due date, assignee, and recurrence.
- **Reply-to-assign**: replying to another user's message before `/add` automatically assigns the task to that user.
- Kids cannot create tasks in a group; they must ask an admin.

### NLP parsing (two-tier)
1. **Claude API** (`claude-opus-4-6`): used when API credits are available. Extracts title, ISO 8601 due date, assignee username, recurrence flag and interval.
2. **Regex fallback**: used automatically when the Claude API is unavailable. Handles today / tonight / tomorrow / weekday names / "in N hours" / "in N minutes" / explicit times (12h and 24h).

### Listing tasks
| Command | Shows |
|---------|-------|
| `/list` | Pending tasks where you are creator or assignee |
| `/all` | All tasks (done + pending) where you are creator or assignee |
| `/week` | Pending tasks due in the next 7 days, grouped by day |

### Completing tasks
- `/done <id>` marks a task complete.
- **Verification workflow (groups)**: if the completing user has the `kid` role, the task enters `pending_review` state instead of closing immediately. All admins for that group receive a private notification with **Approve / Reject** inline buttons. On approval the task closes and the kid's streak increments. On rejection, the task reopens and the kid is notified.
- Outside groups, tasks close immediately on `/done`.

### Recurring tasks
- Supported intervals: `daily`, `weekly`, `monthly`.
- When a recurring task is completed, a new task with the next due date is created automatically.

### Deleting tasks
| Command | Private chat | Group (member/kid) | Group (admin) |
|---------|-------------|-------------------|---------------|
| `/delete <id>` | Creator only | Blocked | Any task |
| `/deleteall` | Own tasks | Blocked | Own tasks |

### Reminders
- A background job runs every 60 seconds.
- Any task whose `due_date` is within the next 2 minutes and has not had a reminder sent triggers a notification.
- Notifications are sent to the assignee (or creator) privately **and** to the group chat if the task originated there.
- Each reminder message includes inline buttons: **✅ Done**, **⏰ +1h**, **📅 Tomorrow** (snooze by 1 hour or 1 day).

### Task display format
```
⏳ [#5] Buy groceries → @anna — Mar 20 14:00 🔄
✅ [#3] Call dentist — Mar 18 09:00
🔍 [#7] Clean room → @kid — Mar 21 18:00   (pending review)
```

---

## 5. Shopping List

- Shared per chat (private or group).
- `/buy <item>` — adds an item.
- `/shopping` — shows the full list with checkboxes as inline buttons.
- Tapping an item toggles its checked state in-place (message edits itself).
- **Clear checked** button removes all checked items at once.

---

## 6. Streaks

- Each user has a personal streak counter: the number of consecutive days on which at least one task was completed.
- Streak increments on task completion (including inline **Done** button from reminders).
- Streak resets to 1 if a day was skipped.
- `/streak` — shows current streak count.
- Completion messages display the streak when it reaches 2+ days.

---

## 7. Morning Digest

- At 08:00 in each user's local timezone, the bot sends a private message listing:
  - Tasks due today.
  - Tasks that are overdue (due date in the past, still open).
- If there are no such tasks, a "clear day" message is sent instead.
- Only one digest per user per calendar day (idempotent).

---

## 8. Localisation

Supported languages: **English** (`en`) and **Russian** (`ru`).

- Auto-detected from Telegram's `language_code` on first registration.
- User can switch with `/lang en` or `/lang ru`.
- All bot messages, button labels, and date formatting are translated.

---

## 9. Navigation (Persistent Keyboard)

A persistent bottom keyboard is shown to every user:

| EN | RU | Action |
|----|----|--------|
| 📋 Tasks | 📋 Задачи | `/list` |
| 📅 This Week | 📅 Неделя | `/week` |
| 🛒 Shopping | 🛒 Покупки | `/shopping` |
| 🔥 Streak | 🔥 Серия | `/streak` |
| ❓ Help | ❓ Помощь | `/help` |

---

## 10. Timezone Management

| Method | Command / Action |
|--------|-----------------|
| Auto (GPS) | Share location button shown on `/start` |
| Manual | `/timezone Europe/Moscow` (any IANA tz name) |

All stored due dates are in UTC. Display converts to the viewer's local timezone.

---

## 11. Full Command Reference

| Command | Description |
|---------|-------------|
| `/start` | Register / show welcome message + keyboard |
| `/help` | Show all commands |
| `/add <text>` | Add a task (natural language) |
| `/list` | Pending tasks |
| `/all` | All tasks |
| `/week` | Tasks due this week |
| `/done <id>` | Mark task complete (triggers review if kid) |
| `/delete <id>` | Delete a task |
| `/deleteall` | Delete all your tasks |
| `/buy <item>` | Add item to shopping list |
| `/shopping` | Show shopping list |
| `/role @user admin\|member\|kid` | Assign group role (admin only) |
| `/roles` | Show group role assignments |
| `/streak` | Show your streak |
| `/timezone <tz>` | Set timezone manually |
| `/lang en\|ru` | Set language |

---

## 12. Technical Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| Bot framework | `python-telegram-bot` v20+ (async) |
| Database | SQLite via SQLAlchemy 2.0 |
| NLP (primary) | Anthropic Claude API (`claude-opus-4-6`) |
| NLP (fallback) | Regex-based local parser |
| Scheduling | PTB JobQueue (APScheduler) |
| Timezone detection | `timezonefinder` (GPS-based) |
| Timezone handling | `zoneinfo` (stdlib, Python 3.9+) |
| Config | `.env` via `python-dotenv` |

### Data models

**User** — `telegram_id`, `username`, `first_name`, `timezone`, `language`, `streak`, `last_completed`, `digest_sent_date`

**Task** — `id`, `creator_id`, `assignee_id`, `chat_id`, `title`, `due_date` (UTC), `is_done`, `is_recurring`, `recur_interval`, `reminder_sent`, `pending_review`, `created_at`

**GroupMember** — `chat_id`, `user_id`, `role` (unique per chat+user)

**ShoppingItem** — `id`, `chat_id`, `text`, `added_by`, `is_checked`, `created_at`

### Module layout

| File | Responsibility |
|------|---------------|
| `bot.py` | Entry point, handler registration, job scheduling |
| `db.py` | SQLAlchemy models, session manager, schema migration |
| `nlp.py` | Task parsing (Claude + regex fallback) |
| `i18n.py` | EN/RU string table and helpers |
| `helpers.py` | Shared utilities: `upsert_user`, `render_task`, keyboards, `update_streak` |
| `roles.py` | Role resolution, `/role`, `/roles` |
| `tasks.py` | Task CRUD command handlers |
| `shopping.py` | Shopping list command handlers and UI |
| `settings.py` | `/start`, `/help`, `/timezone`, `/lang`, `/streak`, location handler |
| `callbacks.py` | Inline button callbacks (shopping, verification, reminder actions) |
| `jobs.py` | Background jobs: reminders, morning digest |

---

## 13. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `ANTHROPIC_API_KEY` | Optional | Claude API key. If absent or out of credits, regex parser is used automatically |
| `DATABASE_URL` | Optional | SQLAlchemy DB URL. Defaults to `sqlite:///family_tasks.db` |
