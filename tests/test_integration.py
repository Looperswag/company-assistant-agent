"""Integration tests for assistant session and history behavior."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from src.core.assistant import Assistant, SessionState
from src.core.classifier import QueryType
from src.utils.error_handler import GLMConnectionError


class TestAssistantIntegration:
    """Integration tests for Assistant."""

    def setup_method(self) -> None:
        """Set up test fixtures with mocked external dependencies."""
        with (
            patch("src.core.assistant.QueryClassifier") as mock_classifier,
            patch("src.core.assistant.SafetyFilter") as mock_safety_filter,
            patch("src.core.assistant.HybridRetriever") as mock_hybrid,
            patch("src.core.assistant.WebSearcher") as mock_searcher,
            patch("src.core.assistant.LLMClient") as mock_llm,
        ):
            self.assistant = Assistant(use_hybrid_retriever=True)
            self.assistant.classifier = mock_classifier.return_value
            self.assistant.safety_filter = mock_safety_filter.return_value
            self.assistant.hybrid_retriever = mock_hybrid.return_value
            self.assistant.searcher = mock_searcher.return_value
            self.assistant.llm_client = mock_llm.return_value

            self.assistant.safety_filter.check.return_value = (True, "")
            self.assistant.classifier.classify.return_value = QueryType.EXTERNAL_KNOWLEDGE
            self.assistant.searcher.search.return_value = []
            self.assistant.llm_client.generate_with_context.return_value = "test response"
            self.assistant.llm_client.stream_with_context.return_value = iter(["stream", " response"])

    def test_clear_history(self) -> None:
        """Test clearing conversation history for default session."""
        self.assistant.process_query("hello")
        assert len(self.assistant.get_history()) == 2

        self.assistant.clear_history()
        assert self.assistant.get_history() == []

    def test_get_history_returns_copy(self) -> None:
        """Test getting conversation history returns a copy."""
        self.assistant.process_query("test")
        history = self.assistant.get_history()
        assert len(history) == 2
        assert history is not self.assistant.get_history()

    def test_session_isolation(self) -> None:
        """Different session IDs should not share history."""
        self.assistant.process_query("question 1", session_id="session-a")
        self.assistant.process_query("question 2", session_id="session-b")

        history_a = self.assistant.get_history("session-a")
        history_b = self.assistant.get_history("session-b")

        assert len(history_a) == 2
        assert len(history_b) == 2
        assert history_a[0]["content"] == "question 1"
        assert history_b[0]["content"] == "question 2"

    def test_ttl_cleanup_removes_expired_sessions(self) -> None:
        """Expired sessions should be removed during session access."""
        old_session = SessionState(history=[{"role": "user", "content": "old"}])
        old_session.last_accessed = self.assistant._utc_now() - timedelta(hours=25)
        self.assistant.sessions["expired"] = old_session

        _ = self.assistant.get_history("fresh")

        assert "expired" not in self.assistant.sessions

    def test_process_query_with_sources(self) -> None:
        """Structured sources should be returned in metadata mode."""
        self.assistant.classifier.classify.return_value = QueryType.COMPANY_INTERNAL
        self.assistant.search_knowledge = MagicMock(
            return_value=[
                {
                    "text": "chunk content",
                    "metadata": {
                        "title": "Company Policy",
                        "source": "Knowledge Base/Company Policies.md",
                        "chunk_index": 2,
                    },
                    "similarity": 0.83,
                    "strategy": "hybrid",
                }
            ]
        )
        self.assistant.hybrid_retriever.format_results.return_value = "知识库上下文"

        result = self.assistant.process_query_with_metadata("policy question", session_id="s-1")

        assert result["response"] == "test response"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "Company Policy"
        assert result["sources"][0]["strategy"] == "hybrid"

    def test_stream_query_updates_history(self) -> None:
        """Streaming responses should be accumulated and stored in history."""
        stream_iter, sources = self.assistant.stream_query_with_metadata(
            "stream me",
            session_id="stream-session",
        )
        response = "".join(stream_iter)
        history = self.assistant.get_history("stream-session")

        assert response == "stream response"
        assert sources == []
        assert history[-1]["content"] == "stream response"

    def test_non_stream_fallback_returns_direct_answer(self) -> None:
        """Fallback should return direct answer instead of raw similarity dump."""
        self.assistant.classifier.classify.return_value = QueryType.COMPANY_INTERNAL
        self.assistant.search_knowledge = MagicMock(
            return_value=[
                {
                    "text": "Leave Request Process submit through HR Portal at least 2 weeks in advance. Manager approves within 5 business days.",
                    "metadata": {
                        "title": "Company Procedures",
                        "source": "Knowledge Base/Company Procedures & Guidelines.md",
                        "chunk_index": 1,
                    },
                    "similarity": 0.8,
                    "strategy": "vector",
                }
            ]
        )
        self.assistant.hybrid_retriever.format_results.return_value = (
            "知识库检索结果：\\n\\n1. [Company Procedures] (相似度: 0.80)\\n来源: some/path"
        )
        self.assistant.llm_client.generate_with_context.side_effect = GLMConnectionError(
            "network down"
        )

        result = self.assistant.process_query_with_metadata("如何申请年假", session_id="fallback-s")
        response = result["response"]

        assert "根据知识库" in response
        assert "相似度" not in response
        assert "来源:" not in response
        assert "申请流程" in response

    def test_stream_fallback_returns_direct_answer(self) -> None:
        """Streaming fallback should also avoid raw retrieval dump."""
        self.assistant.classifier.classify.return_value = QueryType.COMPANY_INTERNAL
        self.assistant.search_knowledge = MagicMock(
            return_value=[
                {
                    "text": "20 paid leave days per calendar year. Submit request through HR Portal at least 2 weeks in advance.",
                    "metadata": {
                        "title": "Company Policies",
                        "source": "Knowledge Base/Company Policies.md",
                        "chunk_index": 0,
                    },
                    "similarity": 0.79,
                    "strategy": "vector",
                }
            ]
        )
        self.assistant.hybrid_retriever.format_results.return_value = (
            "知识库检索结果：\\n\\n1. [Company Policies] (相似度: 0.79)\\n来源: some/path"
        )
        self.assistant.llm_client.stream_with_context.side_effect = GLMConnectionError(
            "network down"
        )

        stream_iter, _ = self.assistant.stream_query_with_metadata(
            "如何申请年假",
            session_id="fallback-stream-s",
        )
        response = "".join(stream_iter)

        assert "根据知识库" in response
        assert "相似度" not in response
        assert "来源:" not in response
