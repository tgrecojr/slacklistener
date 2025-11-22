# Slack Listener with AWS Bedrock

A Python Slack application that listens to configured channels for keywords and images, then uses AWS Bedrock (Claude and other models) to generate intelligent responses. Supports both passive channel monitoring and slash commands.

## Features

- **Channel Monitoring**: Listen to specific Slack channels and respond based on keyword triggers
- **Image Analysis**: Process messages with images using Claude's vision capabilities
- **Slash Commands**: Create custom slash commands for explicit user invocations
- **AWS Bedrock Integration**: Use multiple AI models (Claude 3.5 Sonnet, Haiku, etc.) via AWS Bedrock
- **Flexible Configuration**: YAML-based configuration for easy management of channels and responses
- **Thread Responses**: Reply in threads to keep channels organized
- **Reaction Support**: Add emoji reactions to messages being processed

## Vision & Image Analysis

The application fully supports **Claude's vision capabilities** through AWS Bedrock, allowing you to:

### Supported Image Formats
- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)
- **WebP** (.webp)
- **GIF** (.gif)

The application automatically detects the correct MIME type from Slack and forwards it to Bedrock.

### Image Use Cases

Configure channels to analyze images for various purposes:

1. **Design Review**: Analyze UI/UX designs, provide feedback on layouts, accessibility, and visual hierarchy
2. **Bug Screenshots**: Identify errors in screenshots, suggest debugging steps
3. **Receipt Processing**: Extract vendor, date, amount, and line items from receipts/invoices
4. **Diagram Analysis**: Understand architecture diagrams, flowcharts, or technical drawings
5. **Code Screenshots**: Review code snippets shared as images (though text is preferred!)
6. **Product Photos**: Analyze product images for quality, composition, or defects

### How It Works

1. User uploads an image to a monitored Slack channel
2. Bot downloads the image with proper authentication
3. Image is base64-encoded with correct MIME type
4. Sent to Claude via AWS Bedrock with your system prompt
5. Claude analyzes the image and generates a response
6. Response posted back to Slack (typically in thread)

See `config/config.example.yaml` for complete examples of image analysis channels.

## Prerequisites

- Python 3.8 or higher
- AWS Account with Bedrock access
- Slack workspace with admin permissions to create apps
- AWS credentials configured (via `~/.aws/credentials` or environment variables)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd slacklistener
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS Bedrock**:
   - Ensure you have AWS credentials configured
   - Enable model access in AWS Bedrock console for the models you want to use:
     - Anthropic Claude 3.5 Sonnet
     - Anthropic Claude 3 Haiku
     - Any other models you plan to use

## Slack App Setup

1. **Create a Slack App**:
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name your app and select your workspace

2. **Configure Socket Mode**:
   - Go to "Socket Mode" in the sidebar
   - Enable Socket Mode
   - Generate an App-Level Token with `connections:write` scope
   - Save this token as `SLACK_APP_TOKEN`

3. **Configure Bot Token Scopes**:
   - Go to "OAuth & Permissions"
   - Add the following Bot Token Scopes:
     - `chat:write` - Send messages
     - `channels:history` - Read channel messages
     - `channels:read` - View channel information
     - `reactions:write` - Add reactions to messages
     - `files:read` - Access file content (for image analysis)
     - `commands` - Enable slash commands (if using)

4. **Enable Events**:
   - Go to "Event Subscriptions"
   - Enable Events
   - Subscribe to bot events:
     - `message.channels` - Listen to channel messages

5. **Create Slash Commands** (optional):
   - Go to "Slash Commands"
   - Create commands matching your `config.yaml` (e.g., `/analyze`, `/summarize`)

6. **Install App to Workspace**:
   - Go to "Install App"
   - Click "Install to Workspace"
   - Authorize the app
   - Save the Bot User OAuth Token as `SLACK_BOT_TOKEN`

7. **Invite Bot to Channels**:
   - In each channel you want to monitor, type: `/invite @YourBotName`

## Configuration

1. **Environment Variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your tokens:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_APP_TOKEN=xapp-your-token
   AWS_REGION=us-east-1
   ```

2. **Application Configuration**:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

   Edit `config/config.yaml` to configure:
   - Channels to monitor
   - Keywords to trigger on
   - Bedrock models to use
   - System prompts for each channel/command
   - Response behavior

### Example Channel Configuration

```yaml
channels:
  - channel_id: "C01234567"  # Get from Slack channel details
    channel_name: "support"
    enabled: true
    keywords:
      - "help"
      - "issue"
    case_sensitive: false
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

## Usage

1. **Run the application**:
   ```bash
   python -m src.app
   ```

2. **Test in Slack**:
   - Post a message in a configured channel with one of your keywords
   - The bot should react and respond
   - Try slash commands if configured (e.g., `/analyze What is AI?`)

## Configuration Options

### Channel Configuration

- `channel_id`: Slack channel ID (find in channel details)
- `channel_name`: Human-readable name for logging
- `enabled`: Whether this channel is active
- `keywords`: List of keywords to trigger on (empty = all messages)
- `case_sensitive`: Whether keyword matching is case-sensitive
- `require_image`: Only respond to messages with images
- `bedrock.model_id`: AWS Bedrock model ID to use
- `bedrock.max_tokens`: Maximum tokens to generate
- `bedrock.temperature`: Temperature for sampling (0-1)
- `system_prompt`: Instructions for the AI model
- `response.thread_reply`: Reply in thread vs new message
- `response.add_reaction`: Emoji reaction to add (optional)

### Slash Command Configuration

- `command`: Command name (e.g., `/analyze`)
- `description`: Description of the command
- `enabled`: Whether this command is active
- `bedrock`: Same as channel bedrock config
- `system_prompt`: Instructions for the AI model

### Global Settings

- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `max_message_length`: Maximum message length to process
- `bedrock_timeout`: Timeout for Bedrock API calls
- `ignore_bot_messages`: Ignore messages from other bots
- `ignore_self`: Ignore messages from this bot

## Supported Bedrock Models

### Anthropic Claude Models

- `anthropic.claude-3-5-sonnet-20241022-v2:0` - Latest, most capable model
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast and cost-effective
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable (if you have access)

Make sure to enable model access in the AWS Bedrock console before using.

## Project Structure

```
slacklistener/
├── src/
│   ├── handlers/
│   │   ├── message_handler.py   # Channel message handling
│   │   └── command_handler.py   # Slash command handling
│   ├── services/
│   │   └── bedrock_client.py    # AWS Bedrock integration
│   ├── utils/
│   │   ├── config.py            # Configuration loading
│   │   └── slack_helpers.py     # Slack utilities
│   └── app.py                   # Main application
├── config/
│   ├── config.yaml              # Your configuration (not in git)
│   └── config.example.yaml      # Example configuration
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── .env.example                 # Example environment file
└── README.md                    # This file
```

## Troubleshooting

### Bot doesn't respond to messages

1. Check bot is invited to the channel: `/invite @YourBotName`
2. Verify `channel_id` in config matches the Slack channel ID
3. Check keywords match the message content
4. Review logs for errors

### AWS Bedrock errors

1. Verify AWS credentials are configured correctly
2. Ensure model access is enabled in Bedrock console
3. Check `AWS_REGION` matches where you enabled models
4. Verify IAM permissions include `bedrock:InvokeModel`

### Socket Mode connection issues

1. Verify `SLACK_APP_TOKEN` is correct and starts with `xapp-`
2. Check Socket Mode is enabled in Slack app settings
3. Ensure app is installed to workspace

### Image analysis not working

1. Verify bot has `files:read` scope
2. Check you're using a vision-capable model (Claude 3.5 Sonnet)
3. Ensure `require_image` is set correctly in config

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Docker

```bash
# Build image
docker build -t slack-listener .

# Run container
docker run -d \
  --name slack-listener \
  --env-file .env \
  -v $(pwd)/config/config.yaml:/app/config/config.yaml:ro \
  slack-listener

# View logs
docker logs -f slack-listener
```

### Logging

The application logs to **stdout** following Docker best practices. This allows you to:
- Use `docker logs` to view logs
- Integrate with log aggregation systems (CloudWatch, Datadog, etc.)
- Configure Docker's logging driver for your needs

No volume mounting for logs is required.

## Development

### Running in Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with debug logging
# Edit config/config.yaml and set: log_level: "DEBUG"
python -m src.app
```

### Adding New Features

1. **New Handler**: Add to `src/handlers/`
2. **New Service**: Add to `src/services/`
3. **New Config Option**: Update `src/utils/config.py` with Pydantic models

### Testing

The application includes comprehensive unit and integration tests using pytest.

#### Install Test Dependencies

```bash
make install-dev
# Or manually:
pip install -r requirements-dev.txt
```

#### Run Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run with coverage report
make test-cov
```

#### Test Structure

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── test_config.py        # Configuration loading/validation
│   ├── test_bedrock_client.py # Bedrock API integration
│   ├── test_slack_helpers.py  # Slack utilities
│   ├── test_message_handler.py # Message handling
│   └── test_command_handler.py # Slash commands
├── integration/               # End-to-end integration tests
│   └── test_vision_integration.py # Vision/image workflow tests
└── conftest.py               # Shared fixtures
```

#### Key Test Coverage

- **Configuration**: YAML loading, validation, channel/command lookup
- **Bedrock Client**: Claude API calls, image formatting, MIME type handling
- **Vision Support**: Image download, base64 encoding, multi-image messages
- **Message Handling**: Keyword matching, image detection, thread replies
- **Slash Commands**: Command parsing, error handling, response generation
- **Slack Helpers**: File downloads, image extraction, message filtering

#### Writing New Tests

When adding new features, add corresponding tests:

```python
# tests/unit/test_my_feature.py
import pytest

def test_my_new_feature():
    """Test description."""
    # Arrange
    # Act
    # Assert
    pass
```

Use fixtures from `conftest.py` for common test data.

## Security Notes

- **Never commit** `.env` or `config/config.yaml` (they contain secrets)
- Use AWS IAM roles with minimum required permissions
- Regularly rotate Slack tokens
- Review which channels the bot has access to

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
