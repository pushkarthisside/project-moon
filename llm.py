import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError, RateLimitError
from zoneinfo import ZoneInfo

from tools import REGISTERED_TOOL_NAMES, TOOL_DEFINITIONS, execute_tool_call

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing required environment variable: GROQ_API_KEY")

# NOTE: llama-3.1-8b-instant and llama-3.3-70b-versatile were both shut down
# by Groq on 2026-08-16. openai/gpt-oss-120b is Groq's recommended
# replacement for llama-3.3-70b-versatile (Luna's main conversational/
# tool-calling model). Configurable via .env so future Groq deprecations
# don't require a code change.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Retry policy for transient Groq failures (rate limits, connection errors).
# Deliberately small and fast: this call happens inline in the user's
# request path, so we don't want retries to make Luna feel unresponsive.
MAX_GROQ_RETRIES = 1
RETRY_BACKOFF_SECONDS = (1, 3)

logger = logging.getLogger(__name__)
STATE_CHANGE_TOOLS = frozenset({
    "create_goal",
    "update_goal_status",
    "update_goal_target_date",
    "update_multiple_goal_statuses",
    "create_reminder",
    "update_reminder_status",
})

UNSUPPORTED_BULK_GOAL_DELETE_REPLY = (
    "I can't delete all of your goals yet — that action isn't supported."
)
NON_EXECUTING_STATE_REPLY = (
    "I won't pretend a reminder or goal was changed when it wasn't."
)
PROJECT_TIMEZONE = ZoneInfo("Asia/Kolkata")

_GOAL_STATUS_COMMAND = re.compile(
    r"^\s*mark\s+(?P<reference>.+?)\s+(?:as\s+)?(?:done|completed)\s*[.!?]*$",
    re.IGNORECASE,
)
_GOAL_DEADLINE_COMMAND = re.compile(
    r"^\s*(?:move|change|push|reschedule)\s+(?P<reference>.+?)\s+"
    r"(?:goal\s+)?(?:deadline|target\s+date)\s+(?:to|until)\s+"
    r"(?P<target>.+?)\s*[.!?]*$",
    re.IGNORECASE,
)
_WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
_GOAL_CREATION_REQUEST = re.compile(
    r"\b(?:create|add|set)\b.{0,80}\bgoal(?:s)?\b"
    r"|\bmake\s+(?:that|this|it|a|an|my|the)\b"
    r"(?:\s+[\w-]+){0,5}\s+goal(?:s)?\b",
    re.IGNORECASE,
)
_GOAL_DATE_FOLLOW_UP = re.compile(
    r"^\s*(?:like\s+)?(?:"
    r"in\s+(?:\d+\s*(?:[-–]\s*\d+)?|one|two|three|four|five|six|"
    r"seven|eight|nine|ten|a|an)\s+(?:day|week|month)s?"
    r"|(?:next|this)\s+(?:week|month|monday|tuesday|wednesday|thursday|"
    r"friday|saturday|sunday)"
    r"|by\s+(?:[a-z]+\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}\s+[a-z]+"
    r"(?:\s+\d{4})?)"
    r"|(?:today|tomorrow)"
    r"|(?:[a-z]+\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}\s+[a-z]+"
    r"(?:\s+\d{4})?)"
    r")\s*[.!?]*$",
    re.IGNORECASE,
)

# Initialize Groq client.
# max_retries=0: the SDK retries 429s/connection errors on its own by
# default (2 retries, with its own backoff). That stacks with our own
# retry loop below and produces compounding multi-retry delays (observed
# as 15s/2s/17s waits in production logs) instead of one bounded, visible
# retry policy. We own retry behavior entirely in _call_groq_with_retry().
groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0)


def _call_groq_with_retry(**kwargs):
    """Call the Groq completion endpoint with a small retry budget.

    Retries only on rate limits and transient connection errors, since those
    are the failure modes where waiting a moment and retrying can actually
    succeed. Auth/bad-request/other API errors are not retried; they won't
    be fixed by waiting, so we fail fast and let the caller's existing
    error handling (bot.py's top-level except) surface a clean message.
    """
    last_exc = None
    for attempt in range(MAX_GROQ_RETRIES + 1):
        try:
            return groq_client.chat.completions.create(**kwargs)
        except (RateLimitError, APIConnectionError) as exc:
            last_exc = exc
            if attempt < MAX_GROQ_RETRIES:
                wait = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning(
                    "Groq call failed (%s), attempt %s/%s; retrying in %ss",
                    type(exc).__name__,
                    attempt + 1,
                    MAX_GROQ_RETRIES + 1,
                    wait,
                )
                time.sleep(wait)
                continue
            logger.error(
                "Groq call failed after %s attempts (%s); giving up",
                MAX_GROQ_RETRIES + 1,
                type(exc).__name__,
            )
            raise
        except APIStatusError as exc:
            # Non-retryable API error (bad request, auth, model deprecated,
            # etc.). Log with the status code so a deprecated/renamed model
            # shows up clearly in logs instead of a generic failure.
            logger.error(
                "Groq API error: status=%s message=%s",
                getattr(exc, "status_code", "unknown"),
                str(exc),
            )
            raise
    raise last_exc  # pragma: no cover - loop always returns or raises


def _looks_like_pseudo_tool_output(content: str | None) -> bool:
    """Return whether the model emitted fake/XML-like tool syntax.

    This is deliberately only a safety check.  The content is never parsed or
    executed; structured ``tool_calls`` are the only supported execution path.
    """
    if not isinstance(content, str) or not content:
        return False
    return bool(
        re.search(
            r"<function\s*[:=,]\s*[A-Za-z_][\w-]*(?:\s*[>,=])",
            content,
            re.IGNORECASE,
        )
        or re.search(r"</function\s*>", content, re.IGNORECASE)
    )

def get_completion(
    messages: list,
    tools: list | None = None,
) -> dict:
    """
    Low-level Groq call. Takes a fully-formed `messages` list so callers can
    represent any conversation shape — including the
    system -> user -> assistant(tool_call) -> tool -> assistant
    round trip needed for tool calling.
    Returns a structured dictionary containing text content and/or tool call payloads.
    """
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.0,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
        kwargs["parallel_tool_calls"] = True

    completion = _call_groq_with_retry(**kwargs)
    choices = getattr(completion, "choices", None)
    if not choices:
        raise RuntimeError("Groq returned no completion choices")

    try:
        first_choice = choices[0]
    except (IndexError, KeyError, TypeError):
        raise RuntimeError("Groq returned malformed completion choices") from None

    response_message = getattr(first_choice, "message", None)
    if response_message is None:
        raise RuntimeError("Groq completion did not contain a response message")

    if not hasattr(response_message, "content") and not hasattr(
        response_message, "tool_calls"
    ):
        raise RuntimeError("Groq response message has an unexpected shape")

    return {
        "message": response_message,  # raw message object, needed to append back into `messages`
        "content": getattr(response_message, "content", None),
        "tool_calls": getattr(response_message, "tool_calls", None),
    }


def format_tool_message(call_id: str, tool_result_content: str) -> dict:
    """Format a tool result message for follow-up LLM completion turns."""
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": tool_result_content,
    }


def _summarize_tool_result(tool_name: str, result_content: str) -> str:
    """Return a safe deterministic fallback summary for an executed tool."""
    try:
        result = json.loads(result_content)
    except (json.JSONDecodeError, TypeError):
        if isinstance(result_content, str) and result_content.startswith("Error:"):
            return "One requested operation could not be completed."
        return "The requested operation completed."

    if not isinstance(result, dict):
        return "The requested operation completed."

    if tool_name in ("update_goal_status", "update_goal_target_date"):
        goal_reference = result.get("goal_reference", "that goal")
        resolution = result.get("resolution")
        if resolution == "ambiguous":
            return f"You have a few active goals matching '{goal_reference}'. Which one do you mean?"
        if resolution == "not_found":
            return f"I couldn't find an active goal matching '{goal_reference}'."
        if not result.get("success"):
            return "The goal was not updated."

        goal_content = result.get("goal_content")
        if not isinstance(goal_content, str) or not goal_content.strip():
            if tool_name == "update_goal_target_date":
                return "Updated the goal's target date."
            return "Updated the goal."
        if tool_name == "update_goal_target_date":
            return f"Updated the target date for '{goal_content}'."
        status = result.get("status")
        if status == "done":
            return f"Done — I marked '{goal_content}' as completed."
        if status == "dropped":
            return f"Done — I removed '{goal_content}' from your active goals."
        return f"Updated '{goal_content}'."

    if tool_name == "get_active_goals":
        if not result.get("success"):
            return "I couldn't retrieve your active goals."
        goals = result.get("goals", [])
        if not isinstance(goals, list) or not goals:
            return "You have no active goals."
        goal_contents = [
            goal["content"]
            for goal in goals
            if isinstance(goal, dict) and isinstance(goal.get("content"), str)
        ]
        if not goal_contents:
            return "I retrieved your active goals, but couldn't format them."
        if len(goal_contents) == 1:
            return f"Your active goal is {goal_contents[0]}."
        return "Your active goals include " + ", ".join(goal_contents[:-1]) + f", and {goal_contents[-1]}."

    if tool_name == "get_pending_reminders":
        if not result.get("success"):
            return "I couldn't retrieve your pending reminders."
        reminders = result.get("reminders", [])
        if not isinstance(reminders, list) or not reminders:
            return "You have no pending reminders."
        reminder_lines = []
        for reminder in reminders:
            if not isinstance(reminder, dict):
                continue
            content = reminder.get("content")
            if not isinstance(content, str):
                continue
            remind_at = reminder.get("remind_at")
            if isinstance(remind_at, str) and remind_at:
                reminder_lines.append(f"- {content} — {remind_at}")
            else:
                reminder_lines.append(f"- {content}")
        return "Pending reminders:\n" + "\n".join(reminder_lines) if reminder_lines else (
            "I retrieved your pending reminders, but couldn't format the list."
        )

    if tool_name == "update_multiple_goal_statuses":
        updated_count = len(result.get("updated_goal_ids", []))
        not_found_count = len(result.get("not_found_goal_ids", []))
        failed_count = len(result.get("failed_goal_ids", []))
        status = result.get("status", "requested status")
        lines = []
        if updated_count:
            lines.append(f"Updated {updated_count} goal(s) to '{status}'.")
        else:
            lines.append("No requested goals were updated.")
        if not_found_count:
            lines.append(f"{not_found_count} requested goal(s) were not found.")
        if failed_count:
            lines.append(f"{failed_count} requested goal(s) could not be updated.")
        return " ".join(lines)

    if not result.get("success"):
        if tool_name == "create_goal":
            if (
                result.get("message")
                == "Goal was not created because an identical active goal already exists."
            ):
                existing_content = result.get("existing_goal_content")
                if isinstance(existing_content, str) and existing_content.strip():
                    return f"You already have an active goal: {existing_content.strip()}"
                return "You already have an active goal like that."
            return "The goal was not created."
        if tool_name == "create_reminder":
            return "The reminder was not created."
        return "One requested operation could not be completed."

    success_messages = {
        "create_goal": "Created the goal.",
        "update_goal_status": "Updated the goal.",
        "update_goal_target_date": "Updated the goal's target date.",
        "create_reminder": "Set the reminder.",
        "update_reminder_status": "Updated the reminder.",
    }
    return success_messages.get(tool_name, "The requested operation completed.")


def _finalize_executed_tools(tool_results: list[tuple[str, str]]) -> str:
    """Return a truthful response when the bounded loop has no synthesis turn."""
    summaries = [_summarize_tool_result(name, content) for name, content in tool_results]
    return "\n".join(summaries) or "The requested operations completed."


def _tool_result_succeeded(result_content: str) -> bool:
    """Whether a tool explicitly confirmed its operation succeeded."""
    try:
        result = json.loads(result_content)
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(result, dict) and result.get("success") is True


def _has_successful_state_change(tool_results: list[tuple[str, str]]) -> bool:
    """Whether this turn has a confirmed persistent-state change."""
    return any(
        tool_name in STATE_CHANGE_TOOLS and _tool_result_succeeded(result_content)
        for tool_name, result_content in tool_results
    )


def _tool_names_from_definitions(definitions: list | None) -> frozenset[str]:
    """Extract valid function names from the schemas attached to this call."""
    if not definitions:
        return frozenset()
    return frozenset(
        definition.get("function", {}).get("name")
        for definition in definitions
        if isinstance(definition, dict)
        and isinstance(definition.get("function"), dict)
        and isinstance(definition["function"].get("name"), str)
    )


def _is_unsupported_bulk_goal_deletion(user_text: str) -> bool:
    normalized = " ".join(user_text.casefold().split())
    bulk_action = re.search(
        r"\b(?:delete+|remove|drop|cancel|abandon)\b\s+(?:all|every)\s+(?:(?:of\s+)?(?:my|the)\s+)?goal(?:s)?\b",
        normalized,
    )
    # "Clear my goals" is also an unambiguous request to erase the whole
    # collection, even though it does not contain an explicit quantifier.
    clear_collection = re.search(
        r"\bclear\s+(?:(?:all|the|my)\s+)?goal(?:s)?\b",
        normalized,
    )
    return bool((bulk_action or clear_collection) and re.search(r"\bgoal(?:s)?\b", normalized))


def _is_non_executing_state_request(user_text: str) -> bool:
    normalized = " ".join(user_text.casefold().split())
    return bool(
        re.search(r"\b(pretend|simulate|fake|fictional)\b", normalized)
        and re.search(r"\b(goal|reminder|remind)\b", normalized)
    )


def _message_requests_goal_status_update(user_text: str) -> bool:
    normalized = " ".join(user_text.casefold().split())
    return bool(
        re.search(
            r"\b(?:mark|complete|finish)\b.+?\b(?:as\s+)?(?:done|completed)\b",
            normalized,
        )
    )


def _message_requests_state_change(user_text: str) -> bool:
    """Whether the user is asking the application to mutate persistent state."""
    normalized = " ".join(user_text.casefold().split())
    if re.search(r"\b(remind me|set (?:a )?reminder|create (?:a )?reminder)\b", normalized):
        return True
    return bool(
        _message_requests_goal_status_update(user_text)
        or _GOAL_DEADLINE_COMMAND.fullmatch(user_text)
        or re.search(r"\b(create|add|set)\s+(?:a\s+)?goal\b", normalized)
        or re.search(r"\b(mark|complete|finish|drop|remove|cancel|delete)\b.*\bgoal(?:s)?\b", normalized)
        or (
            re.search(r"\breschedule\b.*\bgoal(?:s)?\b", normalized)
            or (
                re.search(r"\b(?:change|move|push)\b", normalized)
                and re.search(r"\b(?:deadline|target date)\b", normalized)
                and re.search(r"\bgoal(?:s)?\b", normalized)
            )
        )
        or re.search(r"\b(dismiss|cancel|remove)\b.*\breminder(?:s)?\b", normalized)
    )


def _message_requests_goal_creation(user_text: str) -> bool:
    """Return whether the user explicitly asks to make a goal."""
    return bool(_GOAL_CREATION_REQUEST.search(" ".join(user_text.casefold().split())))


def _last_recent_turn(system_prompt: str) -> tuple[str, str] | None:
    """Return the last role/content pair from the prompt's recent transcript."""
    if not isinstance(system_prompt, str):
        return None

    recent_marker = "## RECENT CONVERSATION"
    facts_marker = "## KNOWN USER FACTS"
    if recent_marker not in system_prompt or facts_marker not in system_prompt:
        return None

    recent_text = system_prompt.split(recent_marker, 1)[1].split(facts_marker, 1)[0]
    turns = re.findall(
        r"(?ms)^(user|luna):\s*(.*?)(?=^(?:user|luna):|\Z)",
        recent_text,
    )
    if not turns:
        return None
    role, content = turns[-1]
    return role, content.strip()


def _has_pending_goal_creation_date_request(system_prompt: str) -> bool:
    """Detect Luna's immediate request for a missing new-goal target date."""
    last_turn = _last_recent_turn(system_prompt)
    if last_turn is None:
        return False

    role, content = last_turn
    normalized = " ".join(content.casefold().split())
    if role != "luna" or not re.search(r"\bgoal(?:s)?\b", normalized):
        return False

    creation_context = bool(
        re.search(r"\b(?:add|create|set)\b.{0,100}\bgoal(?:s)?\b", normalized)
        or re.search(r"\bnew\s+goal\b", normalized)
    )
    date_request = bool(
        re.search(
            r"\b(?:target|completion)\s+date\b|\bdeadline\b",
            normalized,
        )
        and (
            "?" in content
            or re.search(
                r"\b(?:need|missing|when|what date|by when|would you like|should i use)\b",
                normalized,
            )
        )
    )
    return creation_context and date_request


def _is_goal_date_follow_up(user_text: str) -> bool:
    """Return whether a short message supplies a natural target date."""
    if not isinstance(user_text, str):
        return False
    return bool(_GOAL_DATE_FOLLOW_UP.fullmatch(" ".join(user_text.split())))


def _message_needs_tools(user_text: str, system_prompt: str | None = None) -> bool:
    """Return whether a message clearly requires goal/reminder tooling."""
    if not isinstance(user_text, str):
        return False

    normalized = " ".join(user_text.casefold().split())
    if not normalized:
        return False
    if _message_requests_goal_creation(user_text):
        return True
    if (
        _is_goal_date_follow_up(user_text)
        and _has_pending_goal_creation_date_request(system_prompt or "")
    ):
        return True
    if "remind" in normalized or "reminder" in normalized:
        return True
    if "schedule" in normalized:
        return True
    if _message_requests_goal_status_update(user_text):
        return True
    if _GOAL_DEADLINE_COMMAND.fullmatch(user_text):
        return True

    goal_terms = ("goal", "goals")
    goal_actions = (
        "mark", "complete", "completed", "finish", "finished", "done",
        "create", "add", "set", "update", "drop", "remove", "cancel",
        "change", "show", "list", "what are", "active",
    )
    return any(term in normalized for term in goal_terms) and any(
        action in normalized for action in goal_actions
    )


def _clean_goal_reference(value: str) -> str:
    """Strip conversational wrappers without changing a goal's meaning."""
    reference = value.strip().strip(".!?")
    if len(reference) >= 2 and reference[0] in "\"'" and reference[-1] == reference[0]:
        reference = reference[1:-1].strip()
    reference = re.sub(r"^my\s+", "", reference, flags=re.IGNORECASE)
    reference = re.sub(r"\s+goal$", "", reference, flags=re.IGNORECASE)
    return reference.strip()


def _parse_goal_target_date(value: str, now: datetime | None = None) -> str | None:
    """Parse the small set of deterministic deadline expressions used by fallback."""
    normalized = " ".join(value.casefold().split()).strip(".!?")
    if not normalized:
        return None

    for datetime_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(normalized, datetime_format)
        except ValueError:
            continue
        return parsed.strftime(datetime_format)

    if normalized in ("today", "tomorrow"):
        reference_now = now or datetime.now(PROJECT_TIMEZONE)
        days_ahead = 0 if normalized == "today" else 1
        return (reference_now.date() + timedelta(days=days_ahead)).isoformat()

    weekday = re.fullmatch(r"next\s+([a-z]+)", normalized)
    if weekday is None or weekday.group(1) not in _WEEKDAY_NAMES:
        return None

    reference_now = now or datetime.now(PROJECT_TIMEZONE)
    days_ahead = (_WEEKDAY_NAMES[weekday.group(1)] - reference_now.weekday()) % 7
    return (reference_now.date() + timedelta(days=days_ahead or 7)).isoformat()


def _parse_deterministic_single_goal_command(user_text: str) -> tuple[str, dict] | None:
    """Extract only clear single-goal commands for the no-tool-call fallback."""
    status_match = _GOAL_STATUS_COMMAND.fullmatch(user_text)
    if status_match is not None:
        reference = _clean_goal_reference(status_match.group("reference"))
        if reference and not re.search(r"\b(?:all|every)\b", reference, re.IGNORECASE):
            return "update_goal_status", {"goal_reference": reference, "status": "done"}

    deadline_match = _GOAL_DEADLINE_COMMAND.fullmatch(user_text)
    if deadline_match is not None:
        reference = _clean_goal_reference(deadline_match.group("reference"))
        target_date = _parse_goal_target_date(deadline_match.group("target"))
        if (
            reference
            and target_date is not None
            and not re.search(r"\b(?:all|every)\b", reference, re.IGNORECASE)
        ):
            return (
                "update_goal_target_date",
                {"goal_reference": reference, "target_date": target_date},
            )

    return None


def _execute_deterministic_goal_fallback(
    user_text: str,
    allowed_tool_names: frozenset[str],
) -> tuple[str, str] | None:
    """Execute a clear single-goal command when the model omitted its tool call."""
    command = _parse_deterministic_single_goal_command(user_text)
    if command is None:
        return None

    tool_name, arguments = command
    if tool_name not in allowed_tool_names:
        return None
    return tool_name, execute_tool_call(tool_name, json.dumps(arguments))


def get_reply(
    system_prompt: str,
    user_text: str,
    tools: list | None = None,
    max_tool_rounds: int = 2,
) -> dict:
    """
    High-level entry point: handles a full interaction, including any number
    of tool-call round trips.

    Flow:
      1. system + user -> ask Groq (with tools attached)
      2. if no tool calls -> return the text content
      3. otherwise: append the assistant's tool-call message, execute each
         tool, append each tool result, then ask Groq again with the full
         conversation so far
      4. repeat until Groq responds with plain content (or max_tool_rounds hit)
    """
    # These requests must not reach a state-changing tool.  In particular,
    # the batch-status tool is for explicit, scoped groups; it is not a
    # delete-everything capability.
    if _is_unsupported_bulk_goal_deletion(user_text):
        return {"text": UNSUPPORTED_BULK_GOAL_DELETE_REPLY, "state_change_attempted": False}
    if _is_non_executing_state_request(user_text):
        return {"text": NON_EXECUTING_STATE_REPLY, "state_change_attempted": False}

    if tools is None:
        tools = (
            TOOL_DEFINITIONS
            if _message_needs_tools(user_text, system_prompt)
            else None
        )
    allowed_tool_names = _tool_names_from_definitions(tools) & REGISTERED_TOOL_NAMES

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    # A single model turn must not be able to execute the same operation over
    # and over.  This is especially important for insert-like tools.
    seen_tool_calls = set()
    state_change_attempted = False
    executed_tool_results = []
    last_loop_path = "no completion round was started"
    for _ in range(max(0, max_tool_rounds)):
        current_round = _ + 1
        last_loop_path = f"completion round {current_round} started"
        try:
            response = get_completion(messages, tools=tools)
        except Exception:
            if not _has_successful_state_change(executed_tool_results):
                raise
            logger.exception(
                "Groq synthesis failed after a confirmed state change; "
                "returning deterministic tool result summary"
            )
            return {
                "text": _finalize_executed_tools(executed_tool_results),
                "state_change_attempted": state_change_attempted,
            }
        response_message = response["message"]

        tool_calls = response["tool_calls"]
        if not tool_calls:
            if _looks_like_pseudo_tool_output(response["content"]):
                last_loop_path = (
                    f"round {current_round} returned pseudo-tool output; "
                    "requested structured-tool correction"
                )
                logger.warning(
                    "Pseudo-tool output blocked in round %s/%s; continuing "
                    "with structured-tool correction",
                    current_round,
                    max_tool_rounds,
                )
                # Do not relay or interpret pseudo-function text.  Give the
                # provider one of the remaining structured-tool rounds to
                # correct itself.
                messages.append({
                    "role": "assistant",
                    "content": response["content"],
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "The previous response used invalid pseudo-function "
                        "text. Do not write function markup or imitate tool "
                        "syntax. Use one of the provided structured tools "
                        "with a tool call, or answer normally if no tool is "
                        "needed."
                    ),
                })
                continue
            if _message_requests_state_change(user_text) and not executed_tool_results:
                fallback_result = _execute_deterministic_goal_fallback(
                    user_text,
                    allowed_tool_names,
                )
                if fallback_result is not None:
                    tool_name, result_content = fallback_result
                    logger.warning(
                        "Model returned no tool call for clear goal command; "
                        "using deterministic %s fallback",
                        tool_name,
                    )
                    return {
                        "text": _finalize_executed_tools([(tool_name, result_content)]),
                        "state_change_attempted": True,
                    }
                logger.warning(
                    "State-changing request returned no tool call; blocking free-form response"
                )
                return {
                    "text": "I couldn't complete that action safely.",
                    "state_change_attempted": state_change_attempted,
                }
            return {
                "text": response["content"] or "I couldn't complete that action.",
                "state_change_attempted": state_change_attempted,
            }

        requested_tool_names = {
            call.function.name for call in tool_calls
            if getattr(call, "function", None) is not None
        }
        unsupported_names = requested_tool_names - allowed_tool_names
        if unsupported_names:
            logger.warning(
                "Blocked tool call(s) not available for this interaction: %s",
                sorted(unsupported_names),
            )
            # Never give an unknown-tool error back to the model for
            # interpretation: it could turn that failure into invented state.
            return {
                "text": "That operation isn't currently available.",
                "state_change_attempted": state_change_attempted,
            }

        # Preserve the assistant's tool-call turn in the conversation, as an
        # explicit dict rather than relying on SDK object serialization.
        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ],
        })

        # Run each requested tool and feed its result back in.
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments or "{}"
            logger.debug(
                "Model requested tool: name=%s raw_arguments=%r",
                tool_name,
                raw_arguments,
            )
            try:
                parsed_arguments = json.loads(raw_arguments)
                normalized_arguments = (
                    parsed_arguments if isinstance(parsed_arguments, dict) else {}
                )
                call_key = (tool_name, json.dumps(
                    normalized_arguments, sort_keys=True, separators=(",", ":")
                ))
            except (json.JSONDecodeError, TypeError):
                # Keep malformed argument handling in execute_tool_call(); the
                # raw value still forms a stable key for duplicate detection.
                call_key = (tool_name, str(raw_arguments))

            if call_key in seen_tool_calls:
                logger.warning(
                    "Duplicate tool call blocked: name=%s normalized_arguments=%s",
                    tool_name,
                    call_key[1],
                )
                result_content = (
                    f"Error: duplicate tool call for '{tool_name}' with the "
                    "same arguments was blocked in this interaction."
                )
            else:
                seen_tool_calls.add(call_key)
                if tool_name in STATE_CHANGE_TOOLS:
                    state_change_attempted = True
                result_content = execute_tool_call(
                    tool_name,
                    raw_arguments,
                )
                last_loop_path = (
                    f"round {current_round} executed requested tool '{tool_name}'"
                )

            messages.append(
                format_tool_message(tool_call.id, result_content)
            )
            executed_tool_results.append((tool_name, result_content))

            if not _tool_result_succeeded(result_content):
                logger.warning(
                    "Tool did not confirm success; returning deterministic result: %s",
                    tool_name,
                )
                # A failed operation never gets a free-form synthesis turn.
                # This prevents a model from describing an unconfirmed state
                # change as though it happened.
                return {
                    "text": _finalize_executed_tools(executed_tool_results),
                    "state_change_attempted": state_change_attempted,
                }

        # Loop back around: send the updated conversation (including tool
        # results) back to Groq for the next turn.

    if executed_tool_results:
        logger.warning(
            "Tool loop reached its bounded completion limit after executing "
            "tool calls; returning deterministic result summary instead of a "
            "false failure."
        )
        return {
            "text": _finalize_executed_tools(executed_tool_results),
            "state_change_attempted": state_change_attempted,
        }

    # Safety net: if we somehow never got a plain-content response or tool result.
    logger.error(
        "Final safe fallback returned: reason=max_tool_rounds reached; "
        "current_round=%s configured_max=%s; path=%s; "
        "response=I couldn't complete that action safely. Please try again.",
        max(0, max_tool_rounds),
        max_tool_rounds,
        last_loop_path,
    )
    return {
        "text": "I couldn't complete that action safely. Please try again.",
        "state_change_attempted": state_change_attempted,
    }
