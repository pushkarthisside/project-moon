import unittest

from bot import _plain_text_for_telegram


class TelegramPlainTextTests(unittest.TestCase):
    def test_common_markdown_delimiters_are_not_sent_literally(self):
        self.assertEqual(
            _plain_text_for_telegram("**Important** and *gently*\n```python\nprint('hi')\n```"),
            "Important and gently\nprint('hi')\n",
        )


if __name__ == "__main__":
    unittest.main()
