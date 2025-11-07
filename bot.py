"""
NOVA-AI Discord Bot
A simple Discord bot powered by Google's Generative AI (Gemini).
"""

import os
import discord
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure GenAI
genai.configure(api_key=os.getenv('GENAI_API_KEY'))

# Initialize the model
model = genai.GenerativeModel('gemini-pro')

# Configure Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


async def send_ai_response(channel, content):
    """Helper function to send AI response, handling long messages."""
    try:
        response = model.generate_content(content)
        
        if response.text:
            # Discord has a 2000 character limit
            if len(response.text) > 2000:
                # Split long messages
                chunks = [response.text[i:i+2000] for i in range(0, len(response.text), 2000)]
                for chunk in chunks:
                    await channel.send(chunk)
            else:
                await channel.send(response.text)
        else:
            await channel.send("I couldn't generate a response. Please try again.")
    except Exception as e:
        print(f"Error generating response: {e}")
        await channel.send("Sorry, I encountered an error while processing your request.")


@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Connected to {len(bot.guilds)} guild(s)')


@bot.event
async def on_message(message):
    """Event handler for incoming messages."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Only respond to messages that mention the bot
    if bot.user.mentioned_in(message):
        # Remove the bot mention from the message
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if not content:
            await message.channel.send("Hi! Mention me with a question and I'll help you!")
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
    help_text = """
**NOVA-AI Discord Bot Help**

**Ways to interact with me:**
1. Mention me (@NOVA-AI) followed by your question
2. Use the `!ask` command followed by your question

**Examples:**
- @NOVA-AI What is artificial intelligence?
- !ask Tell me a joke

**Note:** I'm powered by Google's Gemini AI!
    """
    await ctx.send(help_text)


if __name__ == '__main__':
    # Get Discord token from environment
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord token.")
        exit(1)
    
    if not os.getenv('GENAI_API_KEY'):
        print("Error: GENAI_API_KEY not found in environment variables!")
        print("Please create a .env file with your GenAI API key.")
        exit(1)
    
    # Run the bot
    bot.run(token)
