import json
import unittest
from unittest.mock import patch

import tools


class GoalDateValidationTests(unittest.TestCase):
    def test_valid_future_date_only_deadline_is_normalized_and_executed(self):
        recorded = {}

        def fake_create_goal(**kwargs):
            recorded.update(kwargs)
            return {"success": True, "goal_id": 42}

        arguments = json.dumps({
            "content": "Finish learning linked lists",
            "goal_type": "mid-term",
            "target_date": "2026-08-20",
        })
        with patch.dict(tools.TOOL_MAP, {"create_goal": fake_create_goal}):
            result = json.loads(tools.execute_tool_call("create_goal", arguments))

        self.assertTrue(result["success"])
        self.assertEqual(recorded["target_date"], "2026-08-20 23:59:59")

    def test_malformed_goal_date_is_still_rejected(self):
        result = tools.execute_tool_call(
            "create_goal",
            '{"content":"Finish learning linked lists","goal_type":"mid-term","target_date":"August 20"}',
        )
        self.assertTrue(result.startswith("Error: argument 'target_date'"))

    def test_update_goal_target_date_normalizes_date_only_value(self):
        recorded = {}

        def fake_update_goal_target_date(**kwargs):
            recorded.update(kwargs)
            return {"success": True, "goal_id": kwargs["goal_id"], "target_date": kwargs["target_date"]}

        arguments = json.dumps({"goal_id": 5, "target_date": "2026-09-15"})
        with patch.dict(tools.TOOL_MAP, {"update_goal_target_date": fake_update_goal_target_date}):
            result = json.loads(tools.execute_tool_call("update_goal_target_date", arguments))

        self.assertTrue(result["success"])
        self.assertEqual(recorded["goal_id"], 5)
        self.assertEqual(recorded["target_date"], "2026-09-15 23:59:59")

    def test_update_goal_target_date_rejects_malformed_date(self):
        result = tools.execute_tool_call(
            "update_goal_target_date",
            '{"goal_id": 5, "target_date": "September 15"}',
        )
        self.assertTrue(result.startswith("Error: argument 'target_date'"))

    def test_update_goal_target_date_rejects_missing_goal_id(self):
        result = tools.execute_tool_call(
            "update_goal_target_date",
            '{"target_date": "2026-09-15"}',
        )
        self.assertTrue(result.startswith("Error: missing required argument"))

    def test_update_goal_target_date_reports_goal_not_found(self):
        def fake_update_goal_target_date(**kwargs):
            return {"success": False, "error": f"Goal ID {kwargs['goal_id']} not found"}

        with patch.dict(tools.TOOL_MAP, {"update_goal_target_date": fake_update_goal_target_date}):
            result = json.loads(tools.execute_tool_call(
                "update_goal_target_date",
                '{"goal_id": 999, "target_date": "2026-09-15"}',
            ))
        self.assertFalse(result["success"])
        self.assertIn("999", result["error"])


if __name__ == "__main__":
    unittest.main()
