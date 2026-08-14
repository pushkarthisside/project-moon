import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
import db

logger = logging.getLogger(__name__)
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

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
        return {
            "success": False,
            "goal_id": e.goal_id,
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


def update_goal_status(goal_id: int, status: str) -> Dict[str, Any]:
    """
    Update the status of an existing goal.
    
    Args:
        goal_id: Database ID of the goal.
        status: Must be 'active', 'done', or 'dropped'.
    """
    try:
        updated = db.update_goal_status(goal_id=goal_id, status=status)
        if not updated:
            return {"success": False, "error": f"Goal ID {goal_id} not found"}
        return {"success": True, "goal_id": goal_id, "status": status}
    except Exception as e:
        logger.exception("Error updating goal status for ID %s", goal_id)
        return {"success": False, "error": str(e)}


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
                        "description": "Optional completion target. If the user explicitly provides a deadline, provide it as a string in 'YYYY-MM-DD HH:MM:SS' format. If the user does not provide a deadline, send null or omit this property. Never invent a deadline.",
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
                "database. The goal_id must match the existing goal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer", "description": "Database ID of the goal."},
                    "status": {
                        "type": "string",
                        "enum": ["active", "done", "dropped"],
                        "description": "New goal status.",
                    },
                },
                "required": ["goal_id", "status"],
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

            if name == "remind_at" and parsed_datetime <= datetime.now():
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
