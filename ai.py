"""Thin wrapper around the generative AI model.

This module initializes the Google Generative AI client and exposes
a simple generate_response() function returning plain text.
"""

import google.generativeai as genai

import config


def _configure_genai() -> None:
    if not config.GENAI_API_KEY:
        raise RuntimeError("GENAI_API_KEY not set in environment")
    genai.configure(api_key=config.GENAI_API_KEY)


# Lazy-initialized model
_model = None


def _init_model():
    global _model
    if _model is None:
        _configure_genai()
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


def generate_response(user_content: str) -> str:
    """Generate a text response for the given user content.

    The system prompt from `config.SYSTEM_PROMPT` is prefixed to
    the user's content so the model receives system-level instructions.
    """
    model = _init_model()
    full_prompt = f"System: {config.SYSTEM_PROMPT}\n\nUser: {user_content}"
    resp = model.generate_content(full_prompt)
    text = getattr(resp, "text", None)
    if not text:
        raise RuntimeError("No response text generated")
    return text
