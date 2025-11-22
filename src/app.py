"""Main Slack application."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .handlers.message_handler import MessageHandler
from .handlers.command_handler import CommandHandler
from .services.bedrock_client import BedrockClient
from .utils.config import load_config

# Load environment variables
load_dotenv()


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Main application entry point."""
    # Load configuration
    try:
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Setup logging
    setup_logging(config.settings.log_level)
    logger = logging.getLogger(__name__)

    # Get Slack tokens from environment
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    slack_app_token = os.getenv("SLACK_APP_TOKEN")

    if not slack_bot_token or not slack_app_token:
        logger.error(
            "Missing required environment variables: SLACK_BOT_TOKEN and/or SLACK_APP_TOKEN"
        )
        sys.exit(1)

    # Initialize Slack app with Socket Mode
    app = App(token=slack_bot_token)

    # Get bot user ID
    try:
        auth_response = app.client.auth_test()
        bot_user_id = auth_response["user_id"]
        logger.info(f"Bot user ID: {bot_user_id}")
    except Exception as e:
        logger.error(f"Error getting bot user ID: {e}")
        sys.exit(1)

    # Initialize Bedrock client
    bedrock_client = BedrockClient(
        region=os.getenv("AWS_REGION", "us-east-1"),
        timeout=config.settings.bedrock_timeout,
    )

    # Initialize handlers
    message_handler = MessageHandler(
        app=app,
        config=config,
        bedrock_client=bedrock_client,
        bot_user_id=bot_user_id,
        bot_token=slack_bot_token,
    )

    command_handler = CommandHandler(
        app=app,
        config=config,
        bedrock_client=bedrock_client,
    )

    # Register message event listener
    @app.event("message")
    def handle_message_events(event, say, client):
        """Handle message events."""
        message_handler.handle_message(event, say, client)

    # Register slash command handlers
    for cmd_config in config.slash_commands:
        if cmd_config.enabled:
            command_name = cmd_config.command

            # Create a closure to capture the current command_name
            def make_handler():
                _cmd = command_name  # Capture in closure

                def handler(ack, command, say):
                    command_handler.handle_command(ack, command, say)

                return handler

            app.command(command_name)(make_handler())
            logger.info(f"Registered slash command: {command_name}")

    # Log configured channels
    for channel_config in config.channels:
        if channel_config.enabled:
            logger.info(
                f"Monitoring channel: {channel_config.channel_name} "
                f"({channel_config.channel_id}) - "
                f"Keywords: {channel_config.keywords or 'ALL'}"
            )

    # Start the app
    logger.info("Starting Slack Listener application...")
    handler = SocketModeHandler(app, slack_app_token)
    handler.start()


if __name__ == "__main__":
    main()
