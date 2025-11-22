"""AWS Bedrock LLM provider implementation."""

import json
import logging
from typing import List, Dict, Any, Optional

from ..provider import LLMProvider

logger = logging.getLogger(__name__)


class BedrockProvider(LLMProvider):
    """AWS Bedrock LLM provider."""

    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize Bedrock provider.

        Args:
            region: AWS region for Bedrock
            model_id: Bedrock model ID
            aws_access_key_id: Optional AWS access key (uses default credentials if not provided)
            aws_secret_access_key: Optional AWS secret key
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError(
                "boto3 is required for BedrockProvider. "
                "Install it with: pip install boto3"
            )

        self.region = region
        self.model_id = model_id
        self.ClientError = ClientError

        # Create Bedrock client
        client_kwargs = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.client = boto3.client("bedrock-runtime", **client_kwargs)
        logger.info(f"Initialized Bedrock provider with model {model_id} in {region}")

    def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate a response using AWS Bedrock.

        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text response or None on error
        """
        try:
            # Format the request payload using the model's native structure
            native_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                native_request["system"] = system_prompt

            # Convert the native request to JSON
            request = json.dumps(native_request)

            logger.debug(f"Invoking Bedrock model: {self.model_id}")

            # Invoke the model with the request
            response = self.client.invoke_model(modelId=self.model_id, body=request)

            # Decode the response body
            model_response = json.loads(response["body"].read())

            # Extract and return the response text
            if "content" in model_response and len(model_response["content"]) > 0:
                response_text = model_response["content"][0]["text"]
                return response_text
            else:
                logger.error(f"Unexpected response format: {model_response}")
                return None

        except self.ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {e}", exc_info=True)
            return None
