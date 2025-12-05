import re

import discord
from discord.ext import commands

import ai
import constants

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def send_ai_response(target, content: str, reply_to=None, image_urls=None):
    """Fetch a response from the AI and send it.

    - `target` may be a `discord.TextChannel` or a `commands.Context`.
    - If `reply_to` (a `discord.Message`) is provided, the bot will reply
      to that message (keeping the response linked to the original question).
    - `image_urls` is an optional list of image URLs to include in the request.
    - Long messages are split into 2000-character chunks.
    - If the AI output contains the literal token `@user` (or a few common
      placeholders), it will be replaced with the mention for `reply_to.author`.
    """
    try:
        response_text = ai.generate_response(content, image_urls=image_urls)

        # If replying to a message, allow the model to include a placeholder
        # like '@user' which we'll replace with the proper mention syntax.
        if reply_to:
            mention = f"<@{reply_to.author.id}>"
            for token in ("@user", "<@user>", "{user}", "{mention}", "@mention"):
                response_text = response_text.replace(token, mention)

            # Also resolve simple @Name patterns to real member mentions
            # by searching the guild members (display_name or username).
            if reply_to.guild:

                def _resolve(m):
                    name = m.group(1)
                    if name.lower() in ("everyone", "here"):
                        return m.group(0)
                    for member in reply_to.guild.members:
                        if (
                            member.display_name.lower() == name.lower()
                            or member.name.lower() == name.lower()
                        ):
                            return f"<@{member.id}>"
                    return m.group(0)

                response_text = re.sub(
                    r"@([A-Za-z0-9_\-]{2,32})", _resolve, response_text
                )

        async def _send(chunk: str):
            # If we have a message to reply to, reply so the response is threaded
            # to the original question. Otherwise send to the provided target.
            if reply_to:
                await reply_to.reply(chunk)
            else:
                if isinstance(target, commands.Context):
                    await target.send(chunk)
                else:
                    await target.send(chunk)

        if len(response_text) > 2000:
            for i in range(0, len(response_text), 2000):
                await _send(response_text[i : i + 2000])
        else:
            await _send(response_text)
    except Exception as e:
        print(f"Error generating response: {e}")
        # Try to reply if possible, otherwise send to target
        err_msg = "Sorry, I encountered an error while processing your request."
        if reply_to:
            await reply_to.reply(err_msg)
        else:
            if isinstance(target, commands.Context):
                await target.send(err_msg)
            else:
                await target.send(err_msg)


async def collect_channel_history(channel, before_message=None, limit=None) -> str:
    """Collect prior messages from `channel` into a short conversation
    history suitable for prepending to the user's prompt.

    - Uses `clean_content` to avoid active pings.
    - Labels messages as `User:` or `Assistant:` so the model can follow roles.
    - Respects `config.MAX_HISTORY_MESSAGES` and `config.HISTORY_MAX_CHARS`.
    """
    if limit is None:
        limit = constants.LLMConfig.MAX_HISTORY_MESSAGES

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
    while lines and total_chars > constants.LLMConfig.HISTORY_MAX_CHARS:
        removed = lines.pop(0)
        total_chars -= len(removed) + 1

    return "\n".join(lines)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Connected to {len(bot.guilds)} guild(s)")
    if not getattr(bot, "tree_synced", False):
        await bot.tree.sync()
        # Also sync per-guild so slash commands appear immediately
        for guild in bot.guilds:
            try:
                await bot.tree.sync(guild=guild)
                print(f"Synced commands for guild {guild.name} ({guild.id})")
            except Exception as e:
                print(f"Failed to sync commands for guild {guild.id}: {e}")
        bot.tree_synced = True  # type: ignore[attr-defined]
        print("Synced application commands.")


@bot.event
async def on_guild_join(guild):
    try:
        await bot.tree.sync(guild=guild)
        print(f"Synced commands for new guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"Failed to sync commands for guild {guild.id}: {e}")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Only respond to messages that mention the bot
    if bot.user and bot.user.mentioned_in(message):
        # Remove the bot mention from the message (handle both <@id> and <@!id>)
        content = (
            message.content.replace(f"<@{bot.user.id}>", "")
            .replace(f"<@!{bot.user.id}>", "")
            .strip()
        )

        if not content and not message.attachments:
            await message.channel.send(
                "Hi! Mention me with a question and I'll help you!"
            )
            return

        # Extract image URLs from attachments
        image_urls = []
        if message.attachments:
            for attachment in message.attachments:
                # Check if attachment is an image
                if attachment.content_type and attachment.content_type.startswith(
                    "image/"
                ):
                    image_urls.append(attachment.url)
                    # Add attachment info to content if no text was provided
                    if not content:
                        content = "Analyze this image"

        # Build recent channel history and show typing indicator
        history = await collect_channel_history(message.channel, before_message=message)
        if history:
            combined = f"{history}\nUser: {content}"
        else:
            combined = f"User: {content}"

        async with message.channel.typing():
            await send_ai_response(
                message.channel, combined, reply_to=message, image_urls=image_urls
            )

    # Process commands
    await bot.process_commands(message)


@bot.hybrid_command(name="help", description="Display help information.")
async def help(ctx):
    """Display help information."""
    with open(constants.FilePaths.HELP_PROMPT_FILE, "r", encoding="utf-8") as f:
        help_text = f.read()
    await ctx.send(help_text)


@bot.command(name="members")
async def members(ctx):
    """List server members with mention syntax so NOVA can mention them.

    - Excludes bot accounts.
    - Works only in a guild (not in DMs).
    """
    if ctx.guild is None:
        await ctx.send("This command works only in servers (not in DMs).")
        return

    # Exclude bots so the list focuses on real users
    user_members = [m for m in ctx.guild.members]
    if not user_members:
        await ctx.send("No (non-bot) members found in this server.")
        return

    # Sort by display name for a stable order
    user_members.sort(key=lambda m: m.display_name.lower())

    lines = [f"<@{m.id}> — {m.display_name}" for m in user_members]
    header = f"Server members ({len(lines)}):\n"
    text = header + "\n".join(lines)

    # Split into Discord-friendly chunks
    for i in range(0, len(text), 2000):
        await ctx.send(text[i : i + 2000])
