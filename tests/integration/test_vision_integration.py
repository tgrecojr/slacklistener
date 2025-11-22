"""Integration tests for vision/image processing capabilities."""

import base64
import json
from unittest.mock import Mock, patch, MagicMock

import pytest
import responses

from src.handlers.message_handler import MessageHandler
from src.services.bedrock_client import BedrockClient
from src.utils.config import AppConfig, ChannelConfig, BedrockConfig, ResponseConfig, GlobalSettings


@pytest.fixture
def vision_channel_config():
    """Configuration for vision-enabled channel."""
    return ChannelConfig(
        channel_id="C_VISION",
        channel_name="design-review",
        enabled=True,
        keywords=[],
        require_image=True,
        bedrock=BedrockConfig(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region="us-east-1",
            max_tokens=2048,
            temperature=0.7,
        ),
        system_prompt="You are a design review expert. Analyze the provided image in detail.",
        response=ResponseConfig(thread_reply=True, add_reaction="eyes"),
    )


@pytest.fixture
def vision_app_config(vision_channel_config):
    """App config with vision channel."""
    return AppConfig(
        channels=[vision_channel_config],
        slash_commands=[],
        settings=GlobalSettings(),
    )


class TestVisionIntegration:
    """Integration tests for vision capabilities."""

    @responses.activate
    @patch("src.services.bedrock_client.boto3")
    def test_complete_image_workflow(
        self, mock_boto3, vision_app_config, sample_image_bytes, mock_bedrock_vision_response
    ):
        """Test complete workflow: Slack image -> Bedrock vision -> Response."""
        # Setup Bedrock mock
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_vision_response
        mock_boto3.client.return_value = mock_bedrock

        # Create real clients
        bedrock_client = BedrockClient(region="us-east-1")
        bedrock_client.client = mock_bedrock

        # Mock Slack app
        app = MagicMock()
        app.client = MagicMock()

        # Create message handler
        handler = MessageHandler(
            app=app,
            config=vision_app_config,
            bedrock_client=bedrock_client,
            bot_user_id="U_BOT",
            bot_token="xoxb-test-token",
        )

        # Create Slack event with image
        image_url = "https://files.slack.com/files-pri/T12345/screenshot.png"
        event = {
            "type": "message",
            "user": "U_USER",
            "text": "Please review this design",
            "channel": "C_VISION",
            "ts": "1234567890.123456",
            "files": [
                {
                    "id": "F12345",
                    "name": "design.png",
                    "mimetype": "image/png",
                    "url_private": image_url,
                }
            ],
        }

        # Mock file download
        responses.add(responses.GET, image_url, body=sample_image_bytes, status=200)

        # Mock Slack client methods
        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        # Handle the message
        handler.handle_message(event, say, client)

        # Verify reaction was added
        client.reactions_add.assert_called_once_with(
            channel="C_VISION", timestamp="1234567890.123456", name="eyes"
        )

        # Verify Bedrock was called
        assert mock_bedrock.invoke_model.called
        bedrock_call = mock_bedrock.invoke_model.call_args

        # Verify request structure
        body = json.loads(bedrock_call.kwargs["body"])
        assert body["messages"][0]["role"] == "user"
        assert len(body["messages"][0]["content"]) == 2  # Image + text

        # Verify image content
        image_content = body["messages"][0]["content"][0]
        assert image_content["type"] == "image"
        assert image_content["source"]["media_type"] == "image/png"
        assert image_content["source"]["type"] == "base64"

        # Verify image data is valid base64
        image_data = image_content["source"]["data"]
        decoded = base64.b64decode(image_data)
        assert decoded == sample_image_bytes

        # Verify text content
        text_content = body["messages"][0]["content"][1]
        assert text_content["type"] == "text"
        assert text_content["text"] == "Please review this design"

        # Verify system prompt
        assert body["system"] == "You are a design review expert. Analyze the provided image in detail."

        # Verify response was sent
        say.assert_called_once()
        response_text = say.call_args.kwargs["text"]
        assert "red pixel" in response_text.lower()
        assert say.call_args.kwargs["thread_ts"] == "1234567890.123456"

    @responses.activate
    @patch("src.services.bedrock_client.boto3")
    def test_multiple_images_workflow(
        self, mock_boto3, vision_app_config, sample_image_bytes, mock_bedrock_vision_response
    ):
        """Test handling multiple images in one message."""
        # Setup Bedrock mock
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_vision_response
        mock_boto3.client.return_value = mock_bedrock

        bedrock_client = BedrockClient(region="us-east-1")
        bedrock_client.client = mock_bedrock

        app = MagicMock()
        handler = MessageHandler(
            app=app,
            config=vision_app_config,
            bedrock_client=bedrock_client,
            bot_user_id="U_BOT",
            bot_token="xoxb-test-token",
        )

        # Event with multiple images
        event = {
            "type": "message",
            "user": "U_USER",
            "text": "Compare these designs",
            "channel": "C_VISION",
            "ts": "1234567890.123456",
            "files": [
                {
                    "name": "design1.png",
                    "mimetype": "image/png",
                    "url_private": "https://files.slack.com/design1.png",
                },
                {
                    "name": "design2.jpg",
                    "mimetype": "image/jpeg",
                    "url_private": "https://files.slack.com/design2.jpg",
                },
            ],
        }

        # Mock downloads
        for file in event["files"]:
            responses.add(responses.GET, file["url_private"], body=sample_image_bytes, status=200)

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        handler.handle_message(event, say, client)

        # Verify Bedrock was called
        bedrock_call = mock_bedrock.invoke_model.call_args
        body = json.loads(bedrock_call.kwargs["body"])

        # Should have 2 images + 1 text = 3 content blocks
        assert len(body["messages"][0]["content"]) == 3

        # Verify first image is PNG
        assert body["messages"][0]["content"][0]["source"]["media_type"] == "image/png"

        # Verify second image is JPEG
        assert body["messages"][0]["content"][1]["source"]["media_type"] == "image/jpeg"

    @patch("src.services.bedrock_client.boto3")
    def test_vision_error_handling(self, mock_boto3, vision_app_config):
        """Test error handling in vision workflow."""
        # Setup Bedrock to fail
        mock_bedrock = MagicMock()
        from botocore.exceptions import ClientError

        mock_bedrock.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid input"}}, "InvokeModel"
        )
        mock_boto3.client.return_value = mock_bedrock

        bedrock_client = BedrockClient(region="us-east-1")
        bedrock_client.client = mock_bedrock

        app = MagicMock()
        handler = MessageHandler(
            app=app,
            config=vision_app_config,
            bedrock_client=bedrock_client,
            bot_user_id="U_BOT",
            bot_token="xoxb-test-token",
        )

        # Create message with image
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://files.slack.com/image.png",
                body=b"fake_image_data",
                status=200,
            )

            event = {
                "type": "message",
                "user": "U_USER",
                "text": "Review this",
                "channel": "C_VISION",
                "ts": "123",
                "files": [
                    {
                        "name": "image.png",
                        "mimetype": "image/png",
                        "url_private": "https://files.slack.com/image.png",
                    }
                ],
            }

            say = Mock()
            client = Mock()
            client.reactions_add = Mock()

            handler.handle_message(event, say, client)

            # Should handle error gracefully (not crash)
            # Should not send response on error
            say.assert_not_called()

    @pytest.mark.parametrize(
        "mimetype,expected",
        [
            ("image/png", "image/png"),
            ("image/jpeg", "image/jpeg"),
            ("image/webp", "image/webp"),
            ("image/gif", "image/gif"),
        ],
    )
    def test_image_mimetype_preservation(self, mimetype, expected):
        """Test that different image MIME types are preserved."""
        client = BedrockClient()
        image_info = {
            "data": b"fake_image_data",
            "mimetype": mimetype,
            "filename": f"test.{mimetype.split('/')[-1]}",
        }

        message = client.format_message("Test", images=[image_info])

        assert message["content"][0]["source"]["media_type"] == expected
