from __future__ import annotations
import os
import json
import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import anthropic

logger = logging.getLogger(__name__)
_client: anthropic.Anthropic | None = None

_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


# ── Local (regex) parser ──────────────────────────────────────────────────────

def _parse_time(text: str):
    """Return (hour, minute) or None."""
    m = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', text, re.IGNORECASE)
    if m:
        h, mins = int(m.group(1)), int(m.group(2) or 0)
        period = m.group(3).lower()
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return h, mins
    m = re.search(r'\b(\d{1,2}):(\d{2})\b', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _parse_due_date(text: str, now: datetime):
    t = text.lower()
    time_hm = _parse_time(text)
    h, mins = time_hm if time_hm else (9, 0)

    def at(base: datetime) -> datetime:
        return base.replace(hour=h, minute=mins, second=0, microsecond=0)

    if re.search(r'\btoday\b|\btonight\b', t):
        return at(now)
    if re.search(r'\btomorrow\b', t):
        return at(now + timedelta(days=1))

    m = re.search(r'\bin (\d+) hours?\b', t)
    if m:
        return now + timedelta(hours=int(m.group(1)))
    m = re.search(r'\bin (\d+) minutes?\b', t)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    for i, day in enumerate(_DAYS):
        if re.search(r'\b' + day + r'\b', t):
            days_ahead = (i - now.weekday()) % 7 or 7
            return at(now + timedelta(days=days_ahead))

    # Only a time was given — assume today, push to tomorrow if already past
    if time_hm:
        candidate = at(now)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    return None


def _clean_title(text: str) -> str:
    t = re.sub(r'^(remind\s+(me\s+)?to|don\'t\s+forget\s+to|remember\s+to)\s+',
               '', text.strip(), flags=re.IGNORECASE)
    t = re.sub(r'@\w+', '', t)
    # strip trailing date/time phrase
    t = re.sub(
        r'\s+(today|tonight|tomorrow'
        r'|every\b.*'
        r'|in \d+ (hour|minute)s?'
        r'|(this\s+|next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        r'|at \d[\d:]*\s*(am|pm)?'
        r'|by \d.*)$',
        '', t.strip(), flags=re.IGNORECASE,
    )
    t = re.sub(r'\s+', ' ', t).strip()
    return t.capitalize() if t else text.strip()


def _parse_local(text: str, user_timezone: str = "UTC") -> dict:
    now = datetime.now(ZoneInfo(user_timezone))
    tl = text.lower()

    due_dt = _parse_due_date(text, now)

    is_recurring = bool(re.search(r'\bevery\b|\bdaily\b|\bweekly\b|\bmonthly\b', tl))
    recur_interval = None
    if is_recurring:
        if re.search(r'\bdaily\b|\bevery\s+day\b', tl):
            recur_interval = "daily"
        elif re.search(r'\bmonthly\b|\bevery\s+month\b', tl):
            recur_interval = "monthly"
        else:
            recur_interval = "weekly"

    assignee_m = re.search(r'@(\w+)', text)
    assignee = assignee_m.group(1) if assignee_m else None

    return {
        "title": _clean_title(text),
        "due_date": due_dt.isoformat() if due_dt else None,
        "assignee_username": assignee,
        "is_recurring": is_recurring,
        "recur_interval": recur_interval,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def parse_task(text: str, user_timezone: str = "UTC") -> dict:
    """Try Claude first; fall back to local regex parser on any error."""
    now = datetime.now(ZoneInfo(user_timezone))

    try:
        response = _get_client().messages.create(
            model="claude-opus-4-6",
            max_tokens=256,
            system=(
                "You extract task information from natural language. "
                "Return ONLY valid JSON with these exact fields:\n"
                '- "title": concise task name (string)\n'
                '- "due_date": ISO 8601 datetime string (e.g. "2024-06-15T15:00:00") or null\n'
                '- "assignee_username": telegram username without @ or null\n'
                '- "is_recurring": true or false\n'
                '- "recur_interval": "daily" | "weekly" | "monthly" | null\n\n'
                "No markdown, no explanation — raw JSON only."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Current date/time: {now.strftime('%Y-%m-%d %H:%M')} ({user_timezone})\n"
                    f"Task description: {text}"
                ),
            }],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)

    except Exception as exc:
        logger.info("Claude unavailable (%s) — using local parser", type(exc).__name__)
        return _parse_local(text, user_timezone)
