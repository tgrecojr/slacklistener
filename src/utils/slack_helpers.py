"""Slack helper utilities."""

import logging
from typing import List, Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


def matches_keywords(
    text: str,
    keywords: List[str],
    case_sensitive: bool = False
) -> bool:
    """
    Check if text contains any of the keywords.

    Args:
        text: Text to search in
        keywords: List of keywords to search for
        case_sensitive: Whether to use case-sensitive matching

    Returns:
        True if any keyword is found, False otherwise
    """
    if not keywords:
        # Empty keywords list means match everything
        return True

    search_text = text if case_sensitive else text.lower()

    for keyword in keywords:
        search_keyword = keyword if case_sensitive else keyword.lower()
        if search_keyword in search_text:
            logger.debug(f"Matched keyword: {keyword}")
            return True

    return False


def download_slack_file(url: str, token: str) -> Optional[bytes]:
    """
    Download a file from Slack.

    Args:
        url: Slack file URL
        token: Slack bot token

    Returns:
        File bytes or None on error
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading file from Slack: {e}")
        return None


def extract_message_images(
    event: Dict[str, Any],
    client: Any,
    bot_token: str
) -> List[Dict[str, Any]]:
    """
    Extract images from a Slack message event.

    Args:
        event: Slack message event
        client: Slack client
        bot_token: Bot token for downloading files

    Returns:
        List of dicts with 'data' (bytes) and 'mimetype' (str)
    """
    images = []

    # Check for files in the message
    files = event.get("files", [])

    for file_obj in files:
        # Check if it's an image
        mimetype = file_obj.get("mimetype", "")
        if mimetype.startswith("image/"):
            # Download the file
            url = file_obj.get("url_private")
            if url:
                image_data = download_slack_file(url, bot_token)
                if image_data:
                    images.append({
                        "data": image_data,
                        "mimetype": mimetype,
                        "filename": file_obj.get("name", "image")
                    })
                    logger.debug(f"Downloaded image: {file_obj.get('name')} ({mimetype})")

    return images


def should_ignore_message(
    event: Dict[str, Any],
    bot_user_id: str,
    ignore_bots: bool = True,
    ignore_self: bool = True
) -> bool:
    """
    Determine if a message should be ignored.

    Args:
        event: Slack message event
        bot_user_id: This bot's user ID
        ignore_bots: Whether to ignore bot messages
        ignore_self: Whether to ignore own messages

    Returns:
        True if message should be ignored, False otherwise
    """
    # Check if message is from a bot
    if ignore_bots and event.get("bot_id"):
        return True

    # Check if message is from self
    user_id = event.get("user")
    if ignore_self and user_id == bot_user_id:
        return True

    # Ignore message subtypes we don't care about
    subtype = event.get("subtype")
    if subtype in ["message_changed", "message_deleted", "channel_join", "channel_leave"]:
        return True

    return False


def format_slack_text(text: str, max_length: int = 3000) -> str:
    """
    Format text for Slack, respecting length limits.

    Args:
        text: Text to format
        max_length: Maximum length

    Returns:
        Formatted text
    """
    if len(text) <= max_length:
        return text

    # Truncate and add indicator
    return text[:max_length - 50] + "\n\n... (response truncated)"
