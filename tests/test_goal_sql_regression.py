import os
import tempfile
import unittest
from unittest.mock import patch

import db
import tools


class SqlGoalPersistenceTests(unittest.TestCase):
    def test_default_database_path_is_anchored_to_project(self):
        self.assertTrue(os.path.isabs(db.DB_PATH))
        self.assertEqual(
            os.path.normcase(os.path.dirname(db.DB_PATH)),
            os.path.normcase(
                os.path.join(os.path.dirname(os.path.abspath(db.__file__)), "data")
            ),
        )

    def test_created_goal_remains_active_and_resolvable_after_cwd_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "data", "moon.db")
            other_cwd = os.path.join(temp_dir, "other")
            os.makedirs(other_cwd)

            with patch.object(db, "DB_PATH", database_path):
                db.init_db()
                goal_id = db.create_goal("Learn SQL", "mid-term")

                original_cwd = os.getcwd()
                try:
                    os.chdir(other_cwd)
                    active_goals = db.get_active_goals()
                    result = tools.update_goal_status("Learn SQL", "done")
                finally:
                    os.chdir(original_cwd)

            self.assertEqual([row["id"] for row in active_goals], [goal_id])
            self.assertEqual(active_goals[0]["content"], "Learn SQL")
            self.assertEqual(result["success"], True)
            self.assertEqual(result["goal_content"], "Learn SQL")


if __name__ == "__main__":
    unittest.main()
