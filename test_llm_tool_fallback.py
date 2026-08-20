import json
import unittest
from unittest.mock import patch

import db
import tools
from llm import _summarize_tool_result


def tool_result(payload):
    return json.dumps(payload)


class ToolFallbackSummaryTests(unittest.TestCase):
    def test_get_active_goals_with_multiple_goals(self):
        result = tool_result({
            "success": True,
            "goals": [{"id": 1, "content": "Study Java"}, {"id": 2, "content": "Walk daily"}],
        })
        self.assertEqual(
            _summarize_tool_result("get_active_goals", result),
            "Your active goals include Study Java, and Walk daily.",
        )

    def test_get_active_goals_with_no_goals(self):
        self.assertEqual(
            _summarize_tool_result("get_active_goals", tool_result({"success": True, "goals": []})),
            "You have no active goals.",
        )

    def test_get_pending_reminders_with_multiple_reminders(self):
        result = tool_result({
            "success": True,
            "reminders": [
                {"id": 1, "content": "Pay rent", "remind_at": "2026-08-20 09:00:00"},
                {"id": 2, "content": "Call Mum"},
            ],
        })
        self.assertEqual(
            _summarize_tool_result("get_pending_reminders", result),
            "Pending reminders:\n- Pay rent — 2026-08-20 09:00:00\n- Call Mum",
        )

    def test_get_pending_reminders_with_no_reminders(self):
        self.assertEqual(
            _summarize_tool_result("get_pending_reminders", tool_result({"success": True, "reminders": []})),
            "You have no pending reminders.",
        )

    def test_failed_get_pending_reminders(self):
        self.assertEqual(
            _summarize_tool_result("get_pending_reminders", tool_result({"success": False, "error": "database error"})),
            "I couldn't retrieve your pending reminders.",
        )

    def test_duplicate_create_goal_failure(self):
        result = tool_result({
            "success": False,
            "goal_id": 7,
            "error": "duplicate active goal 7",
            "message": "Goal was not created because an identical active goal already exists.",
        })
        self.assertEqual(
            _summarize_tool_result("create_goal", result),
            "You already have an active goal like that.",
        )

    def test_duplicate_create_goal_includes_existing_content(self):
        result = tool_result({
            "success": False,
            "goal_id": 7,
            "existing_goal_content": "Learn Java backend development",
            "message": "Goal was not created because an identical active goal already exists.",
        })
        self.assertEqual(
            _summarize_tool_result("create_goal", result),
            "You already have an active goal: Learn Java backend development",
        )

    def test_generic_create_goal_failure(self):
        self.assertEqual(
            _summarize_tool_result("create_goal", tool_result({"success": False, "error": "database error"})),
            "The goal was not created.",
        )

    def test_successful_create_goal(self):
        self.assertEqual(
            _summarize_tool_result("create_goal", tool_result({"success": True, "goal_id": 7})),
            "Created the goal.",
        )

    def test_successful_update_goal_target_date(self):
        self.assertEqual(
            _summarize_tool_result(
                "update_goal_target_date",
                tool_result({"success": True, "goal_id": 5, "target_date": "2026-09-15 23:59:59"}),
            ),
            "Updated the goal's target date.",
        )

    def test_batch_goal_update_partial_success(self):
        result = tool_result({
            "success": True,
            "status": "done",
            "updated_goal_ids": [1],
            "not_found_goal_ids": [2],
            "failed_goal_ids": [3],
        })
        self.assertEqual(
            _summarize_tool_result("update_multiple_goal_statuses", result),
            "Updated 1 goal(s) to 'done'. 1 requested goal(s) were not found. 1 requested goal(s) could not be updated.",
        )

    def test_duplicate_tool_call_error_remains_safe(self):
        self.assertEqual(
            _summarize_tool_result(
                "create_goal",
                "Error: duplicate tool call for 'create_goal' with the same arguments was blocked in this interaction.",
            ),
            "One requested operation could not be completed.",
        )

    def test_create_goal_duplicate_includes_existing_content(self):
        duplicate = db.DuplicateActiveGoalError(7)
        with patch("tools.db.create_goal", side_effect=duplicate), patch(
            "tools.db.get_active_goals",
            return_value=[{"id": 7, "content": "Learn Java backend development"}],
        ):
            result = tools.create_goal("Learn Java backend development", "mid-term")

        self.assertEqual(
            result["existing_goal_content"],
            "Learn Java backend development",
        )


if __name__ == "__main__":
    unittest.main()
