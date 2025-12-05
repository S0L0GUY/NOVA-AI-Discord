"""Thin wrapper around the generative AI model.

This module initializes the Google GenAI client and exposes
a simple generate_response() function returning plain text.
"""

from google import genai

import constants
from classes import llm_tools

# Lazy-initialized client
_client = None


def _init_client():
    """Initialize the GenAI client."""
    global _client
    if _client is None:
        if not constants.Secrets.GENAI_API_KEY:
            raise RuntimeError("GENAI_API_KEY not set in environment")
        _client = genai.Client(api_key=constants.Secrets.GENAI_API_KEY)
    return _client


def generate_response(user_content: str) -> str:
    """Generate a text response for the given user content.

    The system prompt from `config.SYSTEM_PROMPT` is used as a system instruction,
    and the user's content is passed as the user message. This follows best practices
    for structured prompt handling with the Gemini API.
    """
    client = _init_client()

    # Get the generation config with tools
    gen_config = llm_tools.get_generate_config()

    # Set the system instruction in the config
    with open(constants.FilePaths.SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        gen_config.system_instruction = f.read()

    # Generate content using proper message handling
    response = client.models.generate_content(
        model=constants.LLMConfig.MODEL_NAME,
        contents=user_content,
        config=gen_config,
    )

    text = getattr(response, "text", None)
    if not text:
        return "Error: No response text received from the AI model."
    return text
