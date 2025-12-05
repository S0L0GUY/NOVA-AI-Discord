"""Thin wrapper around the generative AI model.

This module initializes the Google GenAI client and exposes
generate_response() function returning plain text. Supports both
text and multimodal (image) content through the Gemini API.
"""

from typing import Optional

from google import genai
from google.genai import types

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


def _download_image_from_url(image_url: str) -> Optional[bytes]:
    """Download image data from a URL.

    Args:
        image_url: URL to the image file

    Returns:
        Image bytes if successful, None otherwise
    """
    try:
        import requests
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error downloading image from {image_url}: {e}")
        return None


def _build_multimodal_content(text_content: str, image_urls: list) -> list:
    """Build a multimodal content list with text and images.

    Args:
        text_content: Text message from user
        image_urls: List of image URLs to include

    Returns:
        A list of content parts suitable for the Gemini API
    """
    parts = []

    # Add text as the first part
    if text_content.strip():
        parts.append(types.Part.from_text(text=text_content))

    # Download and add images
    for image_url in image_urls:
        image_data = _download_image_from_url(image_url)
        if image_data:
            # Determine MIME type from URL or default to jpeg
            mime_type = "image/jpeg"
            if ".png" in image_url.lower():
                mime_type = "image/png"
            elif ".gif" in image_url.lower():
                mime_type = "image/gif"
            elif ".webp" in image_url.lower():
                mime_type = "image/webp"

            try:
                parts.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ))
            except Exception as e:
                print(f"Error processing image {image_url}: {e}")

    # If no text was provided, add a default prompt
    if not parts:
        parts.append(types.Part.from_text(
            text="Analyze and describe these image(s) in detail."
        ))

    return parts


def generate_response(user_content: str, image_urls: Optional[list] = None) -> str:
    """Generate a text response for the given user content.

    Supports both text-only and multimodal (text + images) responses.
    The system prompt from `config.SYSTEM_PROMPT` is used as a system instruction,
    and the user's content is passed as the user message. This follows best practices
    for structured prompt handling with the Gemini API.

    Args:
        user_content: Text content from the user
        image_urls: Optional list of image URLs to analyze

    Returns:
        Response text from the AI model
    """
    client = _init_client()

    # Get the generation config with tools
    gen_config = llm_tools.get_generate_config()

    # Set the system instruction in the config
    with open(constants.FilePaths.SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        gen_config.system_instruction = f.read()

    # Build content with images if provided
    if image_urls and len(image_urls) > 0:
        contents = _build_multimodal_content(user_content, image_urls)
    else:
        contents = user_content

    # Generate content using proper message handling
    response = client.models.generate_content(
        model=constants.LLMConfig.MODEL_NAME,
        contents=contents,
        config=gen_config,
    )

    text = getattr(response, "text", None)
    if not text:
        return "Error: No response text received from the AI model."
    return text
