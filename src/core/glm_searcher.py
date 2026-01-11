"""GLM-4 Flash native web search module."""

from typing import List, Optional

from zhipuai import ZhipuAI

from src.utils.config import config
from src.utils.logger import logger


class GLMWebSearcher:
    """Web search interface using GLM-4 Flash native web search API.

    GLM-4 Flash provides a standalone web_search API that can be called
    independently of chat completions. This is perfect for RAG systems
    where search happens before the final LLM call.
    """

    # Phrases to remove from search queries for cleaner searches
    QUERY_CLEANUP_PHRASES = [
        "从互联网上",
        "在网上",
        "从网上",
        "上网",
        "互联网上",
        "去网上",
        "用谷歌",
        "用百度",
        "网络搜索",
        "帮我搜索",
        "请搜索",
        "告诉我",
        "from the internet",
        "on the web",
        "search the web",
        "google search",
        "tell me",
    ]

    def __init__(self) -> None:
        """Initialize the GLM web searcher."""
        try:
            self.client = ZhipuAI(api_key=config.zhipuai_api_key)
            self.enabled = config.search_enabled
            self.max_results = config.max_search_results
            self.recency_filter = getattr(config, "search_recency_filter", "")
        except Exception as e:
            logger.error(f"Failed to initialize GLM web searcher: {e}")
            self.enabled = False
            self.client = None
            self.max_results = 5
            self.recency_filter = ""

    def _clean_query(self, query: str) -> str:
        """Clean up search query by removing redundant phrases.

        Args:
            query: Original query string

        Returns:
            Cleaned query string
        """
        import re

        cleaned = query
        # Remove redundant phrases
        for phrase in self.QUERY_CLEANUP_PHRASES:
            cleaned = cleaned.replace(phrase, "")
        # Remove leading/trailing punctuation and whitespace
        cleaned = re.sub(r'^[，、。！？；：,\.!?;:\s]+', "", cleaned)
        cleaned = re.sub(r'[，、。！？；：,\.!?;:\s]+$', "", cleaned)
        return cleaned.strip()

    def search(self, query: str, max_results: Optional[int] = None) -> List[dict]:
        """Search the web using GLM-4 Flash native web search API.

        Args:
            query: Search query
            max_results: Maximum number of results (overrides config)

        Returns:
            List of search results with title, snippet, url, and optional metadata
        """
        if not self.enabled or self.client is None:
            logger.warning("GLM web search is disabled")
            return []

        max_results = max_results or self.max_results

        # Clean the query for better search results
        cleaned_query = self._clean_query(query)
        if cleaned_query != query:
            logger.info(f"Cleaned query: '{query}' -> '{cleaned_query}'")

        try:
            # Build API request parameters
            request_params = {
                "search_query": cleaned_query,
                "count": max_results,
                "search_engine": "google",  # Required: specify search engine
            }

            # Add optional recency filter if configured
            if self.recency_filter:
                request_params["search_recency_filter"] = self.recency_filter

            # Call GLM web search API
            response = self.client.web_search.web_search(**request_params)

            # Format results to match current interface
            formatted_results: List[dict] = []
            if response.search_result:
                # Handle both single result and list of results
                results = (
                    response.search_result
                    if isinstance(response.search_result, list)
                    else [response.search_result]
                )
                for result in results:
                    formatted_results.append(
                        {
                            "title": result.title,
                            "snippet": result.content,
                            "url": result.link,
                            # Additional metadata from GLM
                            "media": getattr(result, "media", ""),
                            "publish_date": getattr(result, "publish_date", ""),
                            "icon": getattr(result, "icon", ""),
                            "refer": getattr(result, "refer", ""),
                        }
                    )

            logger.info(
                f"GLM search found {len(formatted_results)} results for: {cleaned_query}"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"GLM web search error: {e}")
            return []

    def format_search_results(self, results: List[dict]) -> str:
        """Format search results as a string for LLM context.

        Args:
            results: List of search result dictionaries

        Returns:
            Formatted string
        """
        if not results:
            return ""

        formatted = "Web Search Results:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result.get('title', 'No title')}\n"
            formatted += f"   {result.get('snippet', 'No description')}\n"
            formatted += f"   Source: {result.get('url', 'Unknown')}\n\n"

        return formatted
