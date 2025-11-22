# Quick Start Guide

Get your Slack Listener up and running in 5 minutes!

## 1. Initial Setup (One-Time)

```bash
# Run the setup script
bash setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/config.example.yaml config/config.yaml
```

## 2. Get Your Slack Tokens

### Create a Slack App
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name it (e.g., "AI Assistant") and select your workspace

### Get App Token (SLACK_APP_TOKEN)
1. Go to **"Socket Mode"** in sidebar
2. Enable Socket Mode
3. Click **"Generate Token"** with name "socket-token"
4. Add scope: `connections:write`
5. Copy the token (starts with `xapp-`)

### Get Bot Token (SLACK_BOT_TOKEN)
1. Go to **"OAuth & Permissions"**
2. Add these Bot Token Scopes:
   - `chat:write`
   - `channels:history`
   - `channels:read`
   - `reactions:write`
   - `files:read`
   - `commands` (if using slash commands)
3. Click **"Install to Workspace"** at top
4. Authorize the app
5. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

### Update .env file
```bash
SLACK_BOT_TOKEN=xoxb-your-actual-token-here
SLACK_APP_TOKEN=xapp-your-actual-token-here
AWS_REGION=us-east-1
```

## 3. Get Channel IDs

### Method 1: From Slack Desktop/Web
1. Open the channel in Slack
2. Click the channel name at top
3. Scroll to bottom of the popup
4. Look for the Channel ID (e.g., `C01234567`)

### Method 2: Right-click Method
1. Right-click on the channel name in sidebar
2. Select **"Copy"** → **"Copy link"**
3. The ID is at the end of the URL: `https://app.slack.com/client/T.../C01234567`

### Invite Bot to Channels
In each channel you want to monitor:
```
/invite @YourBotName
```

## 4. Configure AWS Bedrock

### Setup AWS Credentials
```bash
# Option 1: AWS CLI (recommended)
aws configure

# Option 2: Environment variables in .env
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

### Enable Model Access
1. Go to AWS Console → Bedrock
2. Click **"Model access"** in sidebar
3. Click **"Enable specific models"**
4. Select:
   - Anthropic Claude 3.5 Sonnet
   - Anthropic Claude 3 Haiku (optional, cheaper/faster)
5. Click **"Save changes"**

Wait a few minutes for access to be granted.

## 5. Configure Your Bot

Edit `config/config.yaml`:

```yaml
channels:
  - channel_id: "C01234567"  # Your actual channel ID
    channel_name: "support"   # Any name you want
    enabled: true
    keywords:
      - "help"
      - "issue"
    bedrock:
      model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
      region: "us-east-1"
      max_tokens: 1024
      temperature: 0.7
    system_prompt: |
      You are a helpful support assistant.
    response:
      thread_reply: true
      add_reaction: "eyes"
```

## 6. Run the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python run.py

# Or using make
make run
```

You should see:
```
INFO - Bot user ID: U01234567
INFO - Monitoring channel: support (C01234567) - Keywords: ['help', 'issue']
INFO - Starting Slack Listener application...
```

## 7. Test It!

1. Go to your configured Slack channel
2. Type a message with one of your keywords: `I need help with something`
3. The bot should:
   - Add a reaction (👀 by default)
   - Reply in a thread with an AI-generated response

## Common Issues

### "Configuration file not found"
```bash
cp config/config.example.yaml config/config.yaml
# Then edit config/config.yaml
```

### "Missing SLACK_BOT_TOKEN"
Make sure `.env` file exists and has the tokens:
```bash
cp .env.example .env
# Then edit .env with your actual tokens
```

### "Bot doesn't respond"
1. Check bot is invited to channel: `/invite @YourBotName`
2. Verify channel_id in config matches the Slack channel ID
3. Check message contains a configured keyword
4. Look at logs for errors

### "AWS Bedrock errors"
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify model access enabled in Bedrock console
3. Ensure region in config matches where you enabled models

## Next Steps

- Add more channels to `config/config.yaml`
- Create slash commands in Slack app settings
- Configure different AI models for different use cases
- Customize system prompts for better responses

## Quick Reference

### Useful Commands
```bash
make setup    # Initial setup
make run      # Run the application
make clean    # Clean up cache files
```

### Configuration Files
- `.env` - Slack tokens and AWS config
- `config/config.yaml` - Channels, commands, prompts

### Logs
The application logs to stdout (console).

To save logs to a file:
```bash
python run.py 2>&1 | tee app.log
```

With Docker:
```bash
docker logs slack-listener           # View logs
docker logs -f slack-listener         # Follow logs in real-time
docker logs --tail 100 slack-listener # Last 100 lines
```

## Getting Help

Check the full README.md for detailed documentation, or open an issue on GitHub.
