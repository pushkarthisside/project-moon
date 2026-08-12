# context.py

from datetime import datetime
from zoneinfo import ZoneInfo
from db import (
    get_active_goals,
    get_facts,
    get_pending_reminders,
    get_recent_messages,
)
from prompt import LUNA_SYSTEM_PROMPT


def format_messages(messages: list) -> str:
    if not messages:
        return "No recent conversation."
    lines = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "luna"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def format_facts(facts: list) -> str:
    if not facts:
        return "No known facts."
    lines = []
    for fact in facts:
        category = f"[{fact['category']}] " if fact["category"] else ""
        lines.append(f"- {category}{fact['content']}")
    return "\n".join(lines)


def format_goals(goals: list) -> str:
    if not goals:
        return "No active goals."
    lines = []
    for g in goals:
        target = f" | target: {g['target_date']}" if g["target_date"] else ""
        lines.append(f"- [{g['id']}] {g['content']} | type: {g['type']}{target}")
    return "\n".join(lines)


def format_reminders(reminders: list) -> str:
    if not reminders:
        return "No pending reminders."
    lines = []
    for r in reminders:
        lines.append(
            f"- [{r['id']}] {r['content']} | remind_at: {r['remind_at']}"
        )
    return "\n".join(lines)


def build_context() -> dict:
    """Fetch and format application state for Luna's system prompt."""
    current_dt = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    try:
        messages = get_recent_messages(limit=20) 
        recent_messages = format_messages(messages)
    except Exception as e:
        print(f"[context] Failed to retrieve recent messages: {e}")
        recent_messages = "[Context unavailable: recent conversation could not be retrieved.]"

    try:
        facts = get_facts(limit=10)
        facts_context = format_facts(facts)
    except Exception as e:
        print(f"[context] Failed to retrieve facts: {e}")
        facts_context = "[Context unavailable: known facts could not be retrieved.]"

    try:
        goals = get_active_goals()
        goals_context = format_goals(goals)
    except Exception as e:
        print(f"[context] Failed to retrieve active goals: {e}")
        goals_context = "[Context unavailable: active goals could not be retrieved.]"

    try:
        reminders = get_pending_reminders()
        reminders_context = format_reminders(reminders)
    except Exception as e:
        print(f"[context] Failed to retrieve pending reminders: {e}")
        reminders_context = "[Context unavailable: pending reminders could not be retrieved.]"

    return {
        "current_datetime": current_dt,
        "recent_messages": recent_messages,
        "facts_context": facts_context,
        "goals_context": goals_context,
        "reminders_context": reminders_context,
    }


def get_formatted_system_prompt() -> str:
    """Retrieve formatted database context and inject it directly into LUNA_SYSTEM_PROMPT."""
    ctx = build_context()
    return LUNA_SYSTEM_PROMPT.format(
        current_datetime=ctx["current_datetime"],
        recent_messages=ctx["recent_messages"],
        facts_context=ctx["facts_context"],
        goals_context=ctx["goals_context"],
        reminders_context=ctx["reminders_context"],
    )


if __name__ == "__main__":
    print("=== TESTING CONTEXT ASSEMBLY ===")
    print(get_formatted_system_prompt())