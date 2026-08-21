import json
import unittest
from unittest.mock import patch

import tools
from llm import _summarize_tool_result


def goal(goal_id, content):
    return {"id": goal_id, "content": content, "type": "mid-term", "target_date": None}


class GoalReferenceTests(unittest.TestCase):
    def test_exact_unique_match(self):
        with patch.object(tools.db, "get_active_goals", return_value=[goal(1, "Finish learning linked lists")]):
            result = tools._resolve_active_goal_reference("Finish learning linked lists")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["goal"]["id"], 1)

    def test_unique_partial_match(self):
        with patch.object(tools.db, "get_active_goals", return_value=[goal(1, "Finish learning linked lists")]):
            result = tools._resolve_active_goal_reference("learning linked lists")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["goal"]["id"], 1)

    def test_no_match(self):
        with patch.object(tools.db, "get_active_goals", return_value=[goal(1, "Finish learning linked lists")]):
            result = tools._resolve_active_goal_reference("Learn databases")
        self.assertEqual(result, {"status": "not_found", "matches": []})

    def test_multiple_matching_goals_are_ambiguous(self):
        rows = [goal(1, "Finish learning linked lists"), goal(2, "Practice linked lists")]
        with patch.object(tools.db, "get_active_goals", return_value=rows):
            result = tools._resolve_active_goal_reference("linked lists")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["matches"], [row["content"] for row in rows])

    def test_matching_is_case_insensitive(self):
        with patch.object(tools.db, "get_active_goals", return_value=[goal(1, "Finish learning linked lists")]):
            result = tools._resolve_active_goal_reference("FINISH LEARNING LINKED LISTS")
        self.assertEqual(result["status"], "matched")

    def test_successful_status_update_resolves_reference(self):
        with patch.object(tools.db, "get_active_goals", return_value=[goal(26, "Finish learning linked lists")]), patch.object(
            tools.db, "update_goal_status", return_value=True
        ) as update:
            result = tools.update_goal_status("Finish learning linked lists", "done")
        self.assertEqual(result, {
            "success": True,
            "goal_content": "Finish learning linked lists",
            "status": "done",
        })
        update.assert_called_once_with(goal_id=26, status="done")

    def test_successful_target_date_update_resolves_reference(self):
        with patch.object(tools.db, "get_active_goals", return_value=[goal(26, "Finish learning linked lists")]), patch.object(
            tools.db, "update_goal_target_date", return_value=True
        ) as update:
            result = tools.update_goal_target_date("learning linked lists", "2026-08-26 23:59:59")
        self.assertEqual(result, {
            "success": True,
            "goal_content": "Finish learning linked lists",
            "target_date": "2026-08-26 23:59:59",
        })
        update.assert_called_once_with(goal_id=26, target_date="2026-08-26 23:59:59")

    def test_ambiguous_status_update_does_not_modify_goal(self):
        rows = [goal(1, "Finish learning linked lists"), goal(2, "Practice linked lists")]
        with patch.object(tools.db, "get_active_goals", return_value=rows), patch.object(
            tools.db, "update_goal_status"
        ) as update:
            result = tools.update_goal_status("linked lists", "done")
        self.assertFalse(result["success"])
        self.assertEqual(result["resolution"], "ambiguous")
        update.assert_not_called()

    def test_user_facing_results_do_not_expose_database_ids(self):
        for tool_name, result in (
            (
                "update_goal_status",
                {"success": True, "goal_content": "Finish learning linked lists", "status": "done"},
            ),
            (
                "update_goal_target_date",
                {"success": True, "goal_content": "Finish learning linked lists", "target_date": "2026-08-26 23:59:59"},
            ),
        ):
            summary = _summarize_tool_result(tool_name, json.dumps(result))
            self.assertNotIn("goal_id", summary)
            self.assertNotIn("database", summary.lower())
            self.assertNotIn("26", summary)

    def test_model_facing_update_schemas_use_goal_reference(self):
        schemas = {
            item["function"]["name"]: item["function"]
            for item in tools.TOOL_DEFINITIONS
        }
        for tool_name in ("update_goal_status", "update_goal_target_date"):
            function = schemas[tool_name]
            self.assertIn("goal_reference", function["parameters"]["properties"])
            self.assertNotIn("goal_id", function["parameters"]["properties"])
            self.assertIn("goal_reference", function["parameters"]["required"])


if __name__ == "__main__":
    unittest.main()
