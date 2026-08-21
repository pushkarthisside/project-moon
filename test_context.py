import unittest
from unittest.mock import patch

import context


def message(index, content):
    return {"role": "user" if index % 2 == 0 else "luna", "content": content}


def fact(index, content):
    return {"category": "test", "content": content, "importance": 5 - index % 5}


def goal(index, content):
    return {
        "id": index,
        "content": content,
        "type": "mid-term",
        "target_date": None,
    }


def reminder(index, content):
    return {"id": index, "content": content, "remind_at": "2030-01-01 09:00:00"}


class ContextBoundsTests(unittest.TestCase):
    def test_context_keys_are_unchanged(self):
        with patch.multiple(
            context,
            get_recent_messages=lambda limit: [],
            get_facts=lambda limit: [],
            get_active_goals=lambda: [],
            get_pending_reminders=lambda: [],
        ):
            result = context.build_context()

        self.assertEqual(
            set(result),
            {
                "current_datetime",
                "recent_messages",
                "facts_context",
                "goals_context",
                "reminders_context",
            },
        )

    def test_dynamic_context_counts_are_bounded(self):
        with patch.multiple(
            context,
            get_recent_messages=lambda limit: [message(i, f"message {i}") for i in range(25)],
            get_facts=lambda limit: [fact(i, f"fact {i}") for i in range(15)],
            get_active_goals=lambda: [goal(i, f"goal {i}") for i in range(20)],
            get_pending_reminders=lambda: [reminder(i, f"reminder {i}") for i in range(20)],
        ):
            result = context.build_context()

        self.assertEqual(len(result["recent_messages"].splitlines()), context.MAX_RECENT_MESSAGES)
        self.assertEqual(len(result["facts_context"].splitlines()), context.MAX_FACTS)
        self.assertEqual(len(result["goals_context"].splitlines()), context.MAX_ACTIVE_GOALS)
        self.assertEqual(len(result["reminders_context"].splitlines()), context.MAX_PENDING_REMINDERS)

    def test_long_content_is_truncated_without_mutating_source(self):
        long_text = "x" * 1000
        msg = message(0, long_text)
        fact_row = fact(0, long_text)
        goal_row = goal(0, long_text)
        reminder_row = reminder(0, long_text)

        formatted = "\n".join(
            (
                context.format_messages([msg]),
                context.format_facts([fact_row]),
                context.format_goals([goal_row]),
                context.format_reminders([reminder_row]),
            )
        )

        self.assertIn("…", formatted)
        self.assertNotIn(long_text, formatted)
        self.assertEqual(msg["content"], long_text)
        self.assertEqual(fact_row["content"], long_text)
        self.assertEqual(goal_row["content"], long_text)
        self.assertEqual(reminder_row["content"], long_text)

    def test_short_content_is_not_altered(self):
        self.assertEqual(context.format_messages([message(0, "hello")]), "user: hello")
        self.assertEqual(
            context.format_facts([fact(0, "likes Java")]),
            "- [test] likes Java",
        )
        self.assertEqual(
            context.format_goals([goal(1, "study DSA")]),
            "- [1] study DSA | type: mid-term",
        )
        self.assertEqual(
            context.format_reminders([reminder(1, "call Mum")]),
            "- [1] call Mum | remind_at: 2030-01-01 09:00:00",
        )

    def test_empty_states_remain_unchanged(self):
        self.assertEqual(context.format_messages([]), "No recent conversation.")
        self.assertEqual(context.format_facts([]), "No known facts.")
        self.assertEqual(context.format_goals([]), "No active goals.")
        self.assertEqual(context.format_reminders([]), "No pending reminders.")

    def test_formatted_context_remains_compatible_with_prompt(self):
        with patch.multiple(
            context,
            get_recent_messages=lambda limit: [message(0, "hello")],
            get_facts=lambda limit: [fact(0, "likes Java")],
            get_active_goals=lambda: [goal(1, "study DSA")],
            get_pending_reminders=lambda: [reminder(1, "call Mum")],
        ):
            prompt = context.get_formatted_system_prompt()

        self.assertIn("CURRENT DATETIME:", prompt)
        self.assertIn("user: hello", prompt)
        self.assertIn("- [test] likes Java", prompt)
        self.assertIn("- [1] study DSA | type: mid-term", prompt)
        self.assertIn("- [1] call Mum | remind_at: 2030-01-01 09:00:00", prompt)


if __name__ == "__main__":
    unittest.main()
