code aimport re

import discord
from discord.ext import commands

import ai
import constants
from logger import get_logger

logger = get_logger(__name__)

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
        logger.debug(f"Generating AI response for content: {content[:100]}...")
        response_text = await ai.generate_response(content, image_urls=image_urls)
        logger.debug(f"Received AI response: {response_text[:100]}...")

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
            try:
                # If we have a message to reply to, reply so the response is threaded
                # to the original question. Otherwise send to the provided target.
                if reply_to:
                    await reply_to.reply(chunk)
                else:
                    if isinstance(target, commands.Context):
                        await target.send(chunk)
                    else:
                        await target.send(chunk)
                logger.debug(
                    f"Successfully sent message chunk of {len(chunk)} characters"
                )
            except discord.errors.HTTPException as e:
                logger.error(
                    f"Discord HTTP error while sending message: {e}", exc_info=True
                )
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error while sending message: {e}", exc_info=True
                )
                raise

        if len(response_text) > 2000:
            logger.info(
                f"Splitting large response ({len(response_text)} chars) into chunks"
            )
            for i in range(0, len(response_text), 2000):
                await _send(response_text[i : i + 2000])
        else:
            await _send(response_text)
        logger.info("AI response sent successfully")
    except ai.APIError as e:
        logger.error(f"AI API error: {e}", exc_info=True)
        err_msg = (
            "Sorry, I encountered an error with the AI service. Please try again later."
        )
        try:
            if reply_to:
                await reply_to.reply(err_msg)
            else:
                if isinstance(target, commands.Context):
                    await target.send(err_msg)
                else:
                    await target.send(err_msg)
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error generating response: {e}", exc_info=True)
        # Try to reply if possible, otherwise send to target
        err_msg = "Sorry, I encountered an error while processing your request."
        try:
            if reply_to:
                await reply_to.reply(err_msg)
            else:
                if isinstance(target, commands.Context):
                    await target.send(err_msg)
                else:
                    await target.send(err_msg)
        except Exception as send_err:
            logger.error(f"Failed to send error message: {send_err}", exc_info=True)


async def collect_channel_history(channel, before_message=None, limit=None) -> str:
    """Collect prior messages from `channel` into a short conversation
    history suitable for prepending to the user's prompt.

    - Uses `clean_content` to avoid active pings.
    - Labels messages as `User:` or `Assistant:` so the model can follow roles.
    - Respects `config.MAX_HISTORY_MESSAGES` and `config.HISTORY_MAX_CHARS`.
    """
    try:
        if limit is None:
            limit = constants.LLMConfig.MAX_HISTORY_MESSAGES

        logger.debug(f"Collecting channel history with limit={limit}")
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

        history = "\n".join(lines)
        logger.debug(
            f"Collected {len(messages)} messages, {len(lines)} lines, {total_chars} chars for history"
        )
        return history
    except Exception as e:
        logger.error(f"Error collecting channel history: {e}", exc_info=True)
        return ""


@bot.event
async def on_ready():
    """Bot ready event - log connection and sync commands."""
    try:
        logger.info(f"✓ Bot connected to Discord - User: {bot.user}")
        logger.info(f"✓ Connected to {len(bot.guilds)} guild(s)")

        if not getattr(bot, "tree_synced", False):
            logger.info("Syncing application commands...")
            await bot.tree.sync()

            # Also sync per-guild so slash commands appear immediately
            for guild in bot.guilds:
                try:
                    await bot.tree.sync(guild=guild)
                    logger.debug(
                        f"Synced commands for guild: {guild.name} ({guild.id})"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to sync commands for guild {guild.id} ({guild.name}): {e}"
                    )

            bot.tree_synced = True  # type: ignore[attr-defined]
            logger.info("✓ Application commands synced successfully")
    except Exception as e:
        logger.error(f"Error in on_ready event: {e}", exc_info=True)


@bot.event
async def on_guild_join(guild):
    """Bot joined a new guild - sync commands."""
    try:
        logger.info(f"Bot joined new guild: {guild.name} ({guild.id})")
        await bot.tree.sync(guild=guild)
        logger.info(f"✓ Synced commands for new guild: {guild.name}")
    except Exception as e:
        logger.error(
            f"Failed to sync commands for guild {guild.id} ({guild.name}): {e}",
            exc_info=True,
        )


@bot.event
async def on_message(message):
    """Handle incoming messages."""
    try:
        # Ignore messages from the bot itself
        if message.author == bot.user:
            return

        # Only respond to messages that mention the bot
        if bot.user and bot.user.mentioned_in(message):
            logger.debug(
                f"Bot mentioned in message from {message.author} ({message.author.id}) in {message.guild.name if message.guild else 'DM'}"
            )

            # Remove the bot mention from the message (handle both <@id> and <@!id>)
            content = (
                message.content.replace(f"<@{bot.user.id}>", "")
                .replace(f"<@!{bot.user.id}>", "")
                .strip()
            )

            if not content and not message.attachments:
                logger.debug(f"Empty message with no attachments from {message.author}")
                await message.channel.send(
                    "Hi! Mention me with a question and I'll help you!"
                )
                return

            # Extract image URLs from attachments
            image_urls = []
            if message.attachments:
                logger.debug(f"Processing {len(message.attachments)} attachment(s)")
                for attachment in message.attachments:
                    try:
                        # Check if attachment is an image
                        if (
                            attachment.content_type
                            and attachment.content_type.startswith("image/")
                        ):
                            image_urls.append(attachment.url)
                            logger.debug(f"Added image attachment: {attachment.url}")
                            # Add attachment info to content if no text was provided
                            if not content:
                                content = "Analyze this image"
                    except Exception as e:
                        logger.warning(f"Error processing attachment: {e}")

            # Build recent channel history and show typing indicator
            logger.debug(f"Building channel history for {message.channel}")
            history = await collect_channel_history(
                message.channel, before_message=message
            )
            if history:
                combined = f"{history}\nUser: {content}"
            else:
                combined = f"User: {content}"

            logger.info(f"Responding to message from {message.author} with AI response")
            async with message.channel.typing():
                await send_ai_response(
                    message.channel, combined, reply_to=message, image_urls=image_urls
                )

        # Process commands
        await bot.process_commands(message)
    except discord.errors.DiscordException as e:
        logger.error(f"Discord error while processing message: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error in on_message: {e}", exc_info=True)


@bot.hybrid_command(name="help_nova", description="Display help information.")
async def help_nova(ctx):
    """Display help information."""
    try:
        logger.debug(f"Help command invoked by {ctx.author} ({ctx.author.id})")
        with open(constants.FilePaths.HELP_PROMPT_FILE, "r", encoding="utf-8") as f:
            help_text = f.read()
        await ctx.send(help_text)
        logger.info(f"Help sent to {ctx.author}")
    except FileNotFoundError as e:
        logger.error(f"Help file not found: {e}")
        await ctx.send("Sorry, I couldn't load the help file.")
    except Exception as e:
        logger.error(f"Error in help_nova command: {e}", exc_info=True)
        await ctx.send("Sorry, I encountered an error while loading help information.")


@bot.command(name="members")
async def members(ctx):
    """List server members with mention syntax so NOVA can mention them.

    - Excludes bot accounts.
    - Works only in a guild (not in DMs).
    """
    try:
        logger.debug(f"Members command invoked by {ctx.author} in {ctx.guild}")

        if ctx.guild is None:
            logger.warning(f"Members command attempted in DM by {ctx.author}")
            await ctx.send("This command works only in servers (not in DMs).")
            return

        # Exclude bots so the list focuses on real users
        user_members = [m for m in ctx.guild.members]
        if not user_members:
            logger.info(f"No members found in guild {ctx.guild.id}")
            await ctx.send("No (non-bot) members found in this server.")
            return

        # Sort by display name for a stable order
        user_members.sort(key=lambda m: m.display_name.lower())

        lines = [f"<@{m.id}> — {m.display_name}" for m in user_members]
        header = f"Server members ({len(lines)}):\n"
        text = header + "\n".join(lines)

        logger.info(
            f"Sending members list ({len(user_members)} members) to {ctx.author}"
        )
        # Split into Discord-friendly chunks
        for i in range(0, len(text), 2000):
            await ctx.send(text[i : i + 2000])
    except Exception as e:
        logger.error(f"Error in members command: {e}", exc_info=True)
        await ctx.send("Sorry, I encountered an error while listing members.")
