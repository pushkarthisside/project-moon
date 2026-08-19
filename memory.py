import json
import logging
import os
import re
import time
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, RateLimitError
from db import create_fact, fact_exists, get_facts

load_dotenv()

logger = logging.getLogger(__name__)


MEMORY_MODEL = os.getenv("GROQ_MEMORY_MODEL", "openai/gpt-oss-20b")

MAX_GROQ_RETRIES = 1
RETRY_BACKOFF_SECONDS = (0.5,)

_TRIVIAL_MEMORY_MESSAGES = frozenset({
    "ok",
    "okay",
    "k",
    "lol",
    "lmao",
    "thanks",
    "thank you",
    "yeah",
    "yep",
    "nope",
    "cool",
    "nice",
    "sure",
    "hi",
    "hello",
    "hey",
    "what",
    "huh",
    "why",
    "how",
    "good morning",
    "good night",
})

_TRANSIENT_MEMORY_PATTERNS = (
    r"^(?:bro\s+)?i['’]?m\s+(?:so\s+)?(?:tired|bored|sleepy|hungry)(?:\s+(?:right\s+now|today))?$",
    r"^(?:what\s+should\s+i\s+do|that['’]?s\s+crazy)$",
)


def _should_attempt_memory_extraction(user_text: str) -> bool:
    """Return whether text is informative enough to ask the memory LLM about."""
    if not isinstance(user_text, str):
        return False

    normalized = user_text.strip().lower().strip("!?.,;:")
    if not normalized or normalized in _TRIVIAL_MEMORY_MESSAGES:
        return False
    return not any(
        re.fullmatch(pattern, normalized)
        for pattern in _TRANSIENT_MEMORY_PATTERNS
    )


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
7. DEFAULT TO NOT SAVING A MEMORY. Only save information when it is
   reasonably likely to remain useful beyond the current conversation and
   meaningfully improve Luna's future understanding of the user.
8. Good candidates include long-term goals, ongoing commitments, stable
   preferences, recurring habits or patterns, important decisions, persistent
   plans, meaningful constraints, durable career or education information, and
   other information likely to matter in future conversations.
9. Do NOT save one-off meals, one-off activities, temporary moods or states,
   casual daily events, trivial conversational details, isolated progress
   updates unless they represent a meaningful durable state, or information
   that is only useful for the current turn.
   Durability and future usefulness matter more than whether the event happened
   today. For example, a decision to switch a career focus to AI/ML may be
   worth saving, while eating a meal today is not.
10. Do not extract multiple facts that express the same underlying information
    from one user message.
11. If the user's statement is already represented by an existing fact, return
    no new fact. Do not create paraphrased duplicates of existing facts.
12. Preserve meaningful differences in temporal state or intention. For
    example, "Plans to focus on backend development this year" and "Currently
    focused on learning backend development" may represent different states
    and should not automatically be treated as identical.
13. Do not infer changes or contradictions unless the user explicitly states
    them.
14. Output MUST be valid JSON with the following structure:
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


def _parse_memory_payload(content: object) -> object | None:
    """Parse only a complete JSON response from the memory model.

    The extractor is deliberately fail-closed: prose, partial JSON, or other
    malformed output becomes no memory rather than a guessed fact.  A complete
    fenced JSON object is accepted because some models add that wrapper despite
    the instruction not to.
    """
    if not isinstance(content, str):
        return None
    candidate = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        logger.warning("Memory extractor returned non-JSON output; skipping memory save")
        return None


def extract_memories(user_text: str, client: Groq, model: str = MEMORY_MODEL) -> list[dict]:
    """Extract durable facts strictly from the user's input."""
    if not _should_attempt_memory_extraction(user_text):
        return []

    try:
        existing_facts = get_facts(limit=10)
        existing_facts_context = "\n".join(
            f"- [{fact['category']}] {fact['content']}"
            for fact in existing_facts
        ) or "(none)"

        completion_kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": MEMORY_EXTRACTOR_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Existing stored facts for duplicate and relevance "
                        "checking:\n"
                        f"{existing_facts_context}\n\n"
                        "Current user text:\n"
                        f"{user_text}"
                    ),
                },
            ],
            # The prompt requests a complete JSON object.  Do not use Groq's
            # hard JSON mode here: a smaller extraction model can fail that
            # provider-side constraint before returning a payload.  Local,
            # fail-closed validation below is sufficient and keeps memory
            # extraction isolated from the response path.
            temperature=0,
        )

        response = None
        last_exc = None
        for attempt in range(MAX_GROQ_RETRIES + 1):
            try:
                response = client.chat.completions.create(**completion_kwargs)
                break
            except (RateLimitError, APIConnectionError) as exc:
                last_exc = exc
                if attempt < MAX_GROQ_RETRIES:
                    wait = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                    logger.warning(
                        "Memory extraction Groq call failed (%s), attempt "
                        "%s/%s; retrying in %ss",
                        type(exc).__name__,
                        attempt + 1,
                        MAX_GROQ_RETRIES + 1,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                raise
        if response is None:
            raise last_exc

        content = response.choices[0].message.content
        data = _parse_memory_payload(content)
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
