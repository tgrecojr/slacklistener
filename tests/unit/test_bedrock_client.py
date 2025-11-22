"""Tests for AWS Bedrock client."""

import base64
import json
from unittest.mock import Mock, patch, MagicMock

import pytest
from botocore.exceptions import ClientError

from src.services.bedrock_client import BedrockClient


@pytest.fixture
def bedrock_client():
    """Create a Bedrock client instance."""
    return BedrockClient(region="us-east-1", timeout=30)


def test_bedrock_client_initialization():
    """Test Bedrock client initialization."""
    client = BedrockClient(region="us-west-2", timeout=60)
    assert client.region == "us-west-2"
    assert client.client is not None


def test_create_simple_message():
    """Test creating a simple text message."""
    client = BedrockClient()
    message = client.create_simple_message("Hello, Claude!")

    assert message["role"] == "user"
    assert len(message["content"]) == 1
    assert message["content"][0]["type"] == "text"
    assert message["content"][0]["text"] == "Hello, Claude!"


def test_format_message_text_only():
    """Test formatting a text-only message."""
    client = BedrockClient()
    message = client.format_message("Test message")

    assert message["role"] == "user"
    assert len(message["content"]) == 1
    assert message["content"][0]["type"] == "text"
    assert message["content"][0]["text"] == "Test message"


def test_format_message_with_image(sample_image_info):
    """Test formatting a message with an image."""
    client = BedrockClient()
    message = client.format_message("Describe this image", images=[sample_image_info])

    assert message["role"] == "user"
    assert len(message["content"]) == 2

    # Check image content
    image_content = message["content"][0]
    assert image_content["type"] == "image"
    assert image_content["source"]["type"] == "base64"
    assert image_content["source"]["media_type"] == "image/png"
    assert len(image_content["source"]["data"]) > 0

    # Check text content
    text_content = message["content"][1]
    assert text_content["type"] == "text"
    assert text_content["text"] == "Describe this image"


def test_format_message_multiple_images(sample_image_bytes):
    """Test formatting a message with multiple images."""
    client = BedrockClient()
    images = [
        {"data": sample_image_bytes, "mimetype": "image/png", "filename": "image1.png"},
        {
            "data": sample_image_bytes,
            "mimetype": "image/jpeg",
            "filename": "image2.jpg",
        },
    ]

    message = client.format_message("Describe these images", images=images)

    assert len(message["content"]) == 3  # 2 images + 1 text
    assert message["content"][0]["source"]["media_type"] == "image/png"
    assert message["content"][1]["source"]["media_type"] == "image/jpeg"


def test_format_message_backwards_compatibility(sample_image_bytes):
    """Test backwards compatibility with raw bytes."""
    client = BedrockClient()
    # Old format: just bytes
    message = client.format_message("Test", images=[sample_image_bytes])

    assert len(message["content"]) == 2
    assert message["content"][0]["type"] == "image"
    assert message["content"][0]["source"]["media_type"] == "image/jpeg"  # Default


@patch("src.services.bedrock_client.boto3")
def test_invoke_claude_success(mock_boto3, bedrock_client, mock_bedrock_response):
    """Test successful Claude invocation."""
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_bedrock_response
    mock_boto3.client.return_value = mock_client

    # Re-initialize to use mocked boto3
    bedrock_client.client = mock_client

    messages = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]

    response = bedrock_client.invoke_claude(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        messages=messages,
        system_prompt="You are helpful",
        max_tokens=1024,
        temperature=0.7,
    )

    assert response == "This is a test response from Claude."
    mock_client.invoke_model.assert_called_once()


@patch("src.services.bedrock_client.boto3")
def test_invoke_claude_with_vision(
    mock_boto3, bedrock_client, mock_bedrock_vision_response, sample_image_info
):
    """Test Claude invocation with vision (image)."""
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_bedrock_vision_response
    mock_boto3.client.return_value = mock_client

    bedrock_client.client = mock_client

    message = bedrock_client.format_message(
        "What is in this image?", images=[sample_image_info]
    )
    messages = [message]

    response = bedrock_client.invoke_claude(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        messages=messages,
        max_tokens=2048,
    )

    assert "red pixel" in response.lower()
    mock_client.invoke_model.assert_called_once()

    # Verify the request body includes image
    call_args = mock_client.invoke_model.call_args
    body = json.loads(call_args.kwargs["body"])
    assert body["messages"][0]["content"][0]["type"] == "image"
    assert body["messages"][0]["content"][0]["source"]["media_type"] == "image/png"


@patch("src.services.bedrock_client.boto3")
def test_invoke_claude_client_error(mock_boto3, bedrock_client):
    """Test handling of Bedrock client errors."""
    mock_client = MagicMock()
    mock_client.invoke_model.side_effect = ClientError(
        {"Error": {"Code": "ValidationException", "Message": "Invalid model"}},
        "InvokeModel",
    )
    mock_boto3.client.return_value = mock_client

    bedrock_client.client = mock_client

    messages = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]

    response = bedrock_client.invoke_claude(model_id="invalid-model", messages=messages)

    assert response is None


@patch("src.services.bedrock_client.boto3")
def test_invoke_claude_unexpected_response_format(mock_boto3, bedrock_client):
    """Test handling of unexpected response format."""
    mock_client = MagicMock()
    mock_response = {
        "body": Mock(
            read=Mock(return_value=json.dumps({"unexpected": "format"}).encode())
        )
    }
    mock_client.invoke_model.return_value = mock_response
    mock_boto3.client.return_value = mock_client

    bedrock_client.client = mock_client

    messages = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]

    response = bedrock_client.invoke_claude(model_id="test-model", messages=messages)

    assert response is None


def test_image_base64_encoding(sample_image_bytes):
    """Test that images are properly base64 encoded."""
    client = BedrockClient()
    image_info = {
        "data": sample_image_bytes,
        "mimetype": "image/png",
        "filename": "test.png",
    }

    message = client.format_message("Test", images=[image_info])

    encoded_data = message["content"][0]["source"]["data"]

    # Verify it's valid base64
    decoded = base64.b64decode(encoded_data)
    assert decoded == sample_image_bytes


def test_format_message_preserves_mimetype():
    """Test that different MIME types are preserved."""
    client = BedrockClient()
    mimetypes = ["image/png", "image/jpeg", "image/webp", "image/gif"]

    for mimetype in mimetypes:
        image_info = {
            "data": b"fake_image_data",
            "mimetype": mimetype,
            "filename": "test",
        }
        message = client.format_message("Test", images=[image_info])

        assert message["content"][0]["source"]["media_type"] == mimetype
