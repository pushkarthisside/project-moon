import json
import os
from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_DEFINITIONS, TOOL_MAP

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing required environment variable: GROQ_API_KEY")

MODEL = "llama-3.3-70b-versatile"

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

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
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    completion = groq_client.chat.completions.create(**kwargs)
    response_message = completion.choices[0].message

    return {
        "message": response_message,  # raw message object, needed to append back into `messages`
        "content": response_message.content,
        "tool_calls": response_message.tool_calls,
    }


def format_tool_message(call_id: str, tool_result_content: str) -> dict:
    """Format a tool result message for follow-up LLM completion turns."""
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": tool_result_content,
    }


def execute_tool_call(tool_call) -> str:
    """
    Runs a single tool call against TOOL_MAP and returns the result
    as a string, ready to be wrapped by format_tool_message().
    """
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return f"Error: could not parse arguments for tool '{name}'"

    fn = TOOL_MAP.get(name)
    if fn is None:
        return f"Error: unknown tool '{name}'"

    try:
        result = fn(**args)
    except Exception as exc:  # keep the loop alive; report the failure to the model
        return f"Error running tool '{name}': {exc}"

    if not isinstance(result, str):
        result = json.dumps(result)
    return result


def get_reply(
    system_prompt: str,
    user_text: str,
    tools: list | None = None,
    max_tool_rounds: int = 5,
) -> str:
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

    for _ in range(max_tool_rounds):
        response = get_completion(messages, tools=tools)
        response_message = response["message"]

        tool_calls = response["tool_calls"]
        if not tool_calls:
            return response["content"]

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
            result_content = execute_tool_call(tool_call)
            messages.append(
                format_tool_message(tool_call.id, result_content)
            )

        # Loop back around: send the updated conversation (including tool
        # results) back to Groq for the next turn.

    # Safety net: if we somehow never got a plain-content response.
    return response["content"] or "I couldn't complete that action."
