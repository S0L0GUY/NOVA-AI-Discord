import discord
from discord.ext import commands

import ai
import config

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def send_ai_response(channel, content: str):
    """Fetch a response from the AI and send it to the channel.

    Handles long messages by splitting into 2000-character chunks.
    """
    try:
        response_text = ai.generate_response(content)
        if len(response_text) > 2000:
            for i in range(0, len(response_text), 2000):
                await channel.send(response_text[i : i + 2000])
        else:
            await channel.send(response_text)
    except Exception as e:
        print(f"Error generating response: {e}")
        await channel.send(
            "Sorry, I encountered an error while processing your request."
        )


async def collect_channel_history(channel, before_message=None, limit=None) -> str:
    """Collect prior messages from `channel` into a short conversation
    history suitable for prepending to the user's prompt.

    - Uses `clean_content` to avoid active pings.
    - Labels messages as `User:` or `Assistant:` so the model can follow roles.
    - Respects `config.MAX_HISTORY_MESSAGES` and `config.HISTORY_MAX_CHARS`.
    """
    if limit is None:
        limit = config.MAX_HISTORY_MESSAGES

    messages = []
    # Fetch messages oldest-first so the conversation reads naturally
    async for m in channel.history(
        limit=limit, before=before_message, oldest_first=True
    ):
        # Skip non-standard message types (like pins or system messages)
        if m.type != discord.MessageType.default:
            continue
        messages.append(m)

    lines = []
    total_chars = 0
    for m in messages:
        content = (m.clean_content or "").strip()
        if config.INCLUDE_ATTACHMENTS and m.attachments:
            for a in m.attachments:
                content += f" [attachment: {a.url}]"

        if not content:
            continue

        if m.author == bot.user or m.author.bot:
            line = f"Assistant: {content}"
        else:
            line = f"User: {content}"

        lines.append(line)
        total_chars += len(line) + 1

    # Trim oldest lines until within HISTORY_MAX_CHARS
    while lines and total_chars > config.HISTORY_MAX_CHARS:
        removed = lines.pop(0)
        total_chars -= len(removed) + 1

    return "\n".join(lines)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Connected to {len(bot.guilds)} guild(s)")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Only respond to messages that mention the bot
    if bot.user and bot.user.mentioned_in(message):
        # Remove the bot mention from the message
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()

        if not content:
            await message.channel.send(
                "Hi! Mention me with a question and I'll help you!"
            )
            return

        # Build recent channel history and show typing indicator
        history = await collect_channel_history(message.channel, before_message=message)
        if history:
            combined = f"{history}\nUser: {content}"
        else:
            combined = f"User: {content}"

        async with message.channel.typing():
            await send_ai_response(message.channel, combined)

    # Process commands
    await bot.process_commands(message)


@bot.command(name="ask")
async def ask(ctx, *, question):
    """Command to ask the AI a question."""
    # Include recent history when answering commands as well
    history = await collect_channel_history(ctx.channel, before_message=ctx.message)
    if history:
        combined = f"{history}\nUser: {question}"
    else:
        combined = f"User: {question}"

    async with ctx.typing():
        await send_ai_response(ctx, combined)


@bot.command(name="help_nova")
async def help_nova(ctx):
    """Display help information."""
    help_text = (
        "**NOVA-AI Discord Bot Help**\n\n"
        "**Ways to interact with me:**\n"
        "1. Mention me (@NOVA-AI) followed by your question\n"
        "2. Use the `!ask` command followed by your question\n\n"
        "**Examples:**\n"
        "- @NOVA-AI What is artificial intelligence?\n"
        "- !ask Tell me a joke\n\n"
        "**Note:** I'm powered by Google's Gemini AI!\n"
    )
    await ctx.send(help_text)
