"""Thin wrapper around the generative AI model.

This module initializes the Google Generative AI client and exposes
a simple generate_response() function returning plain text.
"""

import importlib
from typing import Callable, Optional

import config


def _configure_genai() -> None:
    if not config.GENAI_API_KEY:
        raise RuntimeError("GENAI_API_KEY not set in environment")
    # Defer configuring the google client until it's imported so the
    # module doesn't require google.generativeai to be installed at
    # import time. This function only validates that an API key exists.
    return None


def generate_response(user_content: str,
                      client: Optional[Callable[[str], str]] = None) -> str:
    """Generate a text response for the given user content.

    Lightweight: configure the client (if needed), create a model
    instance for this call, and return the generated text.
    """
    # Build prompt (system prompt + user input)
    full_prompt = f"System: {config.SYSTEM_PROMPT}\n\nUser: {user_content}"

    # If the caller provided a client callable, use it. This lets the
    # caller avoid installing google.generativeai entirely.
    if client is not None:
        return client(full_prompt)

    # Validate the API key before importing the library so we fail with
    # a clear message if the key is missing.
    _configure_genai()

    # Import the google client lazily so the module itself doesn't
    # require the package at import time.
    try:
        genai = importlib.import_module("google.generativeai")
    except Exception as e:  # pragma: no cover - runtime import error
        raise RuntimeError(
            "google.generativeai is not installed. "
            "Install it or pass a `client` callable to generate_response."
        ) from e

    # Use helper if present, otherwise fall back to the model class.
    gen_text = getattr(genai, "generate_text", None)
    resp = None
    if gen_text:
        try:
            resp = gen_text(model="gemini-2.5-flash", prompt=full_prompt)
        except TypeError:
            resp = gen_text(model="gemini-2.5-flash", input=full_prompt)
    else:
        model_cls = getattr(genai, "GenerativeModel", None)
        if model_cls:
            # Configure the library if it exposes a configure function.
            cfg = getattr(genai, "configure", None)
            if cfg:
                cfg(api_key=config.GENAI_API_KEY)
            model = model_cls("gemini-2.5-flash")
            resp = model.generate_content(full_prompt)

    text = getattr(resp, "text", None) if resp is not None else None
    if not text:
        text = getattr(resp, "result", None) or getattr(
            resp, "content", None
        )

    if not text:
        raise RuntimeError("No response text generated")

    return text
