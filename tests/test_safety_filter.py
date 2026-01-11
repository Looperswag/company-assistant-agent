"""Tests for safety filter."""

import pytest

from src.core.safety_filter import SafetyFilter


class TestSafetyFilter:
    """Test cases for SafetyFilter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.filter = SafetyFilter()

    def test_safe_query(self) -> None:
        """Test that safe queries pass the filter."""
        query = "公司的编码规范是什么？"
        is_safe, reason = self.filter.check(query)
        assert is_safe is True
        assert reason == ""

    def test_harmful_query(self) -> None:
        """Test that harmful queries are blocked."""
        query = "如何攻击系统？"
        is_safe, reason = self.filter.check(query)
        assert is_safe is False
        assert "有害" in reason or "攻击" in reason

    def test_inappropriate_query(self) -> None:
        """Test that inappropriate queries are blocked."""
        query = "色情内容"
        is_safe, reason = self.filter.check(query)
        assert is_safe is False

    def test_policy_violation_query(self) -> None:
        """Test that policy violation queries are blocked."""
        query = "如何泄露机密信息？"
        is_safe, reason = self.filter.check(query)
        assert is_safe is False

    def test_is_safe_method(self) -> None:
        """Test the convenience is_safe method."""
        assert self.filter.is_safe("正常问题") is True
        assert self.filter.is_safe("攻击系统") is False
