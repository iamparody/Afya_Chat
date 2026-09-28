"""
LLM provider abstraction for Phase 5.

Each provider implements generate(system_prompt, context) -> str (raw JSON).
rag.py calls provider.generate() and never touches provider internals.

Adding a new provider: subclass LLMProvider, implement generate().
"""

import os
import time
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
        from google.genai.errors import ServerError
        config = self._types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=self._schema,
            temperature=0.0,
        )
        delays = [15, 30, 60, 120]
        for attempt, delay in enumerate(delays, start=1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=context,
                    config=config,
                )
                return response.text
            except ServerError as e:
                if attempt == len(delays):
                    raise
                msg = str(e).lower()
                if "503" not in msg and "unavailable" not in msg and "high demand" not in msg:
                    raise
                print(f"Gemini 503 — attempt {attempt}/{len(delays)}, retrying in {delay}s...", flush=True)
                time.sleep(delay)


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


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "qwen/qwen3.8-27b"):
        from groq import Groq
        self._client = Groq(api_key=api_key)
        self._model  = model

    def generate(self, system_prompt: str, context: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": context},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content


def get_provider() -> LLMProvider:
    """
    Return the active provider based on available env vars.
    Priority: GEMINI_API_KEY → ANTHROPIC_API_KEY → GROQ_API_KEY
    """
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiProvider(api_key=os.environ["GEMINI_API_KEY"])
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
    if os.environ.get("GROQ_API_KEY"):
        return GroqProvider(api_key=os.environ["GROQ_API_KEY"])
    raise EnvironmentError("No LLM provider key found. Set GEMINI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY in .env")
