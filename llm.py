import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    raise ValueError("Missing required environment variable: GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)


def get_reply(system_prompt: str, user_text: str) -> str:
    """Get a completion response from the LLM provider (Groq)."""
    completion = groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    return completion.choices[0].message.content or "I couldn't generate a response."