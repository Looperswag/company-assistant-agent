"""Web search module for external knowledge queries.

Supports GLM-4 Flash native web search API and DuckDuckGo fallback.
"""

from typing import List, Optional

from src.utils.config import config
from src.utils.logger import logger


class WebSearcher:
    """Web search interface with GLM-4 Flash primary and DuckDuckGo fallback.

    GLM-4 Flash provides superior search quality for Chinese content with
    advanced semantic understanding compared to traditional search engines.
    DuckDuckGo serves as a free fallback option.
    """

    def __init__(self) -> None:
        """Initialize the web searcher with GLM backend and DuckDuckGo fallback."""
        self.glm_searcher = None
        self.ddg_searcher = None
        self.provider = config.search_provider
        self.fallback_enabled = getattr(config, "search_fallback_enabled", True)

        # Initialize GLM searcher
        if self.provider in ("glm", "auto"):
            try:
                from src.core.glm_searcher import GLMWebSearcher
                self.glm_searcher = GLMWebSearcher()
                if self.glm_searcher.enabled:
                    logger.info("Web search provider: GLM-4 Flash native search")
                else:
                    self.glm_searcher = None
            except ImportError as e:
                logger.warning(f"Failed to initialize GLM web searcher: {e}")

        # Initialize DuckDuckGo searcher as fallback
        if self.provider in ("duckduckgo", "auto") or self.fallback_enabled:
            try:
                from duckduckgo_search import DDGS
                self.ddg_searcher = DDGS()
                logger.info("DuckDuckGo search initialized as fallback")
            except ImportError:
                logger.warning("DuckDuckGo search not available. Install with: pip install duckduckgo-search")
            except Exception as e:
                logger.warning(f"Failed to initialize DuckDuckGo searcher: {e}")

        self.enabled = (self.glm_searcher is not None) or (self.ddg_searcher is not None)

    def search(self, query: str, max_results: Optional[int] = None) -> List[dict]:
        """Search the web using GLM-4 Flash or DuckDuckGo fallback.

        Args:
            query: Search query
            max_results: Maximum number of results (overrides config)

        Returns:
            List of search results with title, snippet, url, and optional metadata
        """
        if not self.enabled:
            logger.warning("Web search is disabled")
            return []

        max_results = max_results or config.max_search_results

        # Try GLM search first
        if self.glm_searcher and self.provider in ("glm", "auto"):
            try:
                results = self.glm_searcher.search(query, max_results)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"GLM search failed: {e}")

        # Fall back to DuckDuckGo
        if self.ddg_searcher:
            try:
                return self._search_duckduckgo(query, max_results)
            except Exception as e:
                logger.error(f"DuckDuckGo search failed: {e}")

        return []

    def _search_duckduckgo(self, query: str, max_results: int) -> List[dict]:
        """Search using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        results = []
        search_results = list(self.ddg_searcher.text(query, max_results=max_results))

        for result in search_results:
            results.append({
                "title": result.get("title", ""),
                "snippet": result.get("body", ""),
                "url": result.get("link", ""),
            })

        logger.info(f"DuckDuckGo search found {len(results)} results")
        return results

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
