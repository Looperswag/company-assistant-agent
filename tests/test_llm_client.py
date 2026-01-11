"""Tests for LLM client."""

import pytest
from unittest.mock import MagicMock, patch

from src.core.llm_client import LLMClient


class TestLLMClient:
    """Test cases for LLMClient."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        with patch("src.core.llm_client.ZhipuAI"):
            self.client = LLMClient()

    @patch("src.core.llm_client.ZhipuAI")
    def test_initialization(self, mock_zhipuai: MagicMock) -> None:
        """Test LLM client initialization."""
        client = LLMClient()
        assert client.client is not None
        # Model should match config (glm-4-flash or glm-4.7)
        assert client.model in ["glm-4-flash", "glm-4.7"]

    def test_build_system_prompt_without_context(self) -> None:
        """Test building system prompt without context."""
        prompt = self.client._build_system_prompt()
        assert "公司助手" in prompt
        assert "上下文" not in prompt or "上下文信息" in prompt

    def test_build_system_prompt_with_context(self) -> None:
        """Test building system prompt with context."""
        context = "这是测试上下文"
        prompt = self.client._build_system_prompt(context)
        assert context in prompt
        assert "上下文信息" in prompt
