# Slack Listener with OpenRouter LLM Support

A Python Slack application that listens to configured channels for keywords and images, then uses OpenRouter to access multiple LLM providers (Anthropic Claude, OpenAI GPT, etc.) to generate intelligent responses. Supports both passive channel monitoring and slash commands.

## Features

- **Channel Monitoring**: Listen to specific Slack channels and respond based on keyword triggers
- **Image Analysis**: Process messages with images using Claude's vision capabilities
- **Slash Commands**: Create custom slash commands for explicit user invocations
- **OpenRouter Integration**: Access multiple LLM providers through a single API
  - Anthropic Claude (Claude 3.5 Sonnet, Haiku, Opus)
  - OpenAI (GPT-4o, GPT-4, etc.)
  - Many other models via OpenRouter
- **Flexible Configuration**: YAML-based configuration for easy management of channels and responses
- **Thread Responses**: Reply in threads to keep channels organized
- **Reaction Support**: Add emoji reactions to messages being processed

## Vision & Image Analysis

The application fully supports **Claude's vision capabilities** through OpenRouter, allowing you to:

### Supported Image Formats
- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)
- **WebP** (.webp)
- **GIF** (.gif)

The application automatically detects the correct MIME type from Slack and forwards it to the LLM.

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
4. Sent to the LLM via OpenRouter with your system prompt
5. LLM analyzes the image and generates a response
6. Response posted back to Slack (typically in thread)

See `config/config.example.yaml` for complete examples of image analysis channels.

## Tools & Context Enrichment

The application supports **tools** (also called helpers) that execute before LLM invocation to enrich the context with real-time data. This allows the LLM to provide more accurate and contextual responses.

### How Tools Work

1. Tools are configured in `config.yaml` for slash commands or channels
2. Before the LLM is invoked, each configured tool executes
3. Tool results are appended to the system prompt
4. The enriched prompt is sent to the LLM along with the user's message
5. The LLM generates a response based on both the user input and tool data

### Available Tools

#### OpenWeatherMap Tool

Fetches current weather and 24-hour forecast from OpenWeatherMap API.

**Configuration:**
```yaml
tools:
  - type: "openweathermap"
    api_key: "${OPENWEATHERMAP_API_KEY}"
    location: "Boston,MA,US"  # City, State, Country
    # OR use coordinates:
    # latitude: 42.3601
    # longitude: -71.0589
    units: "imperial"  # imperial (F), metric (C), or standard (K)
    language: "en"
```

**Use Cases:**
- Weather-aware recommendations (what to wear for a run)
- Outdoor activity planning
- Travel preparation
- Event planning

#### RSS Feed Tool

Fetches and tracks RSS feed articles, returning only new stories.

**Configuration:**
```yaml
tools:
  - type: "rssfeed"
    feed_urls:
      - "https://feeds.bbci.co.uk/news/technology/rss.xml"
      - "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
    data_file: "data/news_seen_articles.json"  # Persistent storage
    max_stories: 10
```

**Use Cases:**
- News summarization (`/news` command)
- Content monitoring
- Feed aggregation

**Example Integration:**
```yaml
slash_commands:
  - command: "/run"
    description: "Get running advice based on current weather"
    llm:
      api_key: "${OPENROUTER_API_KEY}"
      model: "anthropic/claude-3.5-sonnet"
      max_tokens: 1024
      temperature: 0.7
    system_prompt: |
      You are a running coach. Based on the weather data provided,
      advise on clothing, timing, and safety considerations.
    tools:
      - type: "openweathermap"
        api_key: "${OPENWEATHERMAP_API_KEY}"
        location: "Boston,MA,US"
        units: "imperial"
```

When a user types `/run I want to go for a 5 mile run`, the tool:
1. Fetches current weather and 24-hour forecast
2. Formats data (temperature, conditions, humidity, wind)
3. Appends to system prompt
4. LLM receives both user input and weather data
5. LLM provides personalized advice based on actual conditions

### Creating Custom Tools

To create a new tool:

1. **Create tool class** in `src/tools/implementations/`:
```python
from ..tool import Tool
from typing import Dict, Any

class MyCustomTool(Tool):
    def __init__(self, param1: str, param2: int):
        self.param1 = param1
        self.param2 = param2

    def get_name(self) -> str:
        return "MyCustomTool"

    def execute(self, context: Dict[str, Any]) -> str:
        # Access user input, timestamp, etc. from context
        user_input = context.get("user_input")

        # Fetch/compute your data
        result = self._fetch_data()

        # Return formatted string to enrich prompt
        return f"Custom Data:\n{result}"
```

2. **Register in factory** (`src/tools/factory.py`):
```python
if tool_type == "mycustom":
    from .implementations.mycustom import MyCustomTool
    return MyCustomTool(
        param1=tool_config.get("param1"),
        param2=tool_config.get("param2", 42)
    )
```

3. **Use in config**:
```yaml
tools:
  - type: "mycustom"
    param1: "value"
    param2: 123
```

## OpenRouter

The application uses [OpenRouter](https://openrouter.ai) as a unified gateway to access multiple LLM providers through a single API.

### Why OpenRouter?

- **Single API**: Access Claude, GPT-4, and many other models with one API key
- **Simple Setup**: No need to manage multiple provider accounts
- **Model Flexibility**: Switch models by changing a single config value
- **Cost Tracking**: Unified billing across all providers

### Available Models (via OpenRouter)

- `anthropic/claude-3.5-sonnet` - Balanced capability and speed
- `anthropic/claude-3.5-haiku` - Fast and cost-effective
- `openai/gpt-4o` - Latest GPT-4 with vision
- `openai/gpt-4-turbo` - Fast GPT-4
- Many more at https://openrouter.ai/models

## Prerequisites

- Python 3.8 or higher
- Slack workspace with admin permissions to create apps
- [OpenRouter API Key](https://openrouter.ai/keys)
- Optional tool API keys:
  - **OpenWeatherMap API Key** (if using weather tool)

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

4. **Configure OpenRouter**:
   - Get an API key from https://openrouter.ai/keys
   - Add to `.env` as `OPENROUTER_API_KEY`

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
   - Create commands matching your `config.yaml` (e.g., `/analyze`, `/summarize`, `/news`)

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
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_APP_TOKEN=xapp-your-token
   OPENROUTER_API_KEY=sk-or-v1-your-key
   ```

2. **Application Configuration**:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

   Edit `config/config.yaml` to configure:
   - Channels to monitor
   - Keywords to trigger on
   - LLM model to use
   - System prompts for each channel/command
   - Response behavior

### Example Channel Configuration

```yaml
channels:
  - channel_id: "C01234567"
    channel_name: "support"
    enabled: true
    keywords: ["help", "issue"]
    llm:
      api_key: "${OPENROUTER_API_KEY}"
      model: "anthropic/claude-3.5-sonnet"
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
- `llm.api_key`: OpenRouter API key
- `llm.model`: OpenRouter model identifier
- `llm.max_tokens`: Maximum tokens to generate
- `llm.temperature`: Temperature for sampling (0-1)
- `system_prompt`: Instructions for the AI model
- `tools`: List of tools to execute before LLM invocation (optional)
- `response.thread_reply`: Reply in thread vs new message
- `response.add_reaction`: Emoji reaction to add (optional)

### Slash Command Configuration

- `command`: Command name (e.g., `/analyze`)
- `description`: Description of the command
- `enabled`: Whether this command is active
- `llm`: Same as channel LLM config
- `system_prompt`: Instructions for the AI model
- `tools`: List of tools to execute before LLM invocation (optional)

### Global Settings

- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `max_message_length`: Maximum message length to process
- `llm_timeout`: Timeout for LLM API calls
- `ignore_bot_messages`: Ignore messages from other bots
- `ignore_self`: Ignore messages from this bot

## Project Structure

```
slacklistener/
├── src/
│   ├── handlers/
│   │   ├── message_handler.py   # Channel message handling
│   │   └── command_handler.py   # Slash command handling
│   ├── llm/
│   │   ├── __init__.py          # OpenRouter client export
│   │   └── openrouter.py        # OpenRouter LLM client
│   ├── tools/
│   │   ├── tool.py              # Tool base class
│   │   ├── factory.py           # Tool factory
│   │   └── implementations/
│   │       ├── openweathermap.py    # OpenWeatherMap tool
│   │       └── rssfeed.py           # RSS Feed tool
│   ├── utils/
│   │   ├── config.py            # Configuration loading
│   │   └── slack_helpers.py     # Slack utilities
│   └── app.py                   # Main application
├── config/
│   ├── config.yaml              # Your configuration (not in git)
│   └── config.example.yaml      # Example configuration
├── data/                        # Persistent data storage
│   └── .gitkeep
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

### LLM/OpenRouter errors

1. Verify `OPENROUTER_API_KEY` is set correctly
2. Check API key has sufficient credits
3. Ensure model name matches OpenRouter format (e.g., `anthropic/claude-3.5-sonnet`)
4. Check OpenRouter status at https://openrouter.ai/activity

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
  -v $(pwd)/data:/app/data \
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
2. **New Tool**: Add to `src/tools/implementations/` and register in factory
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
│   ├── test_slack_helpers.py  # Slack utilities
│   ├── test_message_handler.py # Message handling
│   ├── test_command_handler.py # Slash commands
│   ├── test_tools.py          # Tool implementations
│   └── test_rssfeed_tool.py   # RSS Feed tool tests
├── integration/               # End-to-end integration tests
│   └── test_vision_integration.py # Vision/image workflow tests
└── conftest.py               # Shared fixtures
```

#### Key Test Coverage

- **Configuration**: YAML loading, validation, channel/command lookup
- **Vision Support**: Image download, base64 encoding, multi-image messages
- **Message Handling**: Keyword matching, image detection, thread replies
- **Slash Commands**: Command parsing, error handling, response generation
- **Slack Helpers**: File downloads, image extraction, message filtering
- **Tools**: OpenWeatherMap, RSS Feed tool implementations

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
- Regularly rotate API keys and Slack tokens
- Review which channels the bot has access to

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
