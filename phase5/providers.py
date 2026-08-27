"""
LLM provider abstraction for Phase 5.

Each provider implements generate(system_prompt, context) -> str (raw JSON).
rag.py calls provider.generate() and never touches provider internals.

Adding a new provider: subclass LLMProvider, implement generate().
"""

import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, context: str) -> str:
        """Return raw JSON string. Raise on API failure."""


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-flash-lite-latest"):
        from google import genai
        from google.genai import types
        self._types  = types
        self._client = genai.Client(api_key=api_key)
        self._model  = model
        self._schema = None  # set via set_schema()

    def set_schema(self, schema: dict):
        self._schema = schema

    def generate(self, system_prompt: str, context: str) -> str:
        config = self._types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=self._schema,
            temperature=0.0,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=context,
            config=config,
        )
        return response.text


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model  = model

    def generate(self, system_prompt: str, context: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": context}],
        )
        return message.content[0].text


def get_provider() -> LLMProvider:
    """
    Return the active provider based on available env vars.
    Priority: GEMINI_API_KEY → ANTHROPIC_API_KEY
    """
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiProvider(api_key=os.environ["GEMINI_API_KEY"])
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
    raise EnvironmentError("No LLM provider key found. Set GEMINI_API_KEY or ANTHROPIC_API_KEY in .env")
