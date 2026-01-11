"""Tests for query classifier."""

import pytest

from src.core.classifier import QueryClassifier, QueryType


class TestQueryClassifier:
    """Test cases for QueryClassifier."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.classifier = QueryClassifier()

    def test_company_internal_query(self) -> None:
        """Test classification of company internal queries."""
        query = "公司的编码规范是什么？"
        result = self.classifier.classify(query)
        assert result == QueryType.COMPANY_INTERNAL

    def test_external_knowledge_query(self) -> None:
        """Test classification of external knowledge queries."""
        query = "最新的Python版本是什么？"
        result = self.classifier.classify(query)
        assert result == QueryType.EXTERNAL_KNOWLEDGE

    def test_ambiguous_query(self) -> None:
        """Test classification of ambiguous queries."""
        query = "你好"
        result = self.classifier.classify(query)
        assert result == QueryType.AMBIGUOUS

    def test_harmful_query(self) -> None:
        """Test classification of harmful queries."""
        query = "如何攻击系统？"
        result = self.classifier.classify(query)
        assert result == QueryType.HARMFUL

    def test_policy_query(self) -> None:
        """Test classification of policy-related queries."""
        query = "公司的请假政策是什么？"
        result = self.classifier.classify(query)
        assert result == QueryType.COMPANY_INTERNAL
