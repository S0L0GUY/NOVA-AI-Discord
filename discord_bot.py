import discord
from discord.ext import commands

import ai


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


async def send_ai_response(channel, content: str):
    """Fetch a response from the AI and send it to the channel.

    Handles long messages by splitting into 2000-character chunks.
    """
    try:
        response_text = ai.generate_response(content)
        if len(response_text) > 2000:
            for i in range(0, len(response_text), 2000):
                await channel.send(response_text[i:i+2000])
        else:
            await channel.send(response_text)
    except Exception as e:
        print(f"Error generating response: {e}")
        await channel.send(
            "Sorry, I encountered an error while processing your request."
        )


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Connected to {len(bot.guilds)} guild(s)')


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Only respond to messages that mention the bot
    if bot.user and bot.user.mentioned_in(message):
        # Remove the bot mention from the message
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()

        if not content:
            await message.channel.send(
                "Hi! Mention me with a question and I'll help you!"
            )
            return

        # Show typing indicator
        async with message.channel.typing():
            await send_ai_response(message.channel, content)

    # Process commands
    await bot.process_commands(message)


@bot.command(name='ask')
async def ask(ctx, *, question):
    """Command to ask the AI a question."""
    async with ctx.typing():
        await send_ai_response(ctx, question)


@bot.command(name='help_nova')
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
