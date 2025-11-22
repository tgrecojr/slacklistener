#!/usr/bin/env python
"""
Simple test script to verify AWS Bedrock vision capabilities.
This helps you test that your Bedrock setup works before integrating with Slack.
"""

import base64
import json
import sys
from pathlib import Path

import boto3
from botocore.config import Config


def test_vision_with_local_image(
    image_path: str, prompt: str = "What do you see in this image?"
):
    """
    Test Claude vision with a local image file.

    Args:
        image_path: Path to local image file
        prompt: Question to ask about the image
    """
    # Read image file
    img_path = Path(image_path)
    if not img_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    # Detect MIME type from extension
    ext = img_path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_types.get(ext, "image/jpeg")

    print(f"Testing with image: {image_path}")
    print(f"Detected MIME type: {mime_type}")
    print(f"Prompt: {prompt}")
    print("-" * 60)

    # Read and encode image
    with open(img_path, "rb") as f:
        image_data = f.read()

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Create Bedrock client
    config = Config(region_name="us-east-1")
    bedrock = boto3.client("bedrock-runtime", config=config)

    # Build request
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }

    try:
        # Call Bedrock
        print("Calling AWS Bedrock...")
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0", body=json.dumps(body)
        )

        # Parse response
        response_body = json.loads(response["body"].read())

        if "content" in response_body and len(response_body["content"]) > 0:
            result = response_body["content"][0]["text"]
            print("\nClaude's Response:")
            print("=" * 60)
            print(result)
            print("=" * 60)
            print("\n✓ Success! Vision API is working correctly.")
        else:
            print(f"Unexpected response format: {response_body}")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials are configured")
        print("2. Verify Bedrock model access is enabled")
        print("3. Ensure you're using the correct AWS region")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vision.py <image_path> [prompt]")
        print("\nExample:")
        print("  python test_vision.py screenshot.png")
        print('  python test_vision.py diagram.jpg "Explain this architecture diagram"')
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "What do you see in this image? Describe it in detail."
    )

    test_vision_with_local_image(image_path, prompt)
