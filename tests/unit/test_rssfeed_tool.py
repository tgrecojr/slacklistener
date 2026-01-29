"""Tests for RSS Feed tool and factory integration."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.tools.factory import create_tool
from src.tools.implementations.rssfeed import RSSFeedTool


class TestRSSFeedTool:
    """Tests for RSSFeedTool."""

    def test_initialization_with_defaults(self):
        """Test tool initialization with default values."""
        tool = RSSFeedTool(feed_urls=["https://example.com/feed.xml"])

        assert tool.feed_urls == ["https://example.com/feed.xml"]
        assert tool.data_file == "data/seen_articles.json"
        assert tool.max_stories == 10
        assert tool.get_name() == "RSSFeed"

    def test_initialization_with_custom_values(self):
        """Test tool initialization with custom values."""
        tool = RSSFeedTool(
            feed_urls=["https://feed1.com/rss", "https://feed2.com/rss"],
            data_file="custom/path/seen.json",
            max_stories=5,
        )

        assert len(tool.feed_urls) == 2
        assert tool.data_file == "custom/path/seen.json"
        assert tool.max_stories == 5

    @patch("src.tools.implementations.rssfeed.feedparser.parse")
    def test_execute_with_new_stories(self, mock_parse):
        """Test execution when new stories are found."""
        # Mock feed response
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Test Feed"
        mock_feed.entries = [
            MagicMock(
                id="article-1",
                title="Test Article 1",
                link="https://example.com/article1",
                summary="<p>Summary of article 1</p>",
                published_parsed=(2024, 1, 15, 10, 30, 0, 0, 0, 0),
            ),
            MagicMock(
                id="article-2",
                title="Test Article 2",
                link="https://example.com/article2",
                summary="Summary of article 2",
                published_parsed=(2024, 1, 14, 9, 0, 0, 0, 0, 0),
            ),
        ]
        mock_parse.return_value = mock_feed

        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "seen.json")
            tool = RSSFeedTool(
                feed_urls=["https://example.com/feed.xml"],
                data_file=data_file,
                max_stories=10,
            )

            context = {"user_input": "get news"}
            result = tool.execute(context)

            # Verify result contains story info
            assert "NEW STORIES" in result
            assert "Test Article 1" in result
            assert "Test Article 2" in result
            assert "Test Feed" in result

            # Verify seen IDs were saved
            assert os.path.exists(data_file)
            with open(data_file, "r") as f:
                data = json.load(f)
                assert "article-1" in data["seen_ids"]
                assert "article-2" in data["seen_ids"]

    @patch("src.tools.implementations.rssfeed.feedparser.parse")
    def test_execute_filters_seen_stories(self, mock_parse):
        """Test that previously seen stories are filtered out."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Test Feed"
        mock_feed.entries = [
            MagicMock(
                id="article-1",
                title="Already Seen",
                link="https://example.com/article1",
                summary="Old article",
                published_parsed=None,
            ),
            MagicMock(
                id="article-new",
                title="New Article",
                link="https://example.com/new",
                summary="Fresh content",
                published_parsed=None,
            ),
        ]
        mock_parse.return_value = mock_feed

        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "seen.json")

            # Pre-populate with seen article
            with open(data_file, "w") as f:
                json.dump({"seen_ids": ["article-1"]}, f)

            tool = RSSFeedTool(
                feed_urls=["https://example.com/feed.xml"],
                data_file=data_file,
            )

            result = tool.execute({})

            assert "New Article" in result
            assert "Already Seen" not in result

    @patch("src.tools.implementations.rssfeed.feedparser.parse")
    def test_execute_respects_max_stories(self, mock_parse):
        """Test that max_stories limit is respected."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Test Feed"
        mock_feed.entries = [
            MagicMock(
                id=f"article-{i}",
                title=f"Article {i}",
                link=f"https://example.com/article{i}",
                summary=f"Summary {i}",
                published_parsed=(2024, 1, i + 1, 10, 0, 0, 0, 0, 0),
            )
            for i in range(5)
        ]
        mock_parse.return_value = mock_feed

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RSSFeedTool(
                feed_urls=["https://example.com/feed.xml"],
                data_file=os.path.join(tmpdir, "seen.json"),
                max_stories=2,
            )

            result = tool.execute({})

            # Should only have 2 articles in the output
            assert result.count("[") == 2

    @patch("src.tools.implementations.rssfeed.feedparser.parse")
    def test_execute_handles_empty_feed(self, mock_parse):
        """Test handling of empty feeds."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Empty Feed"
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RSSFeedTool(
                feed_urls=["https://example.com/empty.xml"],
                data_file=os.path.join(tmpdir, "seen.json"),
            )

            result = tool.execute({})

            assert "No new stories found" in result

    @patch("src.tools.implementations.rssfeed.feedparser.parse")
    def test_execute_handles_feed_error(self, mock_parse):
        """Test handling of feed parsing errors."""
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RSSFeedTool(
                feed_urls=["https://example.com/bad.xml"],
                data_file=os.path.join(tmpdir, "seen.json"),
            )

            result = tool.execute({})

            # Should return no stories message (feed error is logged)
            assert "No new stories found" in result

    @patch("src.tools.implementations.rssfeed.feedparser.parse")
    def test_execute_multiple_feeds(self, mock_parse):
        """Test fetching from multiple feeds."""
        feed1 = MagicMock()
        feed1.bozo = False
        feed1.feed.get.return_value = "Feed 1"
        feed1.entries = [
            MagicMock(
                id="feed1-article",
                title="From Feed 1",
                link="https://feed1.com/article",
                summary="Content from feed 1",
                published_parsed=None,
            )
        ]

        feed2 = MagicMock()
        feed2.bozo = False
        feed2.feed.get.return_value = "Feed 2"
        feed2.entries = [
            MagicMock(
                id="feed2-article",
                title="From Feed 2",
                link="https://feed2.com/article",
                summary="Content from feed 2",
                published_parsed=None,
            )
        ]

        mock_parse.side_effect = [feed1, feed2]

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RSSFeedTool(
                feed_urls=["https://feed1.com/rss", "https://feed2.com/rss"],
                data_file=os.path.join(tmpdir, "seen.json"),
            )

            result = tool.execute({})

            assert "From Feed 1" in result
            assert "From Feed 2" in result
            assert "Feed 1" in result
            assert "Feed 2" in result

    def test_persistence_across_executions(self):
        """Test that seen IDs persist across tool executions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, "seen.json")

            # First execution
            with patch(
                "src.tools.implementations.rssfeed.feedparser.parse"
            ) as mock_parse:
                mock_feed = MagicMock()
                mock_feed.bozo = False
                mock_feed.feed.get.return_value = "Test Feed"
                mock_feed.entries = [
                    MagicMock(
                        id="article-1",
                        title="First Article",
                        link="https://example.com/1",
                        summary="First",
                        published_parsed=None,
                    )
                ]
                mock_parse.return_value = mock_feed

                tool1 = RSSFeedTool(
                    feed_urls=["https://example.com/feed.xml"],
                    data_file=data_file,
                )
                result1 = tool1.execute({})
                assert "First Article" in result1

            # Second execution with new tool instance
            with patch(
                "src.tools.implementations.rssfeed.feedparser.parse"
            ) as mock_parse:
                mock_feed = MagicMock()
                mock_feed.bozo = False
                mock_feed.feed.get.return_value = "Test Feed"
                mock_feed.entries = [
                    MagicMock(
                        id="article-1",
                        title="First Article",
                        link="https://example.com/1",
                        summary="First",
                        published_parsed=None,
                    ),
                    MagicMock(
                        id="article-2",
                        title="Second Article",
                        link="https://example.com/2",
                        summary="Second",
                        published_parsed=None,
                    ),
                ]
                mock_parse.return_value = mock_feed

                tool2 = RSSFeedTool(
                    feed_urls=["https://example.com/feed.xml"],
                    data_file=data_file,
                )
                result2 = tool2.execute({})

                # First article should not appear (already seen)
                assert "First Article" not in result2
                assert "Second Article" in result2

    def test_clean_summary_removes_html(self):
        """Test that HTML tags are removed from summaries."""
        tool = RSSFeedTool(feed_urls=["https://example.com/feed.xml"])

        html_summary = "<p>This is a <b>test</b> with <a href='#'>links</a>.</p>"
        clean = tool._clean_summary(html_summary)

        assert "<" not in clean
        assert ">" not in clean
        assert "This is a test with links." in clean

    def test_clean_summary_truncates_long_text(self):
        """Test that long summaries are truncated."""
        tool = RSSFeedTool(feed_urls=["https://example.com/feed.xml"])

        long_summary = "x" * 600
        clean = tool._clean_summary(long_summary)

        assert len(clean) <= 500
        assert clean.endswith("...")


class TestRSSFeedToolFactory:
    """Tests for RSSFeed tool factory integration."""

    def test_create_rssfeed_tool_with_required_params(self):
        """Test creating RSSFeed tool with required parameters."""
        config = {
            "type": "rssfeed",
            "feed_urls": ["https://example.com/feed.xml"],
        }

        tool = create_tool(config)

        assert isinstance(tool, RSSFeedTool)
        assert tool.feed_urls == ["https://example.com/feed.xml"]
        assert tool.data_file == "data/seen_articles.json"  # default
        assert tool.max_stories == 10  # default

    def test_create_rssfeed_tool_with_all_params(self):
        """Test creating RSSFeed tool with all parameters."""
        config = {
            "type": "rssfeed",
            "feed_urls": ["https://feed1.com/rss", "https://feed2.com/rss"],
            "data_file": "custom/seen.json",
            "max_stories": 5,
        }

        tool = create_tool(config)

        assert isinstance(tool, RSSFeedTool)
        assert len(tool.feed_urls) == 2
        assert tool.data_file == "custom/seen.json"
        assert tool.max_stories == 5

    def test_create_rssfeed_tool_missing_feed_urls(self):
        """Test error when feed_urls is missing."""
        config = {"type": "rssfeed"}

        with pytest.raises(ValueError, match="requires 'feed_urls'"):
            create_tool(config)

    def test_create_rssfeed_tool_empty_feed_urls(self):
        """Test error when feed_urls is empty."""
        config = {"type": "rssfeed", "feed_urls": []}

        with pytest.raises(ValueError, match="at least one URL"):
            create_tool(config)

    def test_create_rssfeed_tool_invalid_feed_urls_type(self):
        """Test error when feed_urls is not a list."""
        config = {"type": "rssfeed", "feed_urls": "https://example.com/feed.xml"}

        with pytest.raises(ValueError, match="requires 'feed_urls'"):
            create_tool(config)
