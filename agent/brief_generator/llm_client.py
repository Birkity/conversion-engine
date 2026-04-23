"""
LLM client for brief_generator.
Uses OpenRouter with google/gemini-1.5-flash at temperature 0.1.
Traces each call to Langfuse when credentials are present.
"""
import os
import sys

sys.set_int_max_str_digits(0)

from dotenv import load_dotenv
from langfuse.openai import OpenAI

load_dotenv()

BRIEF_MODEL = os.getenv("BRIEF_GENERATOR_MODEL", "google/gemini-2.0-flash-001")
BRIEF_TEMPERATURE = float(os.getenv("BRIEF_GENERATOR_TEMPERATURE", "0.1"))

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    return _client


def call_llm(
    system_prompt: str,
    user_message: str,
    trace_name: str = "brief_generator",
    trace_metadata: dict | None = None,
) -> str:
    """
    Call the LLM and return the raw string response.
    Auto-traced to Langfuse via the langfuse.openai wrapper.
    """
    response = _get_client().chat.completions.create(
        model=BRIEF_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=BRIEF_TEMPERATURE,
        response_format={"type": "json_object"},
        name=trace_name,
        metadata=trace_metadata or {},
    )
    return response.choices[0].message.content
