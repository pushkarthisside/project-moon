import json
import logging
import os
import re
import time
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError, RateLimitError

from tools import TOOL_DEFINITIONS, execute_tool_call

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing required environment variable: GROQ_API_KEY")

# NOTE: llama-3.1-8b-instant and llama-3.3-70b-versatile were both shut down
# by Groq on 2026-08-16. openai/gpt-oss-120b is Groq's recommended
# replacement for llama-3.3-70b-versatile (Luna's main conversational/
# tool-calling model). Configurable via .env so future Groq deprecations
# don't require a code change.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Retry policy for transient Groq failures (rate limits, connection errors).
# Deliberately small and fast: this call happens inline in the user's
# request path, so we don't want retries to make Luna feel unresponsive.
MAX_GROQ_RETRIES = 1
RETRY_BACKOFF_SECONDS = (1, 3)

logger = logging.getLogger(__name__)
STATE_CHANGE_TOOLS = frozenset({
    "create_goal",
    "update_goal_status",
    "update_multiple_goal_statuses",
    "create_reminder",
    "update_reminder_status",
})

# Initialize Groq client.
# max_retries=0: the SDK retries 429s/connection errors on its own by
# default (2 retries, with its own backoff). That stacks with our own
# retry loop below and produces compounding multi-retry delays (observed
# as 15s/2s/17s waits in production logs) instead of one bounded, visible
# retry policy. We own retry behavior entirely in _call_groq_with_retry().
groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0)


def _call_groq_with_retry(**kwargs):
    """Call the Groq completion endpoint with a small retry budget.

    Retries only on rate limits and transient connection errors, since those
    are the failure modes where waiting a moment and retrying can actually
    succeed. Auth/bad-request/other API errors are not retried; they won't
    be fixed by waiting, so we fail fast and let the caller's existing
    error handling (bot.py's top-level except) surface a clean message.
    """
    last_exc = None
    for attempt in range(MAX_GROQ_RETRIES + 1):
        try:
            return groq_client.chat.completions.create(**kwargs)
        except (RateLimitError, APIConnectionError) as exc:
            last_exc = exc
            if attempt < MAX_GROQ_RETRIES:
                wait = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning(
                    "Groq call failed (%s), attempt %s/%s; retrying in %ss",
                    type(exc).__name__,
                    attempt + 1,
                    MAX_GROQ_RETRIES + 1,
                    wait,
                )
                time.sleep(wait)
                continue
            logger.error(
                "Groq call failed after %s attempts (%s); giving up",
                MAX_GROQ_RETRIES + 1,
                type(exc).__name__,
            )
            raise
        except APIStatusError as exc:
            # Non-retryable API error (bad request, auth, model deprecated,
            # etc.). Log with the status code so a deprecated/renamed model
            # shows up clearly in logs instead of a generic failure.
            logger.error(
                "Groq API error: status=%s message=%s",
                getattr(exc, "status_code", "unknown"),
                str(exc),
            )
            raise
    raise last_exc  # pragma: no cover - loop always returns or raises


def _looks_like_pseudo_tool_output(content: str | None) -> bool:
    """Return whether the model emitted fake/XML-like tool syntax.

    This is deliberately only a safety check.  The content is never parsed or
    executed; structured ``tool_calls`` are the only supported execution path.
    """
    if not isinstance(content, str) or not content:
        return False
    return bool(
        re.search(
            r"<function\s*[:=,]\s*[A-Za-z_][\w-]*(?:\s*[>,=])",
            content,
            re.IGNORECASE,
        )
        or re.search(r"</function\s*>", content, re.IGNORECASE)
    )

def get_completion(
    messages: list,
    tools: list | None = None,
) -> dict:
    """
    Low-level Groq call. Takes a fully-formed `messages` list so callers can
    represent any conversation shape — including the
    system -> user -> assistant(tool_call) -> tool -> assistant
    round trip needed for tool calling.
    Returns a structured dictionary containing text content and/or tool call payloads.
    """
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.0,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    completion = _call_groq_with_retry(**kwargs)
    choices = getattr(completion, "choices", None)
    if not choices:
        raise RuntimeError("Groq returned no completion choices")

    try:
        first_choice = choices[0]
    except (IndexError, KeyError, TypeError):
        raise RuntimeError("Groq returned malformed completion choices") from None

    response_message = getattr(first_choice, "message", None)
    if response_message is None:
        raise RuntimeError("Groq completion did not contain a response message")

    if not hasattr(response_message, "content") and not hasattr(
        response_message, "tool_calls"
    ):
        raise RuntimeError("Groq response message has an unexpected shape")

    return {
        "message": response_message,  # raw message object, needed to append back into `messages`
        "content": getattr(response_message, "content", None),
        "tool_calls": getattr(response_message, "tool_calls", None),
    }


def format_tool_message(call_id: str, tool_result_content: str) -> dict:
    """Format a tool result message for follow-up LLM completion turns."""
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": tool_result_content,
    }


def get_reply(
    system_prompt: str,
    user_text: str,
    tools: list | None = None,
    max_tool_rounds: int = 2,
) -> dict:
    """
    High-level entry point: handles a full interaction, including any number
    of tool-call round trips.

    Flow:
      1. system + user -> ask Groq (with tools attached)
      2. if no tool calls -> return the text content
      3. otherwise: append the assistant's tool-call message, execute each
         tool, append each tool result, then ask Groq again with the full
         conversation so far
      4. repeat until Groq responds with plain content (or max_tool_rounds hit)
    """
    if tools is None:
        tools = TOOL_DEFINITIONS

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    # A single model turn must not be able to execute the same operation over
    # and over.  This is especially important for insert-like tools.
    seen_tool_calls = set()
    state_change_attempted = False
    last_loop_path = "no completion round was started"
    for _ in range(max(0, max_tool_rounds)):
        current_round = _ + 1
        last_loop_path = f"completion round {current_round} started"
        response = get_completion(messages, tools=tools)
        response_message = response["message"]

        tool_calls = response["tool_calls"]
        if not tool_calls:
            if _looks_like_pseudo_tool_output(response["content"]):
                last_loop_path = (
                    f"round {current_round} returned pseudo-tool output; "
                    "requested structured-tool correction"
                )
                logger.warning(
                    "Pseudo-tool output blocked in round %s/%s; continuing "
                    "with structured-tool correction",
                    current_round,
                    max_tool_rounds,
                )
                # Do not relay or interpret pseudo-function text.  Give the
                # provider one of the remaining structured-tool rounds to
                # correct itself.
                messages.append({
                    "role": "assistant",
                    "content": response["content"],
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "The previous response used invalid pseudo-function "
                        "text. Do not write function markup or imitate tool "
                        "syntax. Use one of the provided structured tools "
                        "with a tool call, or answer normally if no tool is "
                        "needed."
                    ),
                })
                continue
            return {
                "text": response["content"] or "I couldn't complete that action.",
                "state_change_attempted": state_change_attempted,
            }

        # Preserve the assistant's tool-call turn in the conversation, as an
        # explicit dict rather than relying on SDK object serialization.
        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ],
        })

        # Run each requested tool and feed its result back in.
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments or "{}"
            logger.debug(
                "Model requested tool: name=%s raw_arguments=%r",
                tool_name,
                raw_arguments,
            )
            try:
                parsed_arguments = json.loads(raw_arguments)
                normalized_arguments = (
                    parsed_arguments if isinstance(parsed_arguments, dict) else {}
                )
                call_key = (tool_name, json.dumps(
                    normalized_arguments, sort_keys=True, separators=(",", ":")
                ))
            except (json.JSONDecodeError, TypeError):
                # Keep malformed argument handling in execute_tool_call(); the
                # raw value still forms a stable key for duplicate detection.
                call_key = (tool_name, str(raw_arguments))

            if call_key in seen_tool_calls:
                logger.warning(
                    "Duplicate tool call blocked: name=%s normalized_arguments=%s",
                    tool_name,
                    call_key[1],
                )
                result_content = (
                    f"Error: duplicate tool call for '{tool_name}' with the "
                    "same arguments was blocked in this interaction."
                )
            else:
                seen_tool_calls.add(call_key)
                if tool_name in STATE_CHANGE_TOOLS:
                    state_change_attempted = True
                result_content = execute_tool_call(
                    tool_name,
                    raw_arguments,
                )
                last_loop_path = (
                    f"round {current_round} executed requested tool '{tool_name}'"
                )

            messages.append(
                format_tool_message(tool_call.id, result_content)
            )

        # Loop back around: send the updated conversation (including tool
        # results) back to Groq for the next turn.

    # Safety net: if we somehow never got a plain-content response.
    logger.error(
        "Final safe fallback returned: reason=max_tool_rounds reached; "
        "current_round=%s configured_max=%s; path=%s; "
        "response=I couldn't complete that action safely. Please try again.",
        max(0, max_tool_rounds),
        max_tool_rounds,
        last_loop_path,
    )
    return {
        "text": "I couldn't complete that action safely. Please try again.",
        "state_change_attempted": state_change_attempted,
    }
