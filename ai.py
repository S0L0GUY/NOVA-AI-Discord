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
from logger import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """Base exception for API-related errors."""

    pass


class ConfigError(APIError):
    """Configuration or setup error."""

    pass


class NetworkError(APIError):
    """Network or download error."""

    pass


class ProcessingError(APIError):
    """Error during processing of response or images."""

    pass


def _download_image_from_url(image_url: str) -> Optional[bytes]:
    """Download image data from a URL.

    Args:
        image_url: URL to the image file

    Returns:
        Image bytes if successful, None otherwise

    Raises:
        NetworkError: If download fails after retries
    """
    try:
        import requests

        logger.debug(f"Downloading image from URL: {image_url}")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        logger.debug(f"Successfully downloaded image: {len(response.content)} bytes")
        return response.content

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout downloading image from {image_url}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error downloading image from {image_url}: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error downloading image from {image_url}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error downloading image from {image_url}: {e}", exc_info=True
        )
        return None


def _build_multimodal_content(text_content: str, image_urls: list) -> list:
    """Build a multimodal content list with text and images.

    Args:
        text_content: Text message from user
        image_urls: List of image URLs to include

    Returns:
        A list of content parts suitable for the Gemini API

    Raises:
        ProcessingError: If content building fails
    """
    try:
        parts = []

        # Add text as the first part
        if text_content.strip():
            parts.append(types.Part.from_text(text=text_content))
            logger.debug(f"Added text content: {len(text_content)} characters")

        # Download and add images
        if image_urls:
            logger.debug(f"Processing {len(image_urls)} image(s)")
            for image_url in image_urls:
                try:
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

                        parts.append(
                            types.Part.from_bytes(data=image_data, mime_type=mime_type)
                        )
                        logger.debug(
                            f"Added image part ({mime_type}): {len(image_data)} bytes"
                        )
                except Exception as e:
                    logger.warning(f"Error processing image {image_url}: {e}")

        # If no text was provided, add a default prompt
        if not parts:
            logger.debug("No content provided, using default image analysis prompt")
            parts.append(
                types.Part.from_text(
                    text="Analyze and describe these image(s) in detail."
                )
            )

        logger.debug(f"Built multimodal content with {len(parts)} parts")
        return parts
    except Exception as e:
        logger.error(f"Error building multimodal content: {e}", exc_info=True)
        raise ProcessingError(f"Failed to build multimodal content: {e}")


async def generate_response(
    user_content: str, image_urls: Optional[list] = None
) -> str:
    """Generate a text response using Gemini Live.

    This is a synchronous wrapper that starts a short-lived Live session,
    sends the user's text (and any images as video frames), and collects
    text output events until the model finishes the turn.

    Args:
        user_content: The user's text message
        image_urls: Optional list of image URLs to include

    Returns:
        Generated response text from the model

    Raises:
        ConfigError: If configuration is missing or invalid
        ProcessingError: If processing fails
    """
    try:
        logger.debug(f"Generating response for content: {user_content[:100]}...")

        if not constants.Secrets.GENAI_API_KEY:
            logger.error("GENAI_API_KEY not set in environment")
            raise ConfigError("GENAI_API_KEY not set in environment")

        # Load system prompt
        try:
            logger.debug(
                f"Loading system prompt from {constants.FilePaths.SYSTEM_PROMPT_FILE}"
            )
            with open(
                constants.FilePaths.SYSTEM_PROMPT_FILE, "r", encoding="utf-8"
            ) as f:
                system_instruction = f.read()
            logger.debug(f"Loaded system prompt: {len(system_instruction)} characters")
        except FileNotFoundError as e:
            logger.error(f"System prompt file not found: {e}")
            raise ConfigError(f"System prompt file not found: {e}")

        try:
            tools = llm_tools.get_tools()
            tool_mapping = llm_tools.get_tool_mapping()
            logger.debug(f"Loaded {len(tools)} tools")
        except Exception as e:
            logger.error(f"Error loading tools: {e}", exc_info=True)
            raise ProcessingError(f"Failed to load tools: {e}")

        try:
            logger.debug(
                f"Initializing GeminiLive with model: {constants.LLMConfig.MODEL_NAME}"
            )
            live = GeminiLive(
                api_key=constants.Secrets.GENAI_API_KEY,
                model=constants.LLMConfig.MODEL_NAME,
                input_sample_rate=16000,
                system_instruction=system_instruction,
                tools=tools,
                tool_mapping=tool_mapping,
            )
        except Exception as e:
            logger.error(f"Error initializing GeminiLive: {e}", exc_info=True)
            raise ProcessingError(f"Failed to initialize AI model: {e}")

        async def _run_live() -> str:
            """Run the Gemini Live session and collect response."""
            try:
                logger.debug("Starting Gemini Live session")
                audio_q = asyncio.Queue()
                video_q = asyncio.Queue()
                text_q = asyncio.Queue()

                # If images were provided, send them as video frames
                if image_urls:
                    logger.debug(f"Queueing {len(image_urls)} image(s)")
                    for url in image_urls:
                        try:
                            data = _download_image_from_url(url)
                            if data:
                                await video_q.put(data)
                                logger.debug(f"Queued image: {len(data)} bytes")
                        except Exception as e:
                            logger.warning(f"Error queueing image {url}: {e}")

                # Put the user's message into the text queue
                await text_q.put(user_content)
                logger.debug("Queued user content")

                collected = []
                event_count = 0

                try:
                    # Stream events from Gemini Live; stop when turn_complete is seen
                    async for event in live.start_session(
                        audio_q, video_q, text_q, None, None
                    ):
                        event_count += 1
                        if event is None:
                            logger.debug("Received None event")
                            break
                        if isinstance(event, dict):
                            t = event.get("type")
                            logger.debug(f"Received event type: {t}")

                            if t == "gemini" and event.get("text"):
                                text = event.get("text")
                                collected.append(text)
                                logger.debug(
                                    f"Collected gemini text: {len(text)} chars"
                                )
                            elif t == "turn_complete":
                                logger.debug("Turn complete")
                                break
                            elif t == "error":
                                error_msg = event.get("error", "Unknown error")
                                logger.error(f"Error from Live API: {error_msg}")
                                collected.append(f"Error from Live API: {error_msg}")
                                break

                    logger.debug(
                        f"Received {event_count} events, collected {len(collected)} text parts"
                    )

                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for Gemini Live response")
                    collected.append(
                        "Error: timed out waiting for Gemini Live response"
                    )
                except Exception as e:
                    logger.error(f"Error in Live session: {e}", exc_info=True)
                    raise ProcessingError(f"Error during AI session: {e}")

                raw = " ".join(collected).strip()
                # Collapse any whitespace (newlines, multiple spaces, tabs) to single spaces
                cleaned = re.sub(r"\s+", " ", raw)
                # Remove space before common punctuation
                cleaned = re.sub(r"\s+([,?.!;:])", r"\1", cleaned)

                logger.debug(
                    f"Final response: {cleaned[:100]}... ({len(cleaned)} chars)"
                )
                return cleaned

            except ProcessingError:
                raise
            except Exception as e:
                logger.error(f"Error in _run_live: {e}", exc_info=True)
                raise ProcessingError(f"Failed to generate response: {e}")

        # Run the async Live session and return the result
        response = await _run_live()
        logger.info("Response generated successfully")
        return response

    except (ConfigError, ProcessingError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_response: {e}", exc_info=True)
        raise ProcessingError(f"Unexpected error generating response: {e}")
