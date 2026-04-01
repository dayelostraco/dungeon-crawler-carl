import json
import re

import anthropic

from config import ANTHROPIC_API_KEY, MAX_TOKENS, MODEL, SYSTEM_PROMPT


def generate(trigger: str | None = None) -> dict:
    """
    Generate a satirical achievement.
    trigger: optional context string (e.g. "spilled coffee again")
    Returns dict with keys: title, description, reward
    """
    if not ANTHROPIC_API_KEY:
        raise OSError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if trigger:
        user_message = f"Generate a satirical achievement for this event: {trigger}"
    else:
        user_message = "Generate a random satirical achievement."

    def call_api() -> str:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip()

    def strip_markdown(text: str) -> str:
        """Strip markdown code fences from JSON response."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        return match.group(1) if match else text

    raw = call_api()

    try:
        return json.loads(strip_markdown(raw))
    except json.JSONDecodeError:
        # Retry once
        raw = call_api()
        try:
            return json.loads(strip_markdown(raw))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse achievement JSON after two attempts.\nRaw response:\n{raw}"
            ) from e
