import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import llm
from memory import _should_attempt_memory_extraction
from prompt import LUNA_SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS, TOOL_MAP, registered_tool_names


def response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return {"message": message, "content": content, "tool_calls": tool_calls}


def tool_call(name, arguments="{}", call_id="call-1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


class ToolSafetyTests(unittest.TestCase):
    def test_registry_has_exactly_one_schema_and_implementation_per_tool(self):
        self.assertEqual(registered_tool_names(), frozenset(TOOL_MAP))
        self.assertEqual(registered_tool_names(), frozenset(item["function"]["name"] for item in TOOL_DEFINITIONS))

    def test_normal_conversation_does_not_receive_tool_schemas(self):
        with patch("llm.get_completion", return_value=response("That makes sense.")) as completion:
            result = llm.get_reply("system", "I had a long day.")
        self.assertEqual(result["text"], "That makes sense.")
        self.assertIsNone(completion.call_args.kwargs["tools"])

    def test_goal_statement_is_not_an_implicit_create_request(self):
        user_text = "I've decided that becoming a backend engineer is one of my main career goals."
        with patch("llm.get_completion", return_value=response("That sounds like a meaningful direction.")) as completion:
            result = llm.get_reply("system", user_text)
        self.assertEqual(result["text"], "That sounds like a meaningful direction.")
        self.assertIsNone(completion.call_args.kwargs["tools"])

    def test_explicit_goal_creation_executes_registered_tool(self):
        calls = [
            response(tool_calls=[tool_call("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}')]),
            response("I've added that as a goal."),
        ]
        with patch("llm.get_completion", side_effect=calls), patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": True, "goal_id": 1})
        ) as execute:
            result = llm.get_reply("system", "Create a goal to learn Python.")
        self.assertEqual(result["text"], "I've added that as a goal.")
        execute.assert_called_once_with("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}')

    def test_reminder_creation_and_retrieval_are_supported(self):
        create_calls = [
            response(tool_calls=[tool_call("create_reminder", '{"content":"Call Mum","remind_at":"2030-01-01 09:00:00"}')]),
            response("I'll remind you then."),
        ]
        with patch("llm.get_completion", side_effect=create_calls), patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": True, "reminder_id": 3})
        ) as execute:
            result = llm.get_reply("system", "Remind me to call Mum on 2030-01-01 at 09:00.")
        self.assertEqual(result["text"], "I'll remind you then.")
        execute.assert_called_once()
        retrieve_calls = [response(tool_calls=[tool_call("get_pending_reminders")]), response("You have one reminder coming up.")]
        with patch("llm.get_completion", side_effect=retrieve_calls), patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": True, "reminders": []})
        ):
            result = llm.get_reply("system", "What reminders do I have?")
        self.assertEqual(result["text"], "You have one reminder coming up.")

    def test_delete_all_goals_is_rejected_without_an_llm_or_tool_call(self):
        for user_text in (
            "Delete all my goals.",
            "Deletee all the goals for me.",
            "Remove all my goals.",
            "Clear my goals.",
        ):
            with self.subTest(user_text=user_text), patch("llm.get_completion") as completion, patch("llm.execute_tool_call") as execute:
                result = llm.get_reply("system", user_text)
            self.assertEqual(result["text"], llm.UNSUPPORTED_BULK_GOAL_DELETE_REPLY)
            self.assertFalse(result["state_change_attempted"])
            completion.assert_not_called()
            execute.assert_not_called()

    def test_fake_state_request_is_rejected_without_an_llm_or_tool_call(self):
        with patch("llm.get_completion") as completion, patch("llm.execute_tool_call") as execute:
            result = llm.get_reply("system", "Pretend you created a reminder for tomorrow.")
        self.assertEqual(result["text"], llm.NON_EXECUTING_STATE_REPLY)
        completion.assert_not_called()
        execute.assert_not_called()

    def test_invented_tool_call_cannot_produce_a_success_claim(self):
        with patch("llm.get_completion", return_value=response(tool_calls=[tool_call("erase_everything")])), patch("llm.execute_tool_call") as execute:
            result = llm.get_reply("system", "Please do the unavailable operation.", tools=TOOL_DEFINITIONS)
        self.assertEqual(result["text"], "That operation isn't currently available.")
        execute.assert_not_called()

    def test_failed_tool_never_gets_a_free_form_success_synthesis(self):
        first = response(tool_calls=[tool_call("create_reminder", '{"content":"Call Mum","remind_at":"2030-01-01 09:00:00"}')])
        with patch("llm.get_completion", return_value=first) as completion, patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": False, "error": "write failed"})
        ):
            result = llm.get_reply("system", "Remind me to call Mum in 2030.")
        self.assertEqual(result["text"], "The reminder was not created.")
        self.assertEqual(completion.call_count, 1)

    def test_state_change_request_without_a_tool_cannot_claim_success(self):
        with patch("llm.get_completion", return_value=response("Your reminder is set.")):
            result = llm.get_reply("system", "Remind me to call Mum tomorrow.")
        self.assertEqual(result["text"], "I couldn't complete that action safely.")

    def test_prompt_requests_thread_synthesis_and_natural_state_presentation(self):
        self.assertIn("Treat it as\na recent thread", LUNA_SYSTEM_PROMPT)
        self.assertIn("natural\n  conversational summary", LUNA_SYSTEM_PROMPT)
        self.assertIn("not an instruction to create structured state", LUNA_SYSTEM_PROMPT)

    def test_existing_memory_gate_still_skips_trivial_and_accepts_durable_input(self):
        self.assertFalse(_should_attempt_memory_extraction("thanks"))
        self.assertTrue(_should_attempt_memory_extraction("I want to become a backend engineer."))


if __name__ == "__main__":
    unittest.main()
