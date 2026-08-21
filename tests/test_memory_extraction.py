import unittest
from types import SimpleNamespace
from unittest.mock import patch

import memory


def memory_client_with_content(content):
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    create = unittest.mock.Mock(return_value=completion)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


class MemoryExtractionTests(unittest.TestCase):
    def setUp(self):
        self.facts = patch("memory.get_facts", return_value=[])
        self.facts.start()
        self.addCleanup(self.facts.stop)

    def test_explicit_durable_statements_are_allowed_by_memory_gate(self):
        for user_text in (
            "I want to learn Java backend development.",
            "My goal is to get an internship by fourth semester.",
            "I prefer studying in the morning.",
            "Remember that I use Java for DSA.",
        ):
            with self.subTest(user_text=user_text):
                self.assertTrue(memory._should_attempt_memory_extraction(user_text))

    def test_questions_and_read_only_lookups_are_skipped_by_memory_gate(self):
        for user_text in (
            "What do you remember about me?",
            "What are my active goals?",
            "Show my reminders",
            "Get my active goals",
        ):
            with self.subTest(user_text=user_text):
                self.assertFalse(memory._should_attempt_memory_extraction(user_text))

    def test_skipped_lookup_does_not_call_memory_model(self):
        client = memory_client_with_content('{"facts":[]}')

        self.assertEqual(memory.extract_memories("What do you remember about me?", client), [])
        client.chat.completions.create.assert_not_called()

    def test_existing_trivial_and_transient_messages_remain_skipped(self):
        for user_text in ("Thanks", "Okay", "I'm tired today"):
            with self.subTest(user_text=user_text):
                self.assertFalse(memory._should_attempt_memory_extraction(user_text))

    def test_valid_json_returns_validated_memory_and_uses_memory_model(self):
        client = memory_client_with_content(
            '{"facts":[{"category":"career","content":"Wants to become a backend engineer","importance":4}]}'
        )
        result = memory.extract_memories("I want to become a backend engineer.", client)
        self.assertEqual(result, [{"category": "career", "content": "Wants to become a backend engineer", "importance": 4}])
        self.assertEqual(client.chat.completions.create.call_args.kwargs["model"], memory.MEMORY_MODEL)
        self.assertNotIn("response_format", client.chat.completions.create.call_args.kwargs)

    def test_empty_memory_json_returns_no_memory(self):
        client = memory_client_with_content('{"facts":[]}')
        self.assertEqual(memory.extract_memories("I ate lunch today.", client), [])

    def test_malformed_model_output_is_not_saved_as_memory(self):
        client = memory_client_with_content("You should remember that the user likes backend work.")
        self.assertEqual(memory.extract_memories("I want to become a backend engineer.", client), [])


if __name__ == "__main__":
    unittest.main()
