import os
import tempfile
import unittest
from unittest.mock import patch

import db
import tools


class BatchGoalSafetyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._db_path_patch = patch.object(db, "DB_PATH", self._tmp.name)
        self._db_path_patch.start()
        self.addCleanup(self._db_path_patch.stop)
        self.addCleanup(
            lambda: os.path.exists(self._tmp.name) and os.remove(self._tmp.name)
        )
        db.init_db()

    def _create_goal(self, content: str) -> int:
        return db.create_goal(content, "mid-term")

    def _status(self, goal_id: int) -> str:
        conn = db.get_connection()
        try:
            return conn.execute(
                "SELECT status FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()["status"]
        finally:
            conn.close()

    def test_valid_active_goals_are_updated(self):
        first_id = self._create_goal("Study Java")
        second_id = self._create_goal("Practice DSA")

        result = tools.update_multiple_goal_statuses(
            [first_id, second_id], "done"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["updated_goal_ids"], [first_id, second_id])
        self.assertEqual(result["inactive_goal_ids"], [])
        self.assertEqual(self._status(first_id), "done")
        self.assertEqual(self._status(second_id), "done")

    def test_completed_goal_is_not_reactivated(self):
        goal_id = self._create_goal("Finish DBMS revision")
        db.update_goal_status(goal_id, "done")

        result = tools.update_multiple_goal_statuses([goal_id], "active")

        self.assertFalse(result["success"])
        self.assertEqual(result["updated_goal_ids"], [])
        self.assertEqual(result["inactive_goal_ids"], [goal_id])
        self.assertEqual(self._status(goal_id), "done")

    def test_dropped_goal_is_not_reactivated(self):
        goal_id = self._create_goal("Learn Rust")
        db.update_goal_status(goal_id, "dropped")

        result = tools.update_multiple_goal_statuses([goal_id], "active")

        self.assertFalse(result["success"])
        self.assertEqual(result["updated_goal_ids"], [])
        self.assertEqual(result["inactive_goal_ids"], [goal_id])
        self.assertEqual(self._status(goal_id), "dropped")

    def test_stale_id_does_not_modify_active_goals_or_claim_success(self):
        active_goal_id = self._create_goal("Read operating systems notes")

        result = tools.update_multiple_goal_statuses([999999], "done")

        self.assertFalse(result["success"])
        self.assertEqual(result["updated_goal_ids"], [])
        self.assertEqual(result["inactive_goal_ids"], [999999])
        self.assertEqual(self._status(active_goal_id), "active")
        self.assertIn("not active or no longer exist", result["message"])

    def test_mixed_batch_never_reactivates_inactive_goals(self):
        active_goal_id = self._create_goal("Build portfolio")
        completed_goal_id = self._create_goal("Finish networking course")
        db.update_goal_status(completed_goal_id, "done")

        result = tools.update_multiple_goal_statuses(
            [active_goal_id, completed_goal_id], "active"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["updated_goal_ids"], [active_goal_id])
        self.assertEqual(result["inactive_goal_ids"], [completed_goal_id])
        self.assertEqual(self._status(active_goal_id), "active")
        self.assertEqual(self._status(completed_goal_id), "done")

    def test_existing_valid_batch_deduplicates_ids(self):
        goal_id = self._create_goal("Practice system design")

        result = tools.update_multiple_goal_statuses([goal_id, goal_id], "dropped")

        self.assertTrue(result["success"])
        self.assertEqual(result["updated_goal_ids"], [goal_id])
        self.assertEqual(result["inactive_goal_ids"], [])
        self.assertEqual(self._status(goal_id), "dropped")


if __name__ == "__main__":
    unittest.main()
