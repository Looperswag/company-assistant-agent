"""Query classifier for determining query type."""

from enum import Enum
from typing import List

from src.utils.logger import logger


class QueryType(Enum):
    """Query type enumeration."""

    COMPANY_INTERNAL = "company_internal"
    EXTERNAL_KNOWLEDGE = "external_knowledge"
    AMBIGUOUS = "ambiguous"
    HARMFUL = "harmful"


class QueryClassifier:
    """Classifies user queries to determine appropriate response strategy."""

    def __init__(self) -> None:
        """Initialize the classifier."""
        # Keywords that suggest company-related queries
        self.company_keywords: List[str] = [
            "company",
            "policy",
            "policies",
            "procedure",
            "procedures",
            "guideline",
            "guidelines",
            "employee",
            "employees",
            "staff",
            "recruitment",
            "hiring",
            "onboarding",
            "vacation",
            "leave",
            "holiday",
            "sick",
            "day off",
            "code",
            "coding",
            "style",
            "standard",
            "规范",
            "ZURU",
            "Melon",
            "zurumelon",
            "complaint",
            "complaints",
            "feedback",
            "report",
            "client",
            "customer",
            "internal",
            "contact",
            "email",
            "helpdesk",
            "hr",
            "投诉",
            "反馈",
            "举报",
            "客户",
            "联系",
            "邮箱",
        ]

        # Keywords that suggest external knowledge queries
        self.external_keywords: List[str] = [
            "latest",
            "news",
            "recent",
            "today",
            "current",
            "now",
            "real-time",
            "search",
            "find",
            "what is",
            "how to",
            "how do",
            "why does",
            "最新",
            "新闻",
            "今天",
            "现在",
            "当前",
            "实时",
            "搜索",
            "查找",
            "什么是",
            "如何",
            "为什么",
        ]

        # High-priority phrases that explicitly request web/internet search
        self.web_search_phrases: List[str] = [
            "from the internet",
            "on the web",
            "online",
            "web search",
            "google",
            "bing",
            "从互联网",
            "在网上",
            "网络搜索",
            "上网",
            "互联网上",
            "去网上",
            "谷歌",
            "百度",
            "在线",
            "实时",
        ]

    def classify(self, query: str) -> QueryType:
        """Classify a query.

        Args:
            query: User query string

        Returns:
            QueryType enum value
        """
        query_lower = query.lower()

        # Check for harmful content first
        if self._is_harmful(query_lower):
            return QueryType.HARMFUL

        # PRIORITY 1: Check for explicit web/internet search requests
        # These phrases indicate the user explicitly wants web search
        for phrase in self.web_search_phrases:
            if phrase.lower() in query_lower:
                logger.info(f"Detected explicit web search phrase: '{phrase}'")
                return QueryType.EXTERNAL_KNOWLEDGE

        # Check for company-related keywords
        company_score = sum(1 for keyword in self.company_keywords if keyword.lower() in query_lower)

        # Check for external knowledge keywords
        external_score = sum(
            1 for keyword in self.external_keywords if keyword.lower() in query_lower
        )

        # Determine query type
        if company_score > 0 and company_score >= external_score:
            return QueryType.COMPANY_INTERNAL
        elif external_score > 0 and external_score > company_score:
            return QueryType.EXTERNAL_KNOWLEDGE
        elif company_score == 0 and external_score == 0:
            # Ambiguous: could be either
            return QueryType.AMBIGUOUS
        else:
            # Default to company internal if there's any company keyword
            return QueryType.COMPANY_INTERNAL

    def _is_harmful(self, query: str) -> bool:
        """Check if query contains harmful content.

        Args:
            query: Query string (lowercase)

        Returns:
            True if query appears harmful
        """
        # Basic harmful keywords (can be expanded)
        harmful_keywords = [
            "attack",
            "hack",
            "hacking",
            "exploit",
            "breach",
            "malware",
            "virus",
            "damage",
            "destroy",
            "sabotage",
            "攻击",
            "破坏",
            "非法",
            "违法",
            "黑客",
            "病毒",
            "恶意",
        ]

        return any(keyword in query for keyword in harmful_keywords)
