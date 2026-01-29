"""RSS Feed Tool for fetching and tracking news stories."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser

from ..tool import Tool

logger = logging.getLogger(__name__)


class RSSFeedTool(Tool):
    """Tool to fetch RSS feeds and track seen articles."""

    def __init__(
        self,
        feed_urls: List[str],
        data_file: str = "data/seen_articles.json",
        max_stories: int = 10,
    ):
        """
        Initialize RSS Feed tool.

        Args:
            feed_urls: List of RSS feed URLs to fetch
            data_file: Path to JSON file for storing seen article IDs
            max_stories: Maximum number of new stories to return per execution
        """
        self.feed_urls = feed_urls
        self.data_file = data_file
        self.max_stories = max_stories

    def get_name(self) -> str:
        """Get tool name."""
        return "RSSFeed"

    def execute(self, context: Dict[str, Any]) -> str:
        """
        Fetch RSS feeds and return new stories.

        Args:
            context: Execution context (not used for this tool)

        Returns:
            Formatted string with new story information for LLM summarization
        """
        try:
            # Load previously seen article IDs
            seen_ids = self._load_seen_ids()

            # Fetch all feeds and collect new stories
            new_stories = []
            new_ids = set()

            for feed_url in self.feed_urls:
                try:
                    stories, story_ids = self._fetch_feed(feed_url, seen_ids)
                    new_stories.extend(stories)
                    new_ids.update(story_ids)
                except Exception as e:
                    logger.warning(f"Error fetching feed {feed_url}: {e}")
                    continue

            if not new_stories:
                logger.info("No new stories found in RSS feeds")
                return "No new stories found in the configured RSS feeds."

            # Sort by published date (newest first) and limit
            new_stories.sort(key=lambda x: x.get("published", ""), reverse=True)
            limited_stories = new_stories[: self.max_stories]

            # Mark these stories as seen
            all_seen = seen_ids.union(new_ids)
            self._save_seen_ids(all_seen)

            # Format for LLM
            result = self._format_stories(limited_stories)

            logger.info(
                f"Found {len(new_stories)} new stories, returning {len(limited_stories)}"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing RSS feeds: {e}", exc_info=True)
            return f"Error: Could not fetch RSS feeds - {str(e)}"

    def _load_seen_ids(self) -> set:
        """Load previously seen article IDs from storage."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("seen_ids", []))
        except Exception as e:
            logger.warning(f"Could not load seen IDs from {self.data_file}: {e}")
        return set()

    def _save_seen_ids(self, seen_ids: set) -> None:
        """Save seen article IDs to storage."""
        try:
            # Ensure directory exists
            Path(self.data_file).parent.mkdir(parents=True, exist_ok=True)

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "seen_ids": list(seen_ids),
                        "last_updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Could not save seen IDs to {self.data_file}: {e}")

    def _fetch_feed(
        self, feed_url: str, seen_ids: set
    ) -> tuple[List[Dict[str, Any]], set]:
        """
        Fetch a single RSS feed and extract new stories.

        Args:
            feed_url: URL of the RSS feed
            seen_ids: Set of previously seen article IDs

        Returns:
            Tuple of (list of new story dicts, set of new story IDs)
        """
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            raise ValueError(f"Failed to parse feed: {feed.bozo_exception}")

        new_stories = []
        new_ids = set()

        for entry in feed.entries:
            # Generate unique ID for article
            article_id = self._get_article_id(entry)

            if article_id in seen_ids:
                continue

            story = {
                "id": article_id,
                "title": getattr(entry, "title", "Untitled"),
                "link": getattr(entry, "link", ""),
                "summary": self._clean_summary(getattr(entry, "summary", "")),
                "published": self._get_published_date(entry),
                "source": feed.feed.get("title", feed_url),
            }

            new_stories.append(story)
            new_ids.add(article_id)

        return new_stories, new_ids

    def _get_article_id(self, entry: Any) -> str:
        """Generate a unique ID for an article entry."""
        # Prefer explicit ID, then link, then title hash
        if entry.get("id"):
            return entry.id
        if entry.get("link"):
            return entry.link
        return str(hash(entry.get("title", "")))

    def _get_published_date(self, entry: Any) -> str:
        """Extract published date from entry."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6]).isoformat()
            except (TypeError, ValueError):
                pass
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6]).isoformat()
            except (TypeError, ValueError):
                pass
        return ""

    def _clean_summary(self, summary: str) -> str:
        """Clean up summary text by removing HTML tags."""
        import re

        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", summary)
        # Normalize whitespace
        clean = " ".join(clean.split())
        # Truncate if too long
        if len(clean) > 500:
            clean = clean[:497] + "..."
        return clean

    def _format_stories(self, stories: List[Dict[str, Any]]) -> str:
        """Format stories for LLM consumption."""
        result = f"NEW STORIES ({len(stories)} articles):\n\n"

        for i, story in enumerate(stories, 1):
            result += f"[{i}] {story['title']}\n"
            result += f"    Source: {story['source']}\n"
            if story["published"]:
                result += f"    Published: {story['published']}\n"
            if story["summary"]:
                result += f"    Summary: {story['summary']}\n"
            result += f"    Link: {story['link']}\n\n"

        return result
