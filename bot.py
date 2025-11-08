"""Small runner for the NOVA Discord bot.

This file is intentionally tiny: it validates required environment
variables and starts the bot defined in `discord_bot.py`.
"""
import sys

import config
from discord_bot import bot

from keep_alive import keep_alive


if __name__ == '__main__':
    keep_alive()
    token = config.DISCORD_TOKEN
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord token.")
        sys.exit(1)

    if not config.GENAI_API_KEY:
        print("Error: GENAI_API_KEY not found in environment variables!")
        print("Please create a .env file with your GenAI API key.")
        sys.exit(1)

    bot.run(token)
