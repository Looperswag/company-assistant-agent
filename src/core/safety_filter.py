"""Safety filter for detecting harmful or policy-violating queries."""

from typing import List, Tuple

from src.utils.logger import logger


class SafetyFilter:
    """Filters harmful, inappropriate, or policy-violating queries."""

    def __init__(self) -> None:
        """Initialize the safety filter."""
        # Harmful content keywords
        self.harmful_keywords: List[str] = [
            "attack",
            "hack",
            "hacking",
            "exploit",
            "breach",
            "malware",
            "virus",
            "phishing",
            "fraud",
            "scam",
            "damage",
            "destroy",
            "sabotage",
            "攻击",
            "破坏",
            "非法",
            "违法",
            "黑客",
            "病毒",
            "恶意软件",
            "诈骗",
            "欺诈",
        ]

        # Inappropriate content keywords
        self.inappropriate_keywords: List[str] = [
            "porn",
            "explicit",
            "violence",
            "violent",
            "discrimination",
            "hate",
            "harassment",
            "色情",
            "暴力",
            "歧视",
            "仇恨",
        ]

        # Policy violation keywords (related to company policies)
        self.policy_violation_keywords: List[str] = [
            "leak confidential",
            "steal data",
            "bypass security",
            "unauthorized access",
            "泄露机密",
            "盗取数据",
            "违反保密",
            "绕过安全",
        ]

    def check(self, query: str) -> Tuple[bool, str]:
        """Check if query should be blocked.

        Args:
            query: User query string

        Returns:
            Tuple of (is_safe, reason). is_safe=True means query is safe.
        """
        query_lower = query.lower()

        # Check for harmful content
        for keyword in self.harmful_keywords:
            if keyword in query_lower:
                logger.warning(f"Blocked harmful query: {keyword}")
                return False, f"Harmful content detected: {keyword}"

        # Check for inappropriate content
        for keyword in self.inappropriate_keywords:
            if keyword in query_lower:
                logger.warning(f"Blocked inappropriate query: {keyword}")
                return False, f"Inappropriate content detected: {keyword}"

        # Check for policy violations
        for keyword in self.policy_violation_keywords:
            if keyword in query_lower:
                logger.warning(f"Blocked policy violation query: {keyword}")
                return False, f"Policy violation detected: {keyword}"

        return True, ""

    def is_safe(self, query: str) -> bool:
        """Check if query is safe (convenience method).

        Args:
            query: User query string

        Returns:
            True if query is safe
        """
        is_safe, _ = self.check(query)
        return is_safe
