"""
llm.py — LLM inference using Groq (free, very fast Llama 3)
Maintains conversation history and returns the assistant reply.
"""

import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful voice assistant. Keep answers concise and conversational "
    "since the user will hear them spoken aloud. Avoid markdown, bullet points, or lists.",
)

# Groq async client (reused across calls)
_client = AsyncGroq(api_key=GROQ_API_KEY)


async def get_llm_reply(
    user_message: str,
    conversation_history: list[dict],
) -> tuple[str, list[dict]]:
    """
    Sends the user message + full conversation history to Groq.
    Returns (assistant_reply_text, updated_history).

    conversation_history format:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """
    # Append the new user message to history
    updated_history = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    # Build the messages list with system prompt prepended
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + updated_history

    try:
        chat_completion = await _client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=300,  # Keep replies short for voice
        )
        reply = chat_completion.choices[0].message.content.strip()

        # Save the assistant reply into history
        updated_history.append({"role": "assistant", "content": reply})

        return reply, updated_history

    except Exception as e:
        print(f"[LLM] Groq error: {e}")
        error_reply = "Sorry, I had trouble thinking of a response. Please try again."
        updated_history.append({"role": "assistant", "content": error_reply})
        return error_reply, updated_history


def reset_history() -> list[dict]:
    """Returns a fresh empty conversation history."""
    return []
