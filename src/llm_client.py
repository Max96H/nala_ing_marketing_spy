"""
ING Banking Campaigns Comparator — shared LLM client

One client interface for multiple providers. Groq and Gemini both expose an
OpenAI-compatible endpoint, so switching providers is just a different
base_url/api_key/model — no provider-specific code needed in analyst.py,
analysis.py, assistant.py, or api.py.

Switch providers with the LLM_PROVIDER env var:
    LLM_PROVIDER=groq      (default) — needs GROQ_API_KEY
    LLM_PROVIDER=gemini    — needs GEMINI_API_KEY

Why this exists: at ~3,000 pages, a single free-tier provider's rate limits
become a real constraint, not just a cost question. Splitting load across
two providers — or switching entirely if one is throttled — needs a common
interface so the rest of the pipeline doesn't care which is active.

Setup:
    pip install openai python-dotenv --break-system-packages
    export LLM_PROVIDER=gemini
    export GEMINI_API_KEY=...
    (or leave LLM_PROVIDER unset / "groq" and set GROQ_API_KEY as before)
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "openai/gpt-oss-120b",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "default_model": "gemini-3.5-flash-lite",
    },
}


def get_client(model: str | None = None) -> tuple[OpenAI, str]:
    """Returns (client, model_name) for whichever provider LLM_PROVIDER
    selects. Pass model= to override the provider's default model."""
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown LLM_PROVIDER '{provider}' — choose one of: "
                          f"{', '.join(PROVIDERS)}")

    cfg = PROVIDERS[provider]
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise RuntimeError(f"{cfg['api_key_env']} not set (required for LLM_PROVIDER={provider}).")

    client = OpenAI(base_url=cfg["base_url"], api_key=api_key)
    return client, (model or cfg["default_model"])