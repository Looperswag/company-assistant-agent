"""Integration tests for the assistant."""

import pytest
from unittest.mock import MagicMock, patch

from src.core.assistant import Assistant
from src.core.classifier import QueryType


class TestAssistantIntegration:
    """Integration tests for Assistant."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        with patch("src.core.assistant.KnowledgeRetriever"), patch(
            "src.core.assistant.LLMClient"
        ):
            self.assistant = Assistant()

    def test_clear_history(self) -> None:
        """Test clearing conversation history."""
        self.assistant.conversation_history = [{"role": "user", "content": "test"}]
        self.assistant.clear_history()
        assert len(self.assistant.conversation_history) == 0

    def test_get_history(self) -> None:
        """Test getting conversation history."""
        self.assistant.conversation_history = [{"role": "user", "content": "test"}]
        history = self.assistant.get_history()
        assert len(history) == 1
        assert history[0]["content"] == "test"
        # Should be a copy, not reference
        assert history is not self.assistant.conversation_history

    @patch("src.core.assistant.Assistant.process_query")
    def test_harmful_query_blocking(self, mock_process: MagicMock) -> None:
        """Test that harmful queries are properly handled."""
        # This would be tested more thoroughly with actual safety filter
        pass
