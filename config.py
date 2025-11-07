import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Path to the system prompt file (next to this file)
PROMPT_FILE = os.path.join(os.path.dirname(__file__), 'prompt.txt')


def load_system_prompt() -> str:
    """Load system prompt from PROMPT_FILE. Create with a default if missing.

    Returns the prompt string.
    """
    default = (
        "You are NOVA, a helpful, friendly, and concise AI assistant "
        "for a Discord server. Answer clearly and politely, and keep "
        "replies appropriate for a general audience."
    )
    try:
        if not os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
                f.write(default)
            print(f"Created default prompt file at {PROMPT_FILE}")

        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
            return prompt or default
    except Exception as e:
        print(f"Warning: couldn't read prompt file: {e}")
        return default


SYSTEM_PROMPT = load_system_prompt()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GENAI_API_KEY = os.getenv('GENAI_API_KEY')
