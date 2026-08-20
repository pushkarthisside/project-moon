import unittest

from bot import _needs_active_goal_context, _plain_text_for_telegram


class TelegramPlainTextTests(unittest.TestCase):
    def test_common_markdown_delimiters_are_not_sent_literally(self):
        self.assertEqual(
            _plain_text_for_telegram("**Important** and *gently*\n```python\nprint('hi')\n```"),
            "Important and gently\nprint('hi')\n",
        )

    def test_deadline_changes_include_active_goal_context(self):
        for user_text in (
            "Move my goal deadline to Sunday.",
            "Change the target date of my Python goal.",
            "Reschedule my goal.",
            "Change my goal deadline.",
            "Push my goal deadline to next week.",
            "Move the deadline of my goal.",
        ):
            with self.subTest(user_text=user_text):
                self.assertTrue(_needs_active_goal_context(user_text))

    def test_goal_context_preserves_creation_lookup_and_removal_behavior(self):
        self.assertFalse(_needs_active_goal_context("Create a new goal to learn Python."))
        self.assertFalse(_needs_active_goal_context("I had a long day."))
        self.assertTrue(_needs_active_goal_context("What are my active goals?"))
        self.assertTrue(_needs_active_goal_context("Complete my goal."))
        self.assertTrue(_needs_active_goal_context("Remove my goal."))


if __name__ == "__main__":
    unittest.main()
