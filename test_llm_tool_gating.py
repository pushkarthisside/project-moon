import unittest
from types import SimpleNamespace
from unittest.mock import patch

import json

import llm
from tools import TOOL_DEFINITIONS


def response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return {"message": message, "content": content, "tool_calls": tool_calls}


def tool_call(name, arguments="{}", call_id="call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


PENDING_GOAL_DATE_PROMPT = """
## RECENT CONVERSATION
user: I want to learn Spring Boot. Make that a mid-term goal.
luna: I can add a goal for learning Spring Boot, but I need a target date to set the mid-term timeframe. When would you like to have this goal completed?
## KNOWN USER FACTS
No known facts.
"""


UNRELATED_CONVERSATION_PROMPT = """
## RECENT CONVERSATION
user: What do you think about Spring Boot?
luna: Spring Boot is a useful framework for building Java applications.
## KNOWN USER FACTS
No known facts.
"""


class GoalCreationFollowUpToolGatingTests(unittest.TestCase):
    def test_initial_goal_request_can_receive_clarification_response(self):
        with patch(
            "llm.get_completion",
            return_value=response("When would you like to complete it?"),
        ) as completion:
            result = llm.get_reply(
                "system",
                "I want to learn Spring Boot. Make that a mid-term goal.",
            )

        self.assertEqual(result["text"], "When would you like to complete it?")
        self.assertIsNotNone(completion.call_args.kwargs["tools"])

    def test_four_to_five_week_follow_up_enables_tools(self):
        self.assertTrue(
            llm._message_needs_tools("like in 4-5 weeks", PENDING_GOAL_DATE_PROMPT)
        )

    def test_next_month_follow_up_enables_tools(self):
        self.assertTrue(
            llm._message_needs_tools("next month", PENDING_GOAL_DATE_PROMPT)
        )

    def test_explicit_calendar_date_follow_up_enables_tools(self):
        self.assertTrue(
            llm._message_needs_tools("by September 20", PENDING_GOAL_DATE_PROMPT)
        )

    def test_weekday_follow_up_enables_tools(self):
        self.assertTrue(
            llm._message_needs_tools("this Friday", PENDING_GOAL_DATE_PROMPT)
        )

    def test_date_only_follow_up_enables_tools(self):
        self.assertTrue(
            llm._message_needs_tools("September 20", PENDING_GOAL_DATE_PROMPT)
        )

    def test_unrelated_date_does_not_enable_tools(self):
        self.assertFalse(
            llm._message_needs_tools("by September 20", UNRELATED_CONVERSATION_PROMPT)
        )

    def test_ordinary_follow_ups_do_not_enable_tools(self):
        for user_text in (
            "that's good",
            "okay",
            "thanks",
            "I'm tired",
            "I studied today",
            "what do you think about Spring Boot?",
        ):
            with self.subTest(user_text=user_text):
                self.assertFalse(
                    llm._message_needs_tools(user_text, PENDING_GOAL_DATE_PROMPT)
                )

    def test_pending_date_follow_up_can_execute_goal_creation(self):
        calls = [
            response(
                tool_calls=[
                    tool_call(
                        "create_goal",
                        json.dumps(
                            {
                                "content": "Learn Spring Boot",
                                "goal_type": "mid-term",
                                "target_date": "2026-09-22",
                            }
                        ),
                    )
                ]
            ),
            response("I created that mid-term goal."),
        ]
        with patch("llm.get_completion", side_effect=calls) as completion, patch(
            "llm.execute_tool_call",
            return_value=json.dumps({"success": True, "goal_id": 1}),
        ) as execute:
            result = llm.get_reply(
                PENDING_GOAL_DATE_PROMPT,
                "like in 4-5 weeks",
            )

        self.assertEqual(result["text"], "I created that mid-term goal.")
        self.assertIsNotNone(completion.call_args_list[0].kwargs["tools"])
        execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
