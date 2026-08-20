import json
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import tools


class GoalDateValidationTests(unittest.TestCase):
    def _run_reminder_validation(self, remind_at: str, now: datetime):
        with patch.object(tools, "datetime") as datetime_mock, patch.dict(
            tools.TOOL_MAP,
            {"create_reminder": lambda **kwargs: {"success": True, "reminder_id": 1}},
        ):
            datetime_mock.strptime.side_effect = datetime.strptime
            datetime_mock.now.return_value = now
            result = tools.execute_tool_call(
                "create_reminder",
                json.dumps({"content": "Study Python", "remind_at": remind_at}),
            )
        return result, datetime_mock

    def test_future_asia_kolkata_reminder_is_accepted(self):
        future = datetime(2026, 8, 20, 13, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        result, datetime_mock = self._run_reminder_validation(
            "2026-08-20 14:00:00", future
        )

        self.assertNotIn("must be in the future", result)
        datetime_mock.now.assert_called_once_with(ZoneInfo("Asia/Kolkata"))

    def test_past_asia_kolkata_reminder_is_rejected(self):
        now = datetime(2026, 8, 20, 13, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        result, _ = self._run_reminder_validation("2026-08-20 12:00:00", now)

        self.assertIn("must be in the future", result)

    def test_reminder_validation_uses_project_timezone_not_host_timezone(self):
        now = datetime(2026, 8, 20, 13, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        result, datetime_mock = self._run_reminder_validation(
            "2026-08-20 14:00:00", now
        )

        self.assertNotIn("Error running tool", result)
        datetime_mock.now.assert_called_once_with(ZoneInfo("Asia/Kolkata"))

    def test_malformed_reminder_datetime_is_still_rejected(self):
        result = tools.execute_tool_call(
            "create_reminder",
            '{"content":"Study Python","remind_at":"August 20"}',
        )

        self.assertTrue(result.startswith("Error: argument 'remind_at'"))

    def test_create_goal_without_target_date_is_valid(self):
        recorded = {}

        def fake_create_goal(**kwargs):
            recorded.update(kwargs)
            return {"success": True, "goal_id": 42}

        with patch.dict(tools.TOOL_MAP, {"create_goal": fake_create_goal}):
            result = json.loads(tools.execute_tool_call(
                "create_goal",
                '{"content":"Learn Python","goal_type":"mid-term"}',
            ))

        self.assertTrue(result["success"])
        self.assertNotIn("target_date", recorded)

    def test_create_goal_with_null_target_date_is_valid(self):
        recorded = {}

        def fake_create_goal(**kwargs):
            recorded.update(kwargs)
            return {"success": True, "goal_id": 42}

        with patch.dict(tools.TOOL_MAP, {"create_goal": fake_create_goal}):
            result = json.loads(tools.execute_tool_call(
                "create_goal",
                '{"content":"Learn Python","goal_type":"mid-term","target_date":null}',
            ))

        self.assertTrue(result["success"])
        self.assertIsNone(recorded["target_date"])

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

    def test_empty_goal_target_date_is_rejected(self):
        result = tools.execute_tool_call(
            "create_goal",
            '{"content":"Learn Python","goal_type":"mid-term","target_date":""}',
        )
        self.assertTrue(result.startswith("Error: argument 'target_date'"))

    def test_unrelated_malformed_arguments_are_still_rejected(self):
        missing_content = tools.execute_tool_call(
            "create_goal",
            '{"goal_type":"mid-term"}',
        )
        unknown_argument = tools.execute_tool_call(
            "create_goal",
            '{"content":"Learn Python","goal_type":"mid-term","unexpected":true}',
        )

        self.assertTrue(missing_content.startswith("Error: missing required argument"))
        self.assertTrue(unknown_argument.startswith("Error: unexpected argument"))

    def test_update_goal_target_date_normalizes_date_only_value(self):
        recorded = {}

        def fake_update_goal_target_date(**kwargs):
            recorded.update(kwargs)
            return {"success": True, "goal_content": "Learn Python", "target_date": kwargs["target_date"]}

        arguments = json.dumps({"goal_reference": "Learn Python", "target_date": "2026-09-15"})
        with patch.dict(tools.TOOL_MAP, {"update_goal_target_date": fake_update_goal_target_date}):
            result = json.loads(tools.execute_tool_call("update_goal_target_date", arguments))

        self.assertTrue(result["success"])
        self.assertEqual(recorded["goal_reference"], "Learn Python")
        self.assertEqual(recorded["target_date"], "2026-09-15 23:59:59")

    def test_update_goal_target_date_rejects_malformed_date(self):
        result = tools.execute_tool_call(
            "update_goal_target_date",
            '{"goal_reference": "Learn Python", "target_date": "September 15"}',
        )
        self.assertTrue(result.startswith("Error: argument 'target_date'"))

    def test_update_goal_target_date_rejects_missing_goal_reference(self):
        result = tools.execute_tool_call(
            "update_goal_target_date",
            '{"target_date": "2026-09-15"}',
        )
        self.assertTrue(result.startswith("Error: missing required argument"))

    def test_update_goal_target_date_reports_goal_not_found(self):
        def fake_update_goal_target_date(**kwargs):
            return {"success": False, "error": "goal not found"}

        with patch.dict(tools.TOOL_MAP, {"update_goal_target_date": fake_update_goal_target_date}):
            result = json.loads(tools.execute_tool_call(
                "update_goal_target_date",
            '{"goal_reference": "Missing goal", "target_date": "2026-09-15"}',
            ))
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "goal not found")


if __name__ == "__main__":
    unittest.main()
