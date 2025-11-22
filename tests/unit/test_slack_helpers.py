"""Tests for Slack helper utilities."""

from unittest.mock import Mock, patch

import pytest
import responses

from src.utils.slack_helpers import (
    matches_keywords,
    download_slack_file,
    extract_message_images,
    should_ignore_message,
    format_slack_text,
)


class TestKeywordMatching:
    """Tests for keyword matching."""

    def test_matches_keywords_simple(self):
        """Test simple keyword matching."""
        assert matches_keywords("I need help", ["help"]) is True
        assert matches_keywords("This has an issue", ["issue"]) is True
        assert matches_keywords("Random text", ["help", "issue"]) is False

    def test_matches_keywords_case_insensitive(self):
        """Test case-insensitive matching (default)."""
        assert matches_keywords("HELP ME", ["help"]) is True
        assert matches_keywords("Help me", ["HELP"]) is True
        assert matches_keywords("HeLp", ["help"]) is True

    def test_matches_keywords_case_sensitive(self):
        """Test case-sensitive matching."""
        assert matches_keywords("Help", ["help"], case_sensitive=True) is False
        assert matches_keywords("help", ["help"], case_sensitive=True) is True
        assert matches_keywords("HELP", ["help"], case_sensitive=True) is False

    def test_matches_keywords_empty_list(self):
        """Test that empty keyword list matches everything."""
        assert matches_keywords("Any text", []) is True
        assert matches_keywords("", []) is True

    def test_matches_keywords_partial_match(self):
        """Test that keywords match as substrings."""
        assert matches_keywords("I have a problem", ["problem"]) is True
        assert matches_keywords("troubleshooting", ["trouble"]) is True


class TestSlackFileDownload:
    """Tests for Slack file download."""

    @responses.activate
    def test_download_slack_file_success(self, sample_image_bytes):
        """Test successful file download."""
        url = "https://files.slack.com/files-pri/T12345/test.png"
        responses.add(responses.GET, url, body=sample_image_bytes, status=200)

        result = download_slack_file(url, "xoxb-test-token")

        assert result == sample_image_bytes
        assert len(responses.calls) == 1
        assert (
            responses.calls[0].request.headers["Authorization"]
            == "Bearer xoxb-test-token"
        )

    @responses.activate
    def test_download_slack_file_error(self):
        """Test file download error handling."""
        url = "https://files.slack.com/files-pri/T12345/test.png"
        responses.add(responses.GET, url, status=404)

        result = download_slack_file(url, "xoxb-test-token")

        assert result is None

    @responses.activate
    def test_download_slack_file_timeout(self):
        """Test file download timeout handling."""
        url = "https://files.slack.com/files-pri/T12345/test.png"
        responses.add(responses.GET, url, body=Exception("Timeout"))

        result = download_slack_file(url, "xoxb-test-token")

        assert result is None


class TestExtractMessageImages:
    """Tests for image extraction from Slack messages."""

    @responses.activate
    def test_extract_message_images_success(
        self, sample_slack_image_event, sample_image_bytes
    ):
        """Test successful image extraction."""
        # Mock file download
        url = sample_slack_image_event["files"][0]["url_private"]
        responses.add(responses.GET, url, body=sample_image_bytes, status=200)

        images = extract_message_images(
            sample_slack_image_event, Mock(), "xoxb-test-token"
        )

        assert len(images) == 1
        assert images[0]["data"] == sample_image_bytes
        assert images[0]["mimetype"] == "image/png"
        assert images[0]["filename"] == "screenshot.png"

    def test_extract_message_images_no_files(self, sample_slack_message_event):
        """Test message with no files."""
        images = extract_message_images(
            sample_slack_message_event, Mock(), "xoxb-test-token"
        )

        assert len(images) == 0

    def test_extract_message_images_non_image_files(self):
        """Test message with non-image files."""
        event = {
            "type": "message",
            "files": [
                {
                    "mimetype": "application/pdf",
                    "url_private": "https://example.com/doc.pdf",
                },
                {
                    "mimetype": "text/plain",
                    "url_private": "https://example.com/text.txt",
                },
            ],
        }

        images = extract_message_images(event, Mock(), "xoxb-test-token")

        assert len(images) == 0

    @responses.activate
    def test_extract_message_images_multiple_formats(self, sample_image_bytes):
        """Test extracting multiple images with different formats."""
        event = {
            "type": "message",
            "files": [
                {
                    "mimetype": "image/png",
                    "url_private": "https://files.slack.com/test1.png",
                    "name": "image1.png",
                },
                {
                    "mimetype": "image/jpeg",
                    "url_private": "https://files.slack.com/test2.jpg",
                    "name": "image2.jpg",
                },
                {
                    "mimetype": "image/webp",
                    "url_private": "https://files.slack.com/test3.webp",
                    "name": "image3.webp",
                },
            ],
        }

        # Mock all downloads
        for file in event["files"]:
            responses.add(
                responses.GET, file["url_private"], body=sample_image_bytes, status=200
            )

        images = extract_message_images(event, Mock(), "xoxb-test-token")

        assert len(images) == 3
        assert images[0]["mimetype"] == "image/png"
        assert images[1]["mimetype"] == "image/jpeg"
        assert images[2]["mimetype"] == "image/webp"

    @responses.activate
    def test_extract_message_images_partial_failure(self, sample_image_bytes):
        """Test when some images fail to download."""
        event = {
            "type": "message",
            "files": [
                {
                    "mimetype": "image/png",
                    "url_private": "https://files.slack.com/good.png",
                    "name": "good.png",
                },
                {
                    "mimetype": "image/jpeg",
                    "url_private": "https://files.slack.com/bad.jpg",
                    "name": "bad.jpg",
                },
            ],
        }

        # First succeeds, second fails
        responses.add(
            responses.GET,
            event["files"][0]["url_private"],
            body=sample_image_bytes,
            status=200,
        )
        responses.add(responses.GET, event["files"][1]["url_private"], status=404)

        images = extract_message_images(event, Mock(), "xoxb-test-token")

        # Should only get the successful one
        assert len(images) == 1
        assert images[0]["filename"] == "good.png"


class TestShouldIgnoreMessage:
    """Tests for message filtering."""

    def test_should_ignore_bot_messages(self):
        """Test ignoring bot messages."""
        event = {"user": "U12345", "bot_id": "B12345"}

        assert should_ignore_message(event, "U99999", ignore_bots=True) is True
        assert should_ignore_message(event, "U99999", ignore_bots=False) is False

    def test_should_ignore_self_messages(self):
        """Test ignoring own messages."""
        event = {"user": "U12345"}

        assert should_ignore_message(event, "U12345", ignore_self=True) is True
        assert should_ignore_message(event, "U12345", ignore_self=False) is False
        assert should_ignore_message(event, "U99999", ignore_self=True) is False

    def test_should_ignore_system_subtypes(self):
        """Test ignoring system message subtypes."""
        subtypes = [
            "message_changed",
            "message_deleted",
            "channel_join",
            "channel_leave",
        ]

        for subtype in subtypes:
            event = {"user": "U12345", "subtype": subtype}
            assert should_ignore_message(event, "U99999") is True

    def test_should_not_ignore_normal_message(self):
        """Test not ignoring normal messages."""
        event = {"user": "U12345", "text": "Hello"}

        assert should_ignore_message(event, "U99999") is False


class TestFormatSlackText:
    """Tests for Slack text formatting."""

    def test_format_slack_text_short(self):
        """Test formatting short text."""
        text = "Short message"
        assert format_slack_text(text) == text

    def test_format_slack_text_long(self):
        """Test truncating long text."""
        text = "A" * 5000
        formatted = format_slack_text(text, max_length=1000)

        assert len(formatted) <= 1000
        assert "truncated" in formatted

    def test_format_slack_text_exact_limit(self):
        """Test text at exact limit."""
        text = "A" * 3000
        formatted = format_slack_text(text, max_length=3000)

        assert formatted == text
        assert "truncated" not in formatted
