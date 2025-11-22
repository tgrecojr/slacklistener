"""AWS Bedrock client wrapper for LLM interactions."""

import json
import logging
from typing import Optional, List, Dict, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Wrapper for AWS Bedrock API calls."""

    def __init__(self, region: str = "us-east-2", timeout: int = 30):
        """
        Initialize Bedrock client.

        Args:
            region: AWS region for Bedrock
            timeout: Timeout for API calls in seconds (not currently used)
        """
        self.region = region
        # Create client using region_name parameter directly (matching AWS SDK examples)
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def invoke_claude(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Optional[str]:
        """
        Invoke Claude model via Bedrock.

        Args:
            model_id: Bedrock model ID (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter

        Returns:
            Generated text response or None on error
        """
        try:
            # Format the request payload using the model's native structure
            # (matching AWS SDK example structure exactly)
            native_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            # Add optional parameters
            if top_p != 0.9:  # Only include if non-default
                native_request["top_p"] = top_p

            if system_prompt:
                native_request["system"] = system_prompt

            # Convert the native request to JSON (matching AWS SDK example)
            request = json.dumps(native_request)

            logger.debug(f"Invoking Bedrock model: {model_id}")

            # Invoke the model with the request (matching AWS SDK example)
            response = self.client.invoke_model(modelId=model_id, body=request)

            # Decode the response body (matching AWS SDK example)
            model_response = json.loads(response["body"].read())

            # Extract and return the response text (matching AWS SDK example)
            if "content" in model_response and len(model_response["content"]) > 0:
                response_text = model_response["content"][0]["text"]
                return response_text
            else:
                logger.error(f"Unexpected response format: {model_response}")
                return None

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {e}")
            return None

    def format_message(
        self,
        text: str,
        role: str = "user",
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Format a message for Claude API.

        Args:
            text: Message text
            role: Message role ("user" or "assistant")
            images: Optional list of image dicts with 'data' (bytes) and 'mimetype' (str)

        Returns:
            Formatted message dict
        """
        import base64

        content = []

        # Add images if provided
        if images:
            for image_info in images:
                # Extract image data and mimetype
                if isinstance(image_info, dict):
                    image_data = image_info.get("data")
                    mimetype = image_info.get("mimetype", "image/jpeg")
                else:
                    # Backwards compatibility: if just bytes are passed
                    image_data = image_info
                    mimetype = "image/jpeg"

                if image_data:
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mimetype,
                                "data": base64.b64encode(image_data).decode("utf-8"),
                            },
                        }
                    )

        # Add text
        if text:
            content.append({"type": "text", "text": text})

        return {"role": role, "content": content}

    def create_simple_message(self, text: str, role: str = "user") -> Dict[str, Any]:
        """
        Create a simple text-only message.

        Args:
            text: Message text
            role: Message role

        Returns:
            Formatted message dict
        """
        return {"role": role, "content": [{"type": "text", "text": text}]}
