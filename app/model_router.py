"""
Model Router — the seam where multi-model orchestration plugs in.

Only Anthropic is wired up today. Adding GPT or Gemini later means adding
another branch here, each using its OWN organizational API credential
(ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, etc.) — never a fellow's
personal ChatGPT/Claude subscription. OpenAI in particular separates ChatGPT
and API billing entirely, so there's no shortcut there; Vinverse needs its own
authorized API connections regardless of what individual fellows already pay
for personally.
"""
import os
from anthropic import AsyncAnthropic

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "anthropic")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

_anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def call_model(system_prompt: str, messages: list[dict]) -> str:
    if MODEL_PROVIDER == "anthropic":
        response = await _anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")

    # Placeholders for future providers — implement when actually adding them:
    # if MODEL_PROVIDER == "openai": ...
    # if MODEL_PROVIDER == "google": ...
    raise NotImplementedError(f"Model provider '{MODEL_PROVIDER}' is not implemented yet")
