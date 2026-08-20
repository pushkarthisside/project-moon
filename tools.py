import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
import db

logger = logging.getLogger(__name__)
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

# ==========================================
# GOAL TOOLS
# ==========================================

def create_goal(content: str, goal_type: str, target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new goal in the database.
    
    Args:
        content: Description of the goal.
        goal_type: Must be 'daily', 'mid-term', or 'long-term'.
        target_date: Target completion date in ISO format 'YYYY-MM-DD HH:MM:SS' (optional).
    """
    try:
        goal_id = db.create_goal(content=content, goal_type=goal_type, target_date=target_date)
        return {"success": True, "goal_id": goal_id, "message": f"Goal created successfully with ID {goal_id}."}
    except db.DuplicateActiveGoalError as e:
        existing_content = None
        try:
            existing_content = next(
                (
                    row["content"]
                    for row in db.get_active_goals()
                    if row["id"] == e.goal_id
                ),
                None,
            )
        except Exception:
            logger.exception("Error retrieving duplicate goal content for ID %s", e.goal_id)
        return {
            "success": False,
            "goal_id": e.goal_id,
            "existing_goal_content": existing_content,
            "error": str(e),
            "message": "Goal was not created because an identical active goal already exists.",
        }
    except Exception as e:
        logger.exception("Error creating goal")
        return {"success": False, "error": str(e)}


def get_active_goals() -> Dict[str, Any]:
    """Retrieve all currently active goals."""
    try:
        rows = db.get_active_goals()
        goals = [dict(row) for row in rows]
        return {"success": True, "count": len(goals), "goals": goals}
    except Exception as e:
        logger.exception("Error fetching active goals")
        return {"success": False, "error": str(e)}


def _resolve_active_goal_reference(goal_reference: str) -> Dict[str, Any]:
    """Resolve a conservative human-readable reference against active goals."""
    normalized_reference = " ".join(goal_reference.strip().casefold().split())
    goals = [dict(row) for row in db.get_active_goals()]

    exact_matches = [
        goal
        for goal in goals
        if " ".join(goal["content"].strip().casefold().split()) == normalized_reference
    ]
    if len(exact_matches) == 1:
        return {"status": "matched", "goal": exact_matches[0]}
    if len(exact_matches) > 1:
        matches = exact_matches
    else:
        matches = [
            goal
            for goal in goals
            if normalized_reference
            and normalized_reference in " ".join(goal["content"].strip().casefold().split())
        ]

    if len(matches) == 1:
        return {"status": "matched", "goal": matches[0]}
    if matches:
        return {
            "status": "ambiguous",
            "matches": [goal["content"] for goal in matches],
        }
    return {"status": "not_found", "matches": []}


def _goal_resolution_failure(goal_reference: str, resolution: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": False,
        "resolution": resolution["status"],
        "goal_reference": goal_reference,
        "matching_goals": resolution.get("matches", []),
    }


def update_goal_status(goal_reference: str, status: str) -> Dict[str, Any]:
    """
    Update the status of an existing goal.
    
    Args:
        goal_reference: Human-readable reference to an existing active goal.
        status: Must be 'active', 'done', or 'dropped'.
    """
    try:
        resolution = _resolve_active_goal_reference(goal_reference)
        if resolution["status"] != "matched":
            return _goal_resolution_failure(goal_reference, resolution)

        goal = resolution["goal"]
        updated = db.update_goal_status(goal_id=goal["id"], status=status)
        if not updated:
            return _goal_resolution_failure(
                goal_reference,
                {"status": "not_found", "matches": []},
            )
        return {
            "success": True,
            "goal_content": goal["content"],
            "status": status,
        }
    except Exception as e:
        logger.exception("Error updating goal status for goal reference")
        return {"success": False, "error": str(e)}


def update_goal_target_date(goal_reference: str, target_date: str) -> Dict[str, Any]:
    """
    Change the target completion date of an EXISTING goal.

    Does not create a new goal and does not touch status or content. Use
    update_goal_status for status changes.

    Args:
        goal_reference: Human-readable reference to an existing active goal.
        target_date: New target date in ISO format 'YYYY-MM-DD HH:MM:SS'.
    """
    try:
        resolution = _resolve_active_goal_reference(goal_reference)
        if resolution["status"] != "matched":
            return _goal_resolution_failure(goal_reference, resolution)

        goal = resolution["goal"]
        updated = db.update_goal_target_date(
            goal_id=goal["id"],
            target_date=target_date,
        )
        if not updated:
            return _goal_resolution_failure(
                goal_reference,
                {"status": "not_found", "matches": []},
            )
        return {
            "success": True,
            "goal_content": goal["content"],
            "target_date": target_date,
        }
    except Exception as e:
        logger.exception("Error updating target date for goal reference")
        return {"success": False, "error": str(e)}


def update_multiple_goal_statuses(goal_ids: list, status: str) -> Dict[str, Any]:
    """
    Update the status of MULTIPLE existing goals in a single deterministic
    batch operation.

    Exists specifically for requests like "remove all my duplicate Java
    goals" or "mark these three as done" — updating goals one at a time via
    update_goal_status would need one tool-call round per goal, which can
    exceed the model's bounded tool-round budget. This does it in one round
    regardless of how many goals are involved.

    Args:
        goal_ids: Database IDs of the goals to update. Must come from the
            supplied ACTIVE GOALS context — never invented by the model.
        status: Must be 'active', 'done', or 'dropped'. Applied to every ID.
    """
    if not isinstance(goal_ids, list) or not goal_ids:
        return {"success": False, "error": "goal_ids must be a non-empty list of integers"}

    # Validate every ID up front (fail the whole batch on a malformed entry
    # rather than partially applying it), and dedupe so a repeated ID in the
    # model's list can't be processed twice.
    deduped_ids = []
    for goal_id in goal_ids:
        if isinstance(goal_id, bool) or not isinstance(goal_id, int):
            return {
                "success": False,
                "error": f"invalid goal_id in list: {goal_id!r} (must be an integer)",
            }
        if goal_id not in deduped_ids:
            deduped_ids.append(goal_id)

    if status not in ("active", "done", "dropped"):
        return {"success": False, "error": "status must be 'active', 'done', or 'dropped'"}

    updated_ids = []
    not_found_ids = []
    failed_ids = []
    for goal_id in deduped_ids:
        try:
            was_updated = db.update_goal_status(goal_id=goal_id, status=status)
        except Exception:
            logger.exception("Error updating goal status for ID %s in batch", goal_id)
            failed_ids.append(goal_id)
            continue

        if was_updated:
            updated_ids.append(goal_id)
        else:
            not_found_ids.append(goal_id)

    message = f"Updated {len(updated_ids)} goal(s) to '{status}'."
    if not_found_ids:
        message += f" {len(not_found_ids)} ID(s) not found: {not_found_ids}."
    if failed_ids:
        message += f" {len(failed_ids)} ID(s) failed to update: {failed_ids}."

    return {
        "success": len(updated_ids) > 0,
        "status": status,
        "updated_goal_ids": updated_ids,
        "not_found_goal_ids": not_found_ids,
        "failed_goal_ids": failed_ids,
        "message": message,
    }


# ==========================================
# REMINDER TOOLS
# ==========================================

def create_reminder(content: str, remind_at: str) -> Dict[str, Any]:
    """
    Create a new pending reminder.
    
    Args:
        content: What the user needs to be reminded about.
        remind_at: Datetime string in ISO format 'YYYY-MM-DD HH:MM:SS'.
    """
    try:
        reminder_id = db.create_reminder(content=content, remind_at=remind_at)
        return {"success": True, "reminder_id": reminder_id, "message": f"Reminder set successfully for {remind_at} with ID {reminder_id}."}
    except Exception as e:
        logger.exception("Error creating reminder")
        return {"success": False, "error": str(e)}


def get_pending_reminders() -> Dict[str, Any]:
    """Retrieve all currently pending reminders."""
    try:
        rows = db.get_pending_reminders()
        reminders = [dict(row) for row in rows]
        return {"success": True, "count": len(reminders), "reminders": reminders}
    except Exception as e:
        logger.exception("Error fetching pending reminders")
        return {"success": False, "error": str(e)}


def update_reminder_status(reminder_id: int, status: str) -> Dict[str, Any]:
    """
    Update the status of a reminder.
    
    Args:
        reminder_id: Database ID of the reminder.
        status: Must be 'pending', 'sent', or 'dismissed'.
    """
    try:
        updated = db.update_reminder_status(reminder_id=reminder_id, status=status)
        if not updated:
            return {"success": False, "error": f"Reminder ID {reminder_id} not found or no changes made."}
        return {"success": True,"reminder_id": reminder_id,"status": status}
    except Exception as e:
        logger.exception("Error updating reminder status for ID %s", reminder_id)
        return {"success": False, "error": str(e)}


# ==========================================
# TOOL DISPATCH MAP & GROQ SCHEMAS
# ==========================================

TOOL_MAP = {
    "create_goal": create_goal,
    "get_active_goals": get_active_goals,
    "update_goal_status": update_goal_status,
    "update_goal_target_date": update_goal_target_date,
    "update_multiple_goal_statuses": update_multiple_goal_statuses,
    "create_reminder": create_reminder,
    "get_pending_reminders": get_pending_reminders,
    "update_reminder_status": update_reminder_status,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": (
                "Create a NEW active goal for the user. Use this only when the "
                "user wants to create, add, or set a new goal. Do NOT use this "
                "tool to modify, complete, drop, delete, or remove an existing "
                "goal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Goal description."},
                    "goal_type": {
                        "type": "string",
                        "enum": ["daily", "mid-term", "long-term"],
                        "description": "Time horizon of the goal. Deduce contextually (e.g., 'today' = daily, 'this month' = mid-term).",
                    },
                    "target_date": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                        "description": "Optional completion target. If the user gives only a calendar date, provide 'YYYY-MM-DD'; it is stored as the end of that date. If a time is given, use 'YYYY-MM-DD HH:MM:SS'. If the user does not provide a deadline, send null or omit this property. Never invent a deadline.",
                    },
                },
                "required": ["content", "goal_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_goals",
            "description": "Get all active goals currently stored in the database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal_status",
            "description": (
                "Change the status of an EXISTING goal. Use status 'done' when "
                "the user completed the goal. Use status 'dropped' when the user "
                "says remove, delete, cancel, abandon, or get rid of the goal. "
                "A dropped goal is logically removed/cancelled and no longer "
                "appears in active goals, but is NOT physically deleted from the "
                "database. Use a human-readable goal_reference from the supplied "
                "ACTIVE GOALS context; never provide an internal database ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_reference": {
                        "type": "string",
                        "description": "Human-readable exact or distinctive partial reference to the existing goal.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "done", "dropped"],
                        "description": "New goal status.",
                    },
                },
                "required": ["goal_reference", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal_target_date",
            "description": (
                "Change the target completion date of an EXISTING goal, "
                "without altering its status or content. Use this when the "
                "user wants to reschedule, push back, move up, or otherwise "
                "change the deadline of a goal that already exists. The "
                "goal_reference must be a human-readable reference from the "
                "supplied ACTIVE GOALS context; never provide an internal ID. Do NOT use this to "
                "create a new goal or to change goal status/content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_reference": {
                        "type": "string",
                        "description": "Human-readable exact or distinctive partial reference to the existing goal.",
                    },
                    "target_date": {
                        "type": "string",
                        "description": "New target completion date. If the user gives only a calendar date, provide 'YYYY-MM-DD'; it is stored as the end of that date. If a time is given, use 'YYYY-MM-DD HH:MM:SS'. Never invent a date the user did not state.",
                    },
                },
                "required": ["goal_reference", "target_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_multiple_goal_statuses",
            "description": (
                "Update the status of MULTIPLE existing goals in a single call. "
                "Use it for clear group requests: remove/drop/complete/mark/change "
                "all matching goals, including duplicate goals (for example, "
                "'remove all my duplicate Java goals' or 'mark all my Java goals "
                "as done'). Select every matching ID from ACTIVE GOALS and call "
                "this once; do not ask for internal IDs or call the single-goal "
                "tool repeatedly. Ask for clarification only when the requested "
                "group itself is genuinely unclear."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Database IDs of the goals to update. Must come from the supplied ACTIVE GOALS context; never invent an ID.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "done", "dropped"],
                        "description": "New status applied to every goal in goal_ids.",
                    },
                },
                "required": ["goal_ids", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Set a reminder for the user at a specific future date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Reminder content."},
                    "remind_at": {
                        "type": "string",
                        "description": "Exact datetime to trigger reminder in 'YYYY-MM-DD HH:MM:SS' format. The datetime must come from the user's request or current application time; do not invent an arbitrary time.",
                    },
                },
                "required": ["content", "remind_at"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending_reminders",
            "description": "Retrieve all pending reminders.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_reminder_status",
            "description": "Update status of a reminder (e.g., dismiss or mark as sent).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "integer", "description": "Database ID of the reminder."},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "sent", "dismissed"],
                        "description": "New reminder status.",
                    },
                },
                "required": ["reminder_id", "status"],
            },
        },
    },
]


def registered_tool_names() -> frozenset[str]:
    """Return tool names that are both model-visible and executable.

    Keeping this check in the tools module makes the dispatcher the single
    source of truth: a schema without an implementation (or vice versa) is a
    configuration error, not a capability the model may attempt to use.
    """
    definition_names = {
        definition.get("function", {}).get("name")
        for definition in TOOL_DEFINITIONS
    }
    definition_names.discard(None)
    map_names = set(TOOL_MAP)
    if definition_names != map_names:
        raise RuntimeError(
            "Tool registry mismatch between TOOL_DEFINITIONS and TOOL_MAP: "
            f"schemas={sorted(definition_names)}, implementations={sorted(map_names)}"
        )
    return frozenset(definition_names)


REGISTERED_TOOL_NAMES = registered_tool_names()


def _tool_schema(tool_name: str) -> Dict[str, Any] | None:
    """Return the model-facing schema for a registered tool."""
    for definition in TOOL_DEFINITIONS:
        function = definition.get("function", {})
        if function.get("name") == tool_name:
            return function
    return None


def _validate_arguments(tool_name: str, arguments: Dict[str, Any]) -> str | None:
    """Perform lightweight validation against the tool definition."""
    schema = _tool_schema(tool_name)
    if schema is None:
        return f"Error: unknown tool '{tool_name}'"

    parameters = schema.get("parameters", {})
    properties = parameters.get("properties", {})
    required = parameters.get("required", [])

    missing = [name for name in required if name not in arguments]
    if missing:
        return (
            f"Error: missing required argument(s) for tool '{tool_name}': "
            f"{', '.join(missing)}"
        )

    unexpected = [name for name in arguments if name not in properties]
    if unexpected:
        return (
            f"Error: unexpected argument(s) for tool '{tool_name}': "
            f"{', '.join(unexpected)}"
        )

    for name, value in arguments.items():
        definition = properties[name]
        expected_type = definition.get("type")

        if value is None and name not in required:
            continue

        if expected_type == "string" and not isinstance(value, str):
            return f"Error: argument '{name}' for tool '{tool_name}' must be a string"
        if expected_type == "integer" and (
            isinstance(value, bool) or not isinstance(value, int)
        ):
            return f"Error: argument '{name}' for tool '{tool_name}' must be an integer"

        if name == "target_date" and isinstance(value, str):
            # A goal deadline often arrives from the model as a calendar date
            # (for example, "2026-08-20").  Preserve the strict calendar
            # validation while deterministically storing it as the end of that
            # date; reminders still require an exact future time.
            try:
                date_only = datetime.strptime(value, DATE_FORMAT)
            except ValueError:
                date_only = None
            if date_only and date_only.strftime(DATE_FORMAT) == value:
                arguments[name] = f"{value} 23:59:59"
                value = arguments[name]

        if name in ("target_date", "remind_at"):
            if not isinstance(value, str):
                return (
                    f"Error: argument '{name}' for tool '{tool_name}' must be a "
                    "datetime string or null"
                )

            try:
                parsed_datetime = datetime.strptime(value, DATETIME_FORMAT)
            except ValueError:
                return (
                    f"Error: argument '{name}' for tool '{tool_name}' must be a "
                    f"valid datetime in {DATETIME_FORMAT!r} format"
                )

            if parsed_datetime.strftime(DATETIME_FORMAT) != value:
                return (
                    f"Error: argument '{name}' for tool '{tool_name}' must use "
                    f"the exact {DATETIME_FORMAT!r} format"
                )

            if name == "remind_at":
                project_timezone = ZoneInfo("Asia/Kolkata")
                parsed_datetime = parsed_datetime.replace(tzinfo=project_timezone)
                if parsed_datetime <= datetime.now(project_timezone):
                    return f"Error: argument 'remind_at' for tool '{tool_name}' must be in the future"

        allowed_values = definition.get("enum")
        if allowed_values is not None and value not in allowed_values:
            return (
                f"Error: argument '{name}' for tool '{tool_name}' must be one of: "
                f"{', '.join(map(str, allowed_values))}"
            )

    return None


def execute_tool_call(tool_name: str, raw_arguments: Any) -> str:
    """Parse, validate, execute, and serialize one requested tool call."""
    func = TOOL_MAP.get(tool_name)
    if not func:
        logger.warning(
            "Tool validation failed: name=%s reason=unknown tool",
            tool_name,
        )
        return f"Error: unknown tool '{tool_name}'"

    try:
        if raw_arguments is None or raw_arguments == "":
            arguments = {}
        elif isinstance(raw_arguments, str):
            parsed_arguments = json.loads(raw_arguments)
            # Preserve the existing zero-argument-tool behavior for JSON null.
            arguments = {} if parsed_arguments is None else parsed_arguments
        else:
            arguments = raw_arguments
    except (json.JSONDecodeError, TypeError) as exc:
        reason = f"could not parse arguments: {exc}"
        logger.warning(
            "Tool validation failed: name=%s reason=%s",
            tool_name,
            reason,
        )
        return f"Error: could not parse arguments for tool '{tool_name}'"

    logger.debug(
        "execute_tool_call received request: name=%s parsed_arguments=%r",
        tool_name,
        arguments,
    )

    if not isinstance(arguments, dict):
        logger.warning(
            "Tool validation failed: name=%s reason=arguments must be a JSON object",
            tool_name,
        )
        return f"Error: arguments for tool '{tool_name}' must be a JSON object"

    validation_error = _validate_arguments(tool_name, arguments)
    if validation_error:
        logger.warning(
            "Tool validation failed: name=%s reason=%s",
            tool_name,
            validation_error,
        )
        return validation_error

    try:
        result = func(**arguments)
    except Exception as exc:
        logger.exception(
            "Tool function raised: name=%s exception=%s",
            tool_name,
            exc,
        )
        return f"Error running tool '{tool_name}': {exc}"

    logger.debug(
        "Tool succeeded: name=%s result_type=%s",
        tool_name,
        type(result).__name__,
    )

    if isinstance(result, str):
        return result

    try:
        return json.dumps(result)
    except (TypeError, ValueError) as exc:
        logger.exception("Could not serialize result from tool '%s'", tool_name)
        return f"Error: could not serialize result from tool '{tool_name}': {exc}"


if __name__ == "__main__":
    print("=== TESTING TOOLS LAYER ===")
    print("Executing safe read-only tests...")
    print("Active goals:", get_active_goals())
    print("Pending reminders:", get_pending_reminders())
