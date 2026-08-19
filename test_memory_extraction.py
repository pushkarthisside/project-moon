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
