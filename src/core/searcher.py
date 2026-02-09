"""Web search module for external knowledge queries.

Supports GLM-4 Flash native web search API and DuckDuckGo fallback with:
- Intelligent provider routing based on query language and type
- Result caching with TTL
- Quality scoring and filtering
- Automatic fallback with retry logic
"""

import hashlib
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from src.core.language_detector import Language, get_detector
from src.utils.config import config
from src.utils.logger import logger


# Simple in-memory cache for search results
_search_cache: dict = {}


class WebSearcher:
    """Web search interface with intelligent provider routing and caching.

    Features:
    - Language-aware routing (Chinese -> GLM, English -> DDG/GLM)
    - Result caching with configurable TTL
    - Quality scoring based on relevance, source, and freshness
    - Automatic fallback on failure
    - Result deduplication across providers
    """

    # Quality scoring weights
    QUALITY_WEIGHTS = {
        "relevance": 0.5,
        "source": 0.3,
        "freshness": 0.2,
    }

    # Trusted domains for quality scoring
    TRUSTED_DOMAINS = {
        "wikipedia.org", "github.com", "stackoverflow.com", "medium.com",
        "dev.to", "reddit.com", "zhihu.com", "csdn.net", "juejin.cn",
        "bilibili.com", "docs.python.org", "developer.mozilla.org",
        "w3schools.com", "azure.microsoft.com", "cloud.google.com",
        "aws.amazon.com", "docs.oracle.com", "openai.com"
    }

    def __init__(self) -> None:
        """Initialize the web searcher."""
        self.glm_searcher = None
        self.ddg_searcher = None
        self.language_detector = get_detector()
        self.provider = config.search_provider
        self.strategy = config.search_strategy
        self.fallback_enabled = config.search_fallback_enabled
        self.cache_enabled = config.search_cache_enabled
        self.cache_ttl = config.search_cache_ttl
        self.quality_threshold = config.search_quality_threshold

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

    def _get_cache_key(self, query: str, provider: str) -> str:
        """Generate cache key for query and provider.

        Args:
            query: Search query
            provider: Provider name

        Returns:
            MD5 hash cache key
        """
        key = f"{provider}:{query.lower().strip()}"
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cached_results(self, cache_key: str) -> Optional[List[dict]]:
        """Get cached results if available and not expired.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached results or None if expired/missing
        """
        if not self.cache_enabled:
            return None

        if cache_key in _search_cache:
            cached = _search_cache[cache_key]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                logger.info(f"Cache hit for query (age: {int(time.time() - cached['timestamp'])}s)")
                return cached["results"]
            else:
                # Expired - remove from cache
                del _search_cache[cache_key]

        return None

    def _cache_results(self, cache_key: str, results: List[dict]) -> None:
        """Cache search results with timestamp.

        Args:
            cache_key: Cache key to store under
            results: Results to cache
        """
        if not self.cache_enabled:
            return

        _search_cache[cache_key] = {
            "results": results,
            "timestamp": time.time()
        }

        # Clean up old cache entries periodically
        if len(_search_cache) > 1000:
            self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """Remove expired entries from cache."""
        now = time.time()
        expired_keys = [
            k for k, v in _search_cache.items()
            if now - v["timestamp"] >= self.cache_ttl
        ]
        for key in expired_keys:
            del _search_cache[key]
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _select_provider(self, query: str) -> str:
        """Select search provider based on query analysis.

        Args:
            query: Search query

        Returns:
            Provider name: "glm" or "ddg"
        """
        # Use configured strategy if not auto
        if self.strategy == "glm_first":
            return "glm"
        elif self.strategy == "ddg_first":
            return "ddg"
        elif self.strategy == "glm_only":
            return "glm"
        elif self.strategy == "ddg_only":
            return "ddg"

        # Auto strategy: analyze query
        language = self.language_detector.detect(query)

        # Chinese queries prioritize GLM (better semantic understanding)
        if language == Language.CHINESE:
            return "glm"

        # English queries: try DDG first for factual queries (faster, free)
        # For complex/nuanced queries, use GLM
        word_count = len(query.split())
        if word_count > 10 or "?" in query:
            # Complex question - use GLM for better understanding
            return "glm"

        # Default to DDG for simple English factual queries
        return "ddg"

    def _calculate_quality_score(self, result: dict, query: str) -> float:
        """Calculate quality score for a search result.

        Args:
            result: Search result dictionary
            query: Original query for relevance check

        Returns:
            Quality score between 0 and 1
        """
        score = 0.0

        # 1. Relevance score (keyword overlap)
        snippet = result.get("snippet", "").lower()
        title = result.get("title", "").lower()
        query_words = set(query.lower().split())

        relevance = 0.0
        if query_words:
            matches = sum(1 for word in query_words if word in snippet or word in title)
            relevance = min(matches / len(query_words), 1.0)

        score += relevance * self.QUALITY_WEIGHTS["relevance"]

        # 2. Source score (trusted domains)
        url = result.get("url", "")
        source_score = 0.0
        for domain in self.TRUSTED_DOMAINS:
            if domain in url:
                source_score = 0.8
                break

        # Penalize low-quality indicators
        if any(x in url for x in ["spam", "ad", "click", "popup"]):
            source_score = min(source_score, 0.2)

        score += source_score * self.QUALITY_WEIGHTS["source"]

        # 3. Freshness score (if publish date available)
        publish_date = result.get("publish_date", "")
        freshness = 0.5  # Default for unknown date
        if publish_date:
            try:
                # Parse common date formats
                if "天前" in publish_date:
                    days = int(re.search(r'(\d+)', publish_date).group(1))
                    freshness = max(0, 1 - days / 365)
                elif "hour" in publish_date or "小时" in publish_date:
                    freshness = 1.0
            except (ValueError, AttributeError):
                pass

        score += freshness * self.QUALITY_WEIGHTS["freshness"]

        return score

    def _deduplicate_results(self, results: List[List[dict]]) -> List[dict]:
        """Deduplicate results across multiple providers.

        Args:
            results: List of result lists from different providers

        Returns:
            Deduplicated and merged results
        """
        seen_urls = set()
        unique_results = []

        for result_list in results:
            for result in result_list:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
                elif not url:
                    # Results without URL are kept (e.g., direct answers)
                    unique_results.append(result)

        return unique_results

    def _rerank_by_quality(self, results: List[dict], query: str) -> List[dict]:
        """Re-rank results by quality score.

        Args:
            results: List of search results
            query: Original query for relevance scoring

        Returns:
            Re-ranked results
        """
        for result in results:
            quality_score = self._calculate_quality_score(result, query)
            result["quality_score"] = quality_score

        # Filter by quality threshold
        filtered = [r for r in results if r.get("quality_score", 0) >= self.quality_threshold]

        # Sort by quality score
        filtered.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        if len(filtered) < len(results):
            logger.info(f"Filtered {len(results) - len(filtered)} low-quality results")

        return filtered

    def search(self, query: str, max_results: Optional[int] = None) -> List[dict]:
        """Search the web using intelligent provider routing.

        Args:
            query: Search query
            max_results: Maximum number of results (overrides config)

        Returns:
            List of search results with quality scores
        """
        if not self.enabled:
            logger.warning("Web search is disabled")
            return []

        max_results = max_results or config.max_search_results

        # Select provider based on query
        primary_provider = self._select_provider(query)
        logger.info(f"Selected search provider: {primary_provider}")

        # Check cache
        cache_key = self._get_cache_key(query, primary_provider)
        cached_results = self._get_cached_results(cache_key)
        if cached_results:
            return cached_results[:max_results]

        # Try primary provider
        all_results = []
        provider_tried = False

        if primary_provider == "glm" and self.glm_searcher:
            try:
                results = self.glm_searcher.search(query, max_results)
                if results:
                    for r in results:
                        r["provider"] = "glm"
                    all_results.append(results)
                provider_tried = True
            except Exception as e:
                logger.warning(f"GLM search failed: {e}")

        elif primary_provider == "ddg" and self.ddg_searcher:
            try:
                results = self._search_duckduckgo(query, max_results)
                if results:
                    for r in results:
                        r["provider"] = "ddg"
                    all_results.append(results)
                provider_tried = True
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")

        # Fallback to other provider if enabled and primary failed
        if (not all_results or not all_results[0]) and self.fallback_enabled:
            logger.info("Primary provider failed, trying fallback")
            if primary_provider == "ddg" and self.glm_searcher:
                try:
                    results = self.glm_searcher.search(query, max_results)
                    if results:
                        for r in results:
                            r["provider"] = "glm"
                        all_results.append(results)
                except Exception as e:
                    logger.warning(f"GLM fallback failed: {e}")
            elif primary_provider == "glm" and self.ddg_searcher:
                try:
                    results = self._search_duckduckgo(query, max_results)
                    if results:
                        for r in results:
                            r["provider"] = "ddg"
                        all_results.append(results)
                except Exception as e:
                    logger.warning(f"DuckDuckGo fallback failed: {e}")

        # Merge and deduplicate results
        if all_results:
            merged = self._deduplicate_results(all_results)
            # Re-rank by quality
            final_results = self._rerank_by_quality(merged, query)
            # Cache results
            self._cache_results(cache_key, final_results)
            return final_results[:max_results]

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
            quality = result.get("quality_score", 0)
            provider = result.get("provider", "unknown")
            formatted += f"{i}. {result.get('title', 'No title')}\n"
            formatted += f"   {result.get('snippet', 'No description')}\n"
            formatted += f"   Source: {result.get('url', 'Unknown')}\n"
            if quality > 0:
                formatted += f"   Quality: {quality:.2f} | Provider: {provider}\n"
            formatted += "\n"

        return formatted
