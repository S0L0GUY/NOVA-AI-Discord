import os

import dotenv

dotenv.load_dotenv()


class LLMConfig:
    MODEL_NAME = "gemini-2.5-flash"
    TEMPERATURE = 0.7

    # How many prior messages to fetch from the channel when building
    # context for NOVA. Override with MAX_HISTORY_MESSAGES env var.
    MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

    # Whether to include attachment URLs from prior messages in the context
    INCLUDE_ATTACHMENTS = True

    # Maximum total characters of history to include in the prompt.
    # Keeps prompts from growing unbounded. Override with HISTORY_MAX_CHARS.
    HISTORY_MAX_CHARS = int(os.getenv("HISTORY_MAX_CHARS", "3000"))


class FilePaths:
    SYSTEM_PROMPT_FILE = os.path.join(
        os.path.dirname(__file__), "text_files/prompt.txt"
    )
    HELP_PROMPT_FILE = os.path.join(
        os.path.dirname(__file__), "text_files/help_text.txt"
    )


class Secrets:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GENAI_API_KEY = os.getenv("GENAI_API_KEY")
