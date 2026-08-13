import logging
from typing import Any, Dict, Optional
import db

logger = logging.getLogger(__name__)

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
            "description": "Create a new active goal for the user.",
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
                        "type": "string",
                        "description": "Optional completion target in 'YYYY-MM-DD HH:MM:SS' format. Use null/omit when no deadline was explicitly given. Do not invent a deadline.",
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
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal_status",
            "description": "Update the status of a specific goal (e.g., mark as done or dropped).",
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


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Safely resolve and execute a requested tool function."""
    func = TOOL_MAP.get(tool_name)
    if not func:
        return {"success": False, "error": f"Tool '{tool_name}' is not recognized."}
    
    try:
        return func(**arguments)
    except TypeError as e:
        return {"success": False, "error": f"Invalid arguments for tool '{tool_name}': {e}"}


if __name__ == "__main__":
    print("=== TESTING TOOLS LAYER ===")
    print("Executing safe read-only tests...")
    print("Active goals:", get_active_goals())
    print("Pending reminders:", get_pending_reminders())