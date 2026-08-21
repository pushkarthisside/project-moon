import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

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
    def test_successful_state_change_uses_deterministic_fallback_when_synthesis_fails(self):
        calls = [
            response(tool_calls=[tool_call("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}')]),
            llm.APIConnectionError(message="Groq unavailable", request=MagicMock()),
        ]
        with patch("llm.get_completion", side_effect=calls) as completion, patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": True, "goal_id": 1})
        ) as execute:
            result = llm.get_reply("system", "Create a goal to learn Python.")

        self.assertEqual(result["text"], "Created the goal.")
        self.assertTrue(result["state_change_attempted"])
        self.assertEqual(completion.call_count, 2)
        execute.assert_called_once_with("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}')

    def test_failed_state_change_keeps_existing_deterministic_failure(self):
        first = response(tool_calls=[tool_call("create_reminder", '{"content":"Call Mum","remind_at":"2030-01-01 09:00:00"}')])
        with patch("llm.get_completion", return_value=first) as completion, patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": False, "error": "write failed"})
        ):
            result = llm.get_reply("system", "Remind me to call Mum in 2030.")

        self.assertEqual(result["text"], "The reminder was not created.")
        self.assertEqual(completion.call_count, 1)

    def test_successful_state_change_keeps_synthesized_response(self):
        calls = [
            response(tool_calls=[tool_call("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}')]),
            response("I've added that as a goal."),
        ]
        with patch("llm.get_completion", side_effect=calls), patch(
            "llm.execute_tool_call", return_value=json.dumps({"success": True, "goal_id": 1})
        ):
            result = llm.get_reply("system", "Create a goal to learn Python.")

        self.assertEqual(result["text"], "I've added that as a goal.")

    def test_non_state_change_groq_failure_still_propagates(self):
        with patch(
            "llm.get_completion",
            side_effect=llm.APIConnectionError(message="Groq unavailable", request=MagicMock()),
        ):
            with self.assertRaises(llm.APIConnectionError):
                llm.get_reply("system", "I had a long day.")

    def test_multiple_tool_rounds_use_fallback_without_duplicate_execution(self):
        calls = [
            response(tool_calls=[tool_call("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}', "call-1")]),
            response(tool_calls=[tool_call("update_goal_status", '{"goal_reference":"Learn Python","status":"done"}', "call-2")]),
            llm.APIConnectionError(message="Groq unavailable", request=MagicMock()),
        ]
        with patch("llm.get_completion", side_effect=calls), patch(
            "llm.execute_tool_call",
            side_effect=[
                json.dumps({"success": True, "goal_id": 1}),
                json.dumps({"success": True, "goal_id": 1, "status": "done"}),
            ],
        ) as execute:
            result = llm.get_reply(
                "system",
                "Create a goal to learn Python, then mark it done.",
                max_tool_rounds=3,
            )

        self.assertEqual(result["text"], "Created the goal.\nUpdated the goal.")
        self.assertTrue(result["state_change_attempted"])
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(
            execute.call_args_list[0].args,
            ("create_goal", '{"content":"Learn Python","goal_type":"mid-term"}'),
        )
        self.assertEqual(
            execute.call_args_list[1].args,
            ("update_goal_status", '{"goal_reference":"Learn Python","status":"done"}'),
        )

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

    def test_learning_ambition_stays_conversational_without_goal_tools(self):
        with patch("llm.get_completion", return_value=response("Docker is worth exploring.")) as completion:
            result = llm.get_reply("system", "I want to learn Docker.")
        self.assertEqual(result["text"], "Docker is worth exploring.")
        self.assertIsNone(completion.call_args.kwargs["tools"])

    def test_state_change_detection_recognizes_goal_target_date_changes(self):
        for user_text in (
            "reschedule my goal",
            "change my goal deadline",
            "move my goal deadline to Sunday",
            "change the target date of my goal",
            "push my goal deadline to next week",
            "move the deadline of my Python goal",
        ):
            with self.subTest(user_text=user_text):
                self.assertTrue(llm._message_requests_state_change(user_text))

    def test_state_change_detection_preserves_existing_cases_and_rejects_ordinary_text(self):
        for user_text in (
            "create a goal",
            "complete my goal",
            "remove my goal",
            "set a reminder",
            "cancel my reminder",
        ):
            with self.subTest(user_text=user_text):
                self.assertTrue(llm._message_requests_state_change(user_text))

        for user_text in ("I had a long day.", "What should I do?", "Tell me about Python."):
            with self.subTest(user_text=user_text):
                self.assertFalse(llm._message_requests_state_change(user_text))

    def test_exact_quoted_goal_title_uses_deterministic_fallback_when_model_omits_tool(self):
        user_text = 'Mark "Finish learning linked lists" as done.'
        self.assertTrue(llm._message_requests_state_change(user_text))
        self.assertTrue(llm._message_needs_tools(user_text))

        with patch("llm.get_completion", return_value=response("I need an ID.")) as completion, patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": True,
                "goal_content": "Finish learning linked lists",
                "status": "done",
            }),
        ) as execute:
            result = llm.get_reply("system", user_text)

        self.assertEqual(result["text"], "Done — I marked 'Finish learning linked lists' as completed.")
        self.assertTrue(result["state_change_attempted"])
        self.assertIsNotNone(completion.call_args.kwargs["tools"])
        tool_name, raw_arguments = execute.call_args.args
        self.assertEqual(tool_name, "update_goal_status")
        self.assertEqual(
            json.loads(raw_arguments),
            {"goal_reference": "Finish learning linked lists", "status": "done"},
        )

    def test_unique_partial_goal_status_uses_deterministic_fallback_when_model_omits_tool(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": True,
                "goal_content": "Finish binary trees",
                "status": "done",
            }),
        ) as execute:
            result = llm.get_reply("system", "Mark my binary trees goal as done.")

        self.assertEqual(result["text"], "Done — I marked 'Finish binary trees' as completed.")
        self.assertEqual(
            json.loads(execute.call_args.args[1]),
            {"goal_reference": "binary trees", "status": "done"},
        )

    def test_ambiguous_goal_status_uses_tool_result_clarification_when_model_omits_tool(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": False,
                "resolution": "ambiguous",
                "goal_reference": "linked lists",
                "matching_goals": ["Finish learning linked lists", "Learn linked lists"],
            }),
        ) as execute:
            result = llm.get_reply("system", "Mark my linked lists goal as done.")

        self.assertEqual(
            result["text"],
            "You have a few active goals matching 'linked lists'. Which one do you mean?",
        )
        self.assertNotIn("ID", result["text"])
        self.assertEqual(
            json.loads(execute.call_args.args[1]),
            {"goal_reference": "linked lists", "status": "done"},
        )

    def test_not_found_goal_status_uses_tool_result_when_model_omits_tool(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": False,
                "resolution": "not_found",
                "goal_reference": "quantum teleportation",
            }),
        ) as execute:
            result = llm.get_reply("system", "Mark my quantum teleportation goal as done.")

        self.assertEqual(result["text"], "I couldn't find an active goal matching 'quantum teleportation'.")
        self.assertEqual(
            json.loads(execute.call_args.args[1]),
            {"goal_reference": "quantum teleportation", "status": "done"},
        )

    def test_exact_goal_deadline_uses_deterministic_fallback_when_model_omits_tool(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": True,
                "goal_content": "Finish learning linked lists",
                "target_date": "2026-08-26 23:59:59",
            }),
        ) as execute, patch(
            "llm._parse_goal_target_date", return_value="2026-08-26"
        ):
            result = llm.get_reply(
                "system",
                'Move "Finish learning linked lists" deadline to next Wednesday.',
            )

        self.assertEqual(result["text"], "Updated the target date for 'Finish learning linked lists'.")
        self.assertEqual(
            json.loads(execute.call_args.args[1]),
            {"goal_reference": "Finish learning linked lists", "target_date": "2026-08-26"},
        )

    def test_unique_partial_goal_deadline_uses_deterministic_fallback_when_model_omits_tool(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": True,
                "goal_content": "Finish binary trees",
                "target_date": "2026-08-26 23:59:59",
            }),
        ) as execute, patch("llm._parse_goal_target_date", return_value="2026-08-26"):
            result = llm.get_reply(
                "system",
                "Move my binary trees goal deadline to next Wednesday.",
            )

        self.assertEqual(result["text"], "Updated the target date for 'Finish binary trees'.")
        self.assertEqual(
            json.loads(execute.call_args.args[1]),
            {"goal_reference": "binary trees", "target_date": "2026-08-26"},
        )

    def test_ambiguous_goal_deadline_uses_tool_result_clarification_when_model_omits_tool(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({
                "success": False,
                "resolution": "ambiguous",
                "goal_reference": "linked lists",
                "matching_goals": ["Finish learning linked lists", "Learn linked lists"],
            }),
        ) as execute, patch("llm._parse_goal_target_date", return_value="2026-08-26"):
            result = llm.get_reply(
                "system",
                "Move my linked lists goal deadline to next Wednesday.",
            )

        self.assertEqual(
            result["text"],
            "You have a few active goals matching 'linked lists'. Which one do you mean?",
        )
        self.assertEqual(
            json.loads(execute.call_args.args[1]),
            {"goal_reference": "linked lists", "target_date": "2026-08-26"},
        )

    def test_next_weekday_deadline_parser_is_deterministic(self):
        now = datetime(2026, 8, 20, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.assertEqual(llm._parse_goal_target_date("next Wednesday", now), "2026-08-26")

    def test_single_goal_fallback_does_not_intercept_scoped_batch_requests(self):
        with patch("llm.get_completion", return_value=response("I need an ID.")), patch(
            "llm.execute_tool_call"
        ) as execute:
            result = llm.get_reply("system", "Mark all my Java goals as done.")

        self.assertEqual(result["text"], "I couldn't complete that action safely.")
        execute.assert_not_called()

    def test_update_goal_target_date_executes_with_state_change_tracking(self):
        calls = [
            response(tool_calls=[tool_call(
                "update_goal_target_date",
                '{"goal_reference": "Learn Python", "target_date": "2026-09-15 23:59:59"}',
            )]),
            response("I've moved that deadline to September 15."),
        ]
        with patch("llm.get_completion", side_effect=calls), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({"success": True, "goal_content": "Learn Python", "target_date": "2026-09-15 23:59:59"}),
        ) as execute:
            result = llm.get_reply("system", "Change my goal deadline to September 15.")
        self.assertEqual(result["text"], "I've moved that deadline to September 15.")
        self.assertTrue(result["state_change_attempted"])
        execute.assert_called_once_with(
            "update_goal_target_date",
            '{"goal_reference": "Learn Python", "target_date": "2026-09-15 23:59:59"}',
        )

    def test_update_goal_target_date_uses_tailored_fallback_when_synthesis_unavailable(self):
        calls = [
            response(tool_calls=[tool_call(
                "update_goal_target_date",
                '{"goal_reference": "Learn Python", "target_date": "2026-09-15 23:59:59"}',
            )]),
        ]
        with patch("llm.get_completion", side_effect=calls), patch(
            "llm.execute_tool_call",
            return_value=json.dumps({"success": True, "goal_content": "Learn Python", "target_date": "2026-09-15 23:59:59"}),
        ):
            result = llm.get_reply(
                "system",
                "Change my goal deadline to September 15.",
                max_tool_rounds=1,
            )
        self.assertTrue(result["state_change_attempted"])
        self.assertEqual(result["text"], "Updated the target date for 'Learn Python'.")
        self.assertNotEqual(result["text"], "The requested operation completed.")

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

    def test_scoped_bulk_goal_requests_are_not_rejected_by_the_prefilter(self):
        for user_text in (
            "Remove all my Java goals.",
            "Complete all my Python goals.",
            "Drop all my exam goals.",
        ):
            with self.subTest(user_text=user_text):
                self.assertFalse(llm._is_unsupported_bulk_goal_deletion(user_text))

    def test_unscoped_bulk_goal_requests_remain_rejected_by_the_prefilter(self):
        for user_text in (
            "Delete all my goals.",
            "Remove every goal.",
            "Clear my goals.",
        ):
            with self.subTest(user_text=user_text):
                self.assertTrue(llm._is_unsupported_bulk_goal_deletion(user_text))

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
        self.assertIn("persist it or offer to create a goal unless", LUNA_SYSTEM_PROMPT)
        self.assertIn("A target\n  date is optional", LUNA_SYSTEM_PROMPT)
        self.assertIn("confirm it briefly and naturally", LUNA_SYSTEM_PROMPT)

    def test_prompt_requires_deterministic_goal_reference_tool_selection(self):
        self.assertIn("exact active\n  goal title", LUNA_SYSTEM_PROMPT)
        self.assertIn("with that\n  title as goal_reference", LUNA_SYSTEM_PROMPT)
        self.assertIn("Only report that a goal was not found\n  after the tool returns a not-found result", LUNA_SYSTEM_PROMPT)
        self.assertIn("If a non-exact reference matches multiple active goals", LUNA_SYSTEM_PROMPT)
        self.assertIn("user for an internal database ID", LUNA_SYSTEM_PROMPT)
        self.assertIn("do not ask for\n  an ID", LUNA_SYSTEM_PROMPT)

    def test_existing_memory_gate_still_skips_trivial_and_accepts_durable_input(self):
        self.assertFalse(_should_attempt_memory_extraction("thanks"))
        self.assertTrue(_should_attempt_memory_extraction("I want to become a backend engineer."))


if __name__ == "__main__":
    unittest.main()
