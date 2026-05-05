"""Adapter that runs the Gemini Live API for single-turn responses.

This module wraps `classes.gemini_live.GeminiLive` to provide a
sync-friendly `generate_response()` function used by the bot. It sends
the user's text (and optional images as video frames) into a Live
session and collects model-produced text events until the turn
completes.
"""

from typing import Optional
import asyncio
import re

import constants
from classes import llm_tools
from classes.gemini_live import GeminiLive
from google.genai import types


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
                parts.append(
                    types.Part.from_bytes(data=image_data, mime_type=mime_type)
                )
            except Exception as e:
                print(f"Error processing image {image_url}: {e}")

    # If no text was provided, add a default prompt
    if not parts:
        parts.append(
            types.Part.from_text(text="Analyze and describe these image(s) in detail.")
        )

    return parts


async def generate_response(user_content: str, image_urls: Optional[list] = None) -> str:
    """Generate a text response using Gemini Live.

    This is a synchronous wrapper that starts a short-lived Live session,
    sends the user's text (and any images as video frames), and collects
    text output events until the model finishes the turn.
    """

    if not constants.Secrets.GENAI_API_KEY:
        raise RuntimeError("GENAI_API_KEY not set in environment")

    # Load system prompt
    with open(constants.FilePaths.SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        system_instruction = f.read()

    tools = llm_tools.get_tools()
    tool_mapping = llm_tools.get_tool_mapping()

    live = GeminiLive(
        api_key=constants.Secrets.GENAI_API_KEY,
        model=constants.LLMConfig.MODEL_NAME,
        input_sample_rate=16000,
        system_instruction=system_instruction,
        tools=tools,
        tool_mapping=tool_mapping,
    )

    async def _run_live() -> str:
        audio_q = asyncio.Queue()
        video_q = asyncio.Queue()
        text_q = asyncio.Queue()

        # If images were provided, send them as video frames
        if image_urls:
            for url in image_urls:
                data = _download_image_from_url(url)
                if data:
                    await video_q.put(data)

        # Put the user's message into the text queue
        await text_q.put(user_content)

        collected = []

        try:
            # Stream events from Gemini Live; stop when turn_complete is seen
            async for event in live.start_session(
                audio_q, video_q, text_q, None, None
            ):
                if event is None:
                    break
                if isinstance(event, dict):
                    t = event.get("type")
                    if t == "gemini" and event.get("text"):
                        collected.append(event.get("text"))
                    if t == "turn_complete":
                        break
                    if t == "error":
                        collected.append(f"Error from Live API: {event.get('error')}")
                        break
        except asyncio.TimeoutError:
            collected.append("Error: timed out waiting for Gemini Live response")

        raw = " ".join(collected).strip()
        # Collapse any whitespace (newlines, multiple spaces, tabs) to single spaces
        cleaned = re.sub(r"\s+", " ", raw)
        # Remove space before common punctuation
        cleaned = re.sub(r"\s+([,?.!;:])", r"\1", cleaned)
        return cleaned

    # Run the async Live session and return the result
    return await _run_live()
