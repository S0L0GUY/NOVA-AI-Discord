# NOVA-AI-Discord
A Simplistic version of NOVA-AI that runs in Discord, powered by Google's Generative AI (Gemini).

## Features
- 🤖 AI-powered responses using Google's Gemini model
- 💬 Responds to mentions and commands
- 🚀 Simple and easy to set up
- 🔒 Secure environment variable configuration

## Prerequisites
- Python 3.8 or higher
- A Discord account
- A Google AI Studio API key

## Discord Bot Setup

### Step 1: Create a Discord Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Give your application a name (e.g., "NOVA-AI")
4. Click **"Create"**

### Step 2: Create a Bot User
1. In your application, navigate to the **"Bot"** section in the left sidebar
2. Click **"Add Bot"**
3. Click **"Yes, do it!"** to confirm
4. Under the **"TOKEN"** section, click **"Reset Token"** and then **"Copy"** to copy your bot token
   - ⚠️ **Keep this token secret!** Never share it or commit it to version control

### Step 3: Configure Bot Permissions
1. Still in the **"Bot"** section, scroll down to **"Privileged Gateway Intents"**
2. Enable the following intents:
   - ✅ **MESSAGE CONTENT INTENT** (required for reading messages)
   - ✅ **SERVER MEMBERS INTENT** (optional, for member information)

### Step 4: Generate Invite Link
1. Navigate to the **"OAuth2"** section, then **"URL Generator"**
2. Under **"SCOPES"**, select:
   - ✅ **bot**
3. Under **"BOT PERMISSIONS"**, select:
   - ✅ **Send Messages**
   - ✅ **Read Messages/View Channels**
   - ✅ **Read Message History**
4. Copy the generated URL at the bottom
5. Open the URL in your browser and select a server to add your bot to

## Google GenAI Setup

### Get Your API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy your API key
   - ⚠️ **Keep this key secret!** Never share it or commit it to version control

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/S0L0GUY/NOVA-AI-Discord.git
cd NOVA-AI-Discord
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your tokens:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   GENAI_API_KEY=your_genai_api_key_here
   ```

### 4. Run the Bot
```bash
python bot.py
```

If everything is set up correctly, you should see:
```
NOVA-AI has connected to Discord!
Connected to X guild(s)
```

## Usage

### Mention the Bot
Simply mention the bot in any channel where it has access:
```
@NOVA-AI What is artificial intelligence?
```

### Use Commands
You can also use the `!ask` command:
```
!ask Tell me a joke
```

### Get Help
Use the help command to see available options:
```
!help_nova
```

## How It Works
1. The bot listens for mentions or the `!ask` command
2. When triggered, it sends your message to Google's Gemini AI
3. The AI generates a response
4. The bot sends the response back to your Discord channel

## Troubleshooting

### Bot doesn't respond
- Make sure **MESSAGE CONTENT INTENT** is enabled in the Discord Developer Portal
- Check that the bot has permission to read and send messages in the channel
- Verify your `.env` file has the correct tokens

### "Error: DISCORD_TOKEN not found"
- Make sure you created a `.env` file (not `.env.example`)
- Verify the token is correctly copied into the `.env` file

### "Error generating response"
- Check that your GenAI API key is valid
- Ensure you have internet connectivity
- Verify you haven't exceeded API rate limits

## Project Structure
```
NOVA-AI-Discord/
├── bot.py              # Main bot application
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .env               # Your environment variables (not in git)
└── README.md          # This file
```

## Security Notes
- ⚠️ **Never commit your `.env` file** to version control
- ⚠️ **Never share your Discord token or GenAI API key**
- The `.env` file is already included in `.gitignore` to prevent accidental commits

## License
See the [LICENSE](LICENSE) file for details.

## Support
If you encounter any issues, please open an issue on the [GitHub repository](https://github.com/S0L0GUY/NOVA-AI-Discord/issues).

## Docker

- **Build**: Create the image from the project directory.

```powershell
docker build -t nova-ai-discord .
```

- **Run**: Provide secrets at runtime. Using an env file is simplest:

```powershell
docker run -d --name nova_bot --env-file .env nova-ai-discord
```

- **Or** pass env vars directly:

```powershell
docker run -d --name nova_bot -e DISCORD_TOKEN="<token>" -e GENAI_API_KEY="<key>" nova-ai-discord
```

- **Notes**: The image does not include your `.env` file by design. Do not commit secrets to source control. The container entrypoint runs `python bot.py` which reads `DISCORD_TOKEN` and `GENAI_API_KEY` from environment variables.
