import json
import logging
import os
from dotenv import load_dotenv
from groq import Groq
from db import create_fact, fact_exists, get_facts

load_dotenv()

logger = logging.getLogger(__name__)

MEMORY_EXTRACTOR_PROMPT = """
You are the Memory Gatekeeper for Project Moon.
Analyze the provided user text and extract durable, long-term facts worth remembering about the user (e.g., goals, studies, preferences, identity, habits).

CRITICAL RULES:
1. Extract ONLY facts explicitly stated by the user.
2. Do NOT invent, assume, or extrapolate facts. In particular, never infer
   the user's current semester or year, age, location, academic year, current
   activity, relationship status, employment status, or other circumstances
   unless the user explicitly states them.
3. A goal or deadline must not be converted into an assumed current state.
   Do not infer current semester/year from a deadline.
4. Preserve the meaning and qualifiers of the original statement, including
   "wants to", "plans to", "before", "by", "hopes to", "considering",
   "currently", and "previously". Do not strengthen an intention into an
   existing or current status.
5. For example, if the user says:
   "I want to get a software engineering internship before my 4th semester ends."
   the valid fact is:
   "Wants to get a software engineering internship before the end of 4th semester."
   The following are invalid and must not be extracted:
   - "Currently pursuing a software engineering internship."
   - "Currently in 3rd semester."
   - "Has started applying for internships."
6. Ignore temporary states ("I'm tired"), transient thoughts, or questions.
7. Output MUST be valid JSON with the following structure:
{
  "facts": [
    {"category": "education", "content": "Studying Java and DSA", "importance": 4}
  ]
}
If no durable facts are present, return: {"facts": []}
"""


def _validate_extracted_facts(data: object) -> list[dict]:
    """Return only fact candidates that match the expected safe shape."""
    if not isinstance(data, dict):
        return []

    facts = data.get("facts")
    if not isinstance(facts, list):
        return []

    valid_facts = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue

        content = fact.get("content")
        category = fact.get("category")
        importance = fact.get("importance")

        if not isinstance(content, str) or not content.strip():
            continue
        if not isinstance(category, str) or not category.strip():
            continue
        if isinstance(importance, bool) or not isinstance(importance, int):
            continue
        if not 1 <= importance <= 5:
            continue

        valid_facts.append({
            "category": category.strip(),
            "content": content.strip(),
            "importance": importance,
        })

    return valid_facts


def extract_memories(user_text: str, client: Groq, model: str = "llama-3.3-70b-versatile") -> list[dict]:
    """Extract durable facts strictly from the user's input."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": MEMORY_EXTRACTOR_PROMPT},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return _validate_extracted_facts(data)
    except Exception as exc:
        logger.error("Failed to extract memories: %s", exc)
        return []


def save_memories(extracted_facts: list[dict]) -> int:
    """Save new facts to the database, skipping duplicates."""
    saved_count = 0
    if not isinstance(extracted_facts, list):
        return 0

    for fact in extracted_facts:
        if not isinstance(fact, dict):
            continue

        # Keep this boundary defensive even when called independently of
        # extract_memories().
        validated = _validate_extracted_facts({"facts": [fact]})
        if not validated:
            continue

        fact = validated[0]
        content = fact["content"]

        try:
            # Prevent duplicate insertion using db.py's normalized exact match.
            if fact_exists(content):
                logger.info("Skipping duplicate memory candidate: %r", content)
                continue

            create_fact(**fact)
            saved_count += 1
        except Exception as exc:
            logger.error("Failed to save memory candidate %r: %s", content, exc)
            continue

    return saved_count


def retrieve_memories(limit: int = 10) -> list[dict]:
    """
    Retrieve top curated facts ordered by importance and recency.
    Note: Opt-in read operation; does not automatically update last_referenced.
    """
    rows = get_facts(limit=limit)
    return [dict(row) for row in rows]


def process_turn_memory(user_text: str, client: Groq) -> int:
    """
    Orchestrates the extraction and saving pipeline for a turn.
    Takes only user_text to enforce the boundary between user input and assistant context.
    """
    extracted = extract_memories(user_text, client)
    if extracted:
        return save_memories(extracted)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise SystemExit(
            "GROQ_API_KEY is required for the standalone memory runner."
        )

    client = Groq(api_key=api_key)
    examples = [
        "I've decided I'm going to focus on backend development this year.",
        "I'm currently studying Java and DSA.",
        "I want to get a software engineering internship before my 4th semester ends.",
        "I ate biryani today for lunch.",
        "Bro I'm so bored right now.",
        "I'm tired.",
        "That movie was crazy.",
    ]

    for user_text in examples:
        extracted = extract_memories(user_text, client)
        saved_count = save_memories(extracted)
        print(f"User: {user_text}")
        print(f"Extracted facts: {extracted}")
        print(f"Saved count: {saved_count}")

    print("Stored facts:")
    for fact in retrieve_memories():
        print(fact)
