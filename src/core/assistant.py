"""Main assistant orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Iterator, List, Optional, Tuple

from src.core.classifier import QueryClassifier, QueryType
from src.core.hybrid_retriever import HybridRetriever
from src.core.llm_client import LLMClient
from src.core.retriever import KnowledgeRetriever
from src.core.safety_filter import SafetyFilter
from src.core.searcher import WebSearcher
from src.utils.config import config
from src.utils.error_handler import (
    ERROR_MESSAGES,
    GLMAPIError,
    GLMAuthenticationError,
    GLMConnectionError,
    GLMQuotaExceededError,
    GLMRateLimitError,
    GLMServerError,
    GLMTimeoutError,
)
from src.utils.logger import logger


@dataclass
class SessionState:
    """Conversation state for a single session."""

    history: List[dict] = field(default_factory=list)
    last_accessed: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Assistant:
    """Main assistant class that orchestrates all components."""

    DEFAULT_SESSION_ID = "default"
    SESSION_TTL = timedelta(hours=24)
    MAX_HISTORY_MESSAGES = 20

    def __init__(self, use_hybrid_retriever: bool = True) -> None:
        """Initialize the assistant.

        Args:
            use_hybrid_retriever: Whether to use the new HybridRetriever (default: True)
        """
        self.classifier = QueryClassifier()
        self.safety_filter = SafetyFilter() if config.safety_filter_enabled else None

        if use_hybrid_retriever:
            self.hybrid_retriever = HybridRetriever()
            self.retriever = None
            logger.info("Using HybridRetriever with multilingual support")
        else:
            self.retriever = KnowledgeRetriever()
            self.hybrid_retriever = None
            logger.info("Using legacy KnowledgeRetriever")

        self.searcher = WebSearcher()
        self.llm_client = LLMClient()
        self.sessions: Dict[str, SessionState] = {}

    @property
    def conversation_history(self) -> List[dict]:
        """Backward-compatible access to default session history."""
        session = self._get_session(self.DEFAULT_SESSION_ID, create=True)
        return session.history if session else []

    @conversation_history.setter
    def conversation_history(self, history: List[dict]) -> None:
        """Backward-compatible setter for default session history."""
        session = self._get_session(self.DEFAULT_SESSION_ID, create=True)
        if session is None:
            return
        session.history = history
        session.last_accessed = self._utc_now()

    def _utc_now(self) -> datetime:
        """Return timezone-aware UTC now."""
        return datetime.now(timezone.utc)

    def _normalize_session_id(self, session_id: Optional[str]) -> str:
        """Normalize session id with fallback default."""
        normalized = (session_id or self.DEFAULT_SESSION_ID).strip()
        return normalized or self.DEFAULT_SESSION_ID

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions based on TTL."""
        now = self._utc_now()
        expired_ids = [
            sid
            for sid, session in self.sessions.items()
            if now - session.last_accessed > self.SESSION_TTL
        ]
        for sid in expired_ids:
            del self.sessions[sid]

        if expired_ids:
            logger.info(f"Expired sessions cleaned: {len(expired_ids)}")

    def _get_session(
        self, session_id: Optional[str], create: bool = True
    ) -> Optional[SessionState]:
        """Get (and optionally create) a session."""
        self._cleanup_expired_sessions()
        normalized_id = self._normalize_session_id(session_id)
        session = self.sessions.get(normalized_id)

        if session is None and create:
            session = SessionState()
            self.sessions[normalized_id] = session

        if session is not None:
            session.last_accessed = self._utc_now()

        return session

    def _append_history(self, session_id: str, query: str, response: str) -> None:
        """Append query/response pair to session history."""
        session = self._get_session(session_id, create=True)
        if session is None:
            return

        session.history.append({"role": "user", "content": query})
        session.history.append({"role": "assistant", "content": response})

        if len(session.history) > self.MAX_HISTORY_MESSAGES:
            session.history = session.history[-self.MAX_HISTORY_MESSAGES :]

    def _format_sources(self, results: List[dict]) -> List[dict]:
        """Format retrieval results into API source items."""
        seen = set()
        formatted_sources: List[dict] = []

        for result in results:
            metadata = result.get("metadata", {})
            source = str(metadata.get("source", "未知"))
            chunk_index = int(metadata.get("chunk_index", 0))
            dedupe_key = f"{source}:{chunk_index}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            formatted_sources.append(
                {
                    "title": str(metadata.get("title", "未知")),
                    "source": source,
                    "chunk_index": chunk_index,
                    "similarity": float(
                        result.get("similarity", result.get("score", 0.0))
                    ),
                    "strategy": str(
                        result.get("strategy", result.get("type", "vector"))
                    ),
                    "snippet": str(result.get("text", "")).replace("\n", " ")[:280],
                }
            )

        return formatted_sources

    def _format_web_sources(self, results: List[dict]) -> List[dict]:
        """Format web search results into source-like items."""
        formatted_sources: List[dict] = []
        for result in results:
            formatted_sources.append(
                {
                    "title": str(result.get("title", "Web Result")),
                    "source": str(result.get("url", "")),
                    "chunk_index": 0,
                    "similarity": float(result.get("quality_score", 0.0)),
                    "strategy": "web",
                    "snippet": str(result.get("snippet", "")).replace("\n", " ")[:280],
                }
            )
        return formatted_sources

    def search_knowledge(
        self, query: str, top_k: int = 8, min_similarity: float = 0.2
    ) -> List[dict]:
        """Search knowledge base and return structured retrieval results."""
        if self.hybrid_retriever:
            return self.hybrid_retriever.retrieve(
                query=query,
                top_k=top_k,
                strategy=config.retrieval_strategy,
                min_similarity=min_similarity,
            )

        if self.retriever:
            return self.retriever.get_relevant_chunks(query=query, n_results=top_k)

        return []

    def _retrieve_context_and_sources(
        self, query: str, query_type: QueryType
    ) -> Tuple[str, List[dict], bool]:
        """Retrieve context and sources based on query type."""
        context = ""
        sources: List[dict] = []
        needs_clarification = False

        if query_type == QueryType.COMPANY_INTERNAL:
            kb_results = self.search_knowledge(
                query=query,
                top_k=config.max_results,
                min_similarity=config.min_similarity,
            )
            if kb_results:
                sources = self._format_sources(kb_results)
                if self.hybrid_retriever:
                    context = self.hybrid_retriever.format_results(kb_results)
                elif self.retriever:
                    context = self.retriever.retrieve(query, n_results=config.max_results)
            else:
                logger.info("No KB results, trying web search")
                web_results = self.searcher.search(query)
                if web_results:
                    sources = self._format_web_sources(web_results)
                    context = self.searcher.format_search_results(web_results)
        elif query_type == QueryType.EXTERNAL_KNOWLEDGE:
            web_results = self.searcher.search(query)
            if web_results:
                sources = self._format_web_sources(web_results)
                context = self.searcher.format_search_results(web_results)
        elif query_type == QueryType.AMBIGUOUS:
            kb_results = self.search_knowledge(query=query, top_k=5, min_similarity=0.2)
            if kb_results:
                sources = self._format_sources(kb_results)
                if self.hybrid_retriever:
                    context = self.hybrid_retriever.format_results(kb_results)
                elif self.retriever:
                    context = self.retriever.retrieve(query, n_results=5)
            else:
                web_results = self.searcher.search(query)
                if web_results:
                    sources = self._format_web_sources(web_results)
                    context = self.searcher.format_search_results(web_results)
                else:
                    needs_clarification = True

        return context, sources, needs_clarification

    def process_query_with_metadata(
        self,
        query: str,
        use_history: bool = True,
        session_id: Optional[str] = None,
    ) -> dict:
        """Process user query and return response with metadata."""
        normalized_session_id = self._normalize_session_id(session_id)
        session = self._get_session(normalized_session_id, create=True)
        conversation_history = (
            session.history if (use_history and session is not None) else []
        )

        if self.safety_filter:
            is_safe, reason = self.safety_filter.check(query)
            if not is_safe:
                response = f"Sorry, I cannot process this request. {reason}"
                if use_history:
                    self._append_history(normalized_session_id, query, response)
                return {"response": response, "sources": []}

        query_type = self.classifier.classify(query)
        logger.info(f"Query classified as: {query_type.value}")

        if query_type == QueryType.HARMFUL:
            response = (
                "Sorry, I cannot process this request. Please ensure your query "
                "complies with company policies and ethical guidelines."
            )
            if use_history:
                self._append_history(normalized_session_id, query, response)
            return {"response": response, "sources": []}

        context, sources, needs_clarification = self._retrieve_context_and_sources(
            query, query_type
        )

        if needs_clarification:
            response = self._ask_clarification(query)
        else:
            try:
                response = self.llm_client.generate_with_context(
                    query=query,
                    context=context if context else None,
                    conversation_history=conversation_history,
                )
            except GLMConnectionError as e:
                logger.error(f"Connection error: {e}")
                response = (
                    self._build_fallback_answer(query, context, sources)
                    if context
                    else ERROR_MESSAGES["connection_error"]
                )
            except GLMTimeoutError as e:
                logger.error(f"Timeout error: {e}")
                response = (
                    self._build_fallback_answer(query, context, sources)
                    if context
                    else ERROR_MESSAGES["timeout_error"]
                )
            except GLMAuthenticationError as e:
                logger.error(f"Authentication error: {e}")
                response = ERROR_MESSAGES["authentication_error"]
            except GLMRateLimitError as e:
                logger.error(f"Rate limit error: {e}")
                response = ERROR_MESSAGES["rate_limit_error"]
            except GLMQuotaExceededError as e:
                logger.error(f"Quota exceeded error: {e}")
                response = ERROR_MESSAGES["quota_exceeded"]
            except GLMServerError as e:
                logger.error(f"Server error: {e}")
                response = (
                    self._build_fallback_answer(query, context, sources)
                    if context
                    else ERROR_MESSAGES["server_error"]
                )
            except GLMAPIError as e:
                logger.error(f"API error: {e}")
                response = (
                    self._build_fallback_answer(query, context, sources)
                    if context
                    else str(e)
                )
            except Exception as e:
                logger.error(f"Unexpected error during LLM generation: {e}")
                response = (
                    self._build_fallback_answer(query, context, sources)
                    if context
                    else (
                        "Sorry, I am currently unable to generate a response. "
                        "Please try again later or contact the administrator."
                    )
                )

        if use_history:
            self._append_history(normalized_session_id, query, response)

        return {"response": response, "sources": sources}

    def stream_query_with_metadata(
        self,
        query: str,
        use_history: bool = True,
        session_id: Optional[str] = None,
    ) -> Tuple[Iterator[str], List[dict]]:
        """Process query and return streaming response iterator with sources."""
        normalized_session_id = self._normalize_session_id(session_id)
        session = self._get_session(normalized_session_id, create=True)
        conversation_history = (
            session.history if (use_history and session is not None) else []
        )

        if self.safety_filter:
            is_safe, reason = self.safety_filter.check(query)
            if not is_safe:
                blocked = f"Sorry, I cannot process this request. {reason}"
                if use_history:
                    self._append_history(normalized_session_id, query, blocked)
                return iter([blocked]), []

        query_type = self.classifier.classify(query)
        logger.info(f"Query classified as: {query_type.value}")

        if query_type == QueryType.HARMFUL:
            blocked = (
                "Sorry, I cannot process this request. Please ensure your query "
                "complies with company policies and ethical guidelines."
            )
            if use_history:
                self._append_history(normalized_session_id, query, blocked)
            return iter([blocked]), []

        context, sources, needs_clarification = self._retrieve_context_and_sources(
            query, query_type
        )
        if needs_clarification:
            clarification = self._ask_clarification(query)
            if use_history:
                self._append_history(normalized_session_id, query, clarification)
            return iter([clarification]), sources

        def stream_generator() -> Iterator[str]:
            chunks: List[str] = []
            try:
                for chunk in self.llm_client.stream_with_context(
                    query=query,
                    context=context if context else None,
                    conversation_history=conversation_history,
                ):
                    if chunk:
                        chunks.append(chunk)
                        yield chunk
            except (GLMConnectionError, GLMTimeoutError, GLMServerError, GLMAPIError):
                if context and not chunks:
                    fallback = self._build_fallback_answer(query, context, sources)
                    chunks = [fallback]
                    yield fallback
                else:
                    raise
            finally:
                final_response = "".join(chunks).strip()
                if use_history and final_response:
                    self._append_history(normalized_session_id, query, final_response)

        return stream_generator(), sources

    def process_query(
        self,
        query: str,
        use_history: bool = True,
        session_id: Optional[str] = None,
    ) -> str:
        """Backward-compatible query processing API."""
        result = self.process_query_with_metadata(
            query=query,
            use_history=use_history,
            session_id=session_id,
        )
        return result["response"]

    def _format_context_response(self, query: str, context: str) -> str:
        """Format a response based on context when LLM is unavailable."""
        response = (
            "Based on the knowledge base, I found the following relevant "
            f"information:\n\n{context}\n\n"
        )
        response += (
            "Note: Due to temporary API service unavailability, the above is the raw "
            "content retrieved directly from the knowledge base."
        )
        return response

    def _clean_text(self, text: str) -> str:
        """Normalize text for fallback answer rendering."""
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        return cleaned.replace("**", "")

    def _extract_leave_answer(self, snippets: List[str]) -> Optional[str]:
        """Build a concise leave-policy answer from snippets when possible."""
        if not snippets:
            return None

        text = " ".join(self._clean_text(s) for s in snippets)
        text_lower = text.lower()

        if not any(
            kw in text_lower
            for kw in ["leave", "vacation", "time off", "请假", "年假", "休假", "病假"]
        ):
            return None

        days_match = re.search(
            r"(\d+)\s*(?:paid leave days|days of paid annual leave|天(?:带薪)?(?:年)?假)",
            text_lower,
        )
        lead_time_match = re.search(
            r"(?:at least|提前)\s*(\d+)\s*(?:weeks?|周)",
            text_lower,
        )
        approval_match = re.search(
            r"within\s*(\d+)\s*business days|(\d+)\s*个工作日",
            text_lower,
        )
        sick_note_match = re.search(
            r"(?:beyond|超过)\s*(\d+)\s*(?:consecutive days|天)",
            text_lower,
        )

        days = days_match.group(1) if days_match else None
        lead_time = lead_time_match.group(1) if lead_time_match else None
        if approval_match:
            approval = approval_match.group(1) or approval_match.group(2)
        else:
            approval = None
        sick_note_days = sick_note_match.group(1) if sick_note_match else None

        lines = ["根据知识库，关于请假/年假的直接答案如下："]
        if days:
            lines.append(f"1. 年假政策：每年约 {days} 天带薪年假（另有法定节假日）。")
        else:
            lines.append("1. 年假政策：公司提供带薪年假，具体天数以制度条款为准。")

        if lead_time and approval:
            lines.append(
                f"2. 申请流程：至少提前 {lead_time} 周通过 HR Portal 提交，经理通常在 {approval} 个工作日内审批，随后 HR 更新记录并邮件确认。"
            )
        elif lead_time:
            lines.append(
                f"2. 申请流程：至少提前 {lead_time} 周通过 HR Portal 提交，经理审批后由 HR 更新记录并确认。"
            )
        else:
            lines.append("2. 申请流程：通过 HR Portal 提交请假申请，经理审批后由 HR 更新记录并确认。")

        if sick_note_days:
            lines.append(f"3. 病假补充：连续超过 {sick_note_days} 天通常需要医生证明。")

        lines.append("如需我可以继续给你整理为“可直接执行的申请步骤清单”。")
        return "\n".join(lines)

    def _build_fallback_answer(
        self, query: str, context: str, sources: Optional[List[dict]] = None
    ) -> str:
        """Build a direct answer from retrieved context when LLM is unavailable."""
        source_snippets = [s.get("snippet", "") for s in (sources or []) if s.get("snippet")]
        leave_answer = self._extract_leave_answer(source_snippets + [context])
        if leave_answer:
            return leave_answer

        summary_points: List[str] = []
        for snippet in source_snippets[:3]:
            cleaned = self._clean_text(snippet)
            if cleaned:
                summary_points.append(cleaned[:220])

        if not summary_points:
            context_lines = [
                self._clean_text(line)
                for line in context.splitlines()
                if line.strip() and "相似度" not in line and "来源:" not in line
            ]
            summary_points.extend([line[:220] for line in context_lines[:3] if line])

        if summary_points:
            bullets = "\n".join(f"{idx}. {point}" for idx, point in enumerate(summary_points, 1))
            return (
                "根据知识库，先给你直接结论：\n"
                f"{bullets}\n"
                "如果你需要，我可以再按“步骤/条件/注意事项”整理成更简洁版本。"
            )

        return ERROR_MESSAGES["server_error"]

    def _ask_clarification(self, query: str) -> str:
        """Ask user for clarification on ambiguous queries."""
        return f"""Your question "{query}" may relate to company internal information or external knowledge.

Please let me know:
1. If you want to know about company policies, procedures, or regulations, please specify
2. If you want to know about general knowledge or latest information, I can search the web for you

Alternatively, you can rephrase your question to be more specific."""

    def clear_history(self, session_id: Optional[str] = None) -> None:
        """Clear conversation history for one session."""
        normalized_session_id = self._normalize_session_id(session_id)
        session = self._get_session(normalized_session_id, create=False)
        if session:
            session.history = []
            session.last_accessed = self._utc_now()
        logger.info(f"Conversation history cleared for session: {normalized_session_id}")

    def get_history(self, session_id: Optional[str] = None) -> List[dict]:
        """Get conversation history for one session."""
        normalized_session_id = self._normalize_session_id(session_id)
        session = self._get_session(normalized_session_id, create=False)
        if not session:
            return []
        return session.history.copy()

    def get_session_last_access(self, session_id: Optional[str] = None) -> Optional[datetime]:
        """Get last access time for a session."""
        normalized_session_id = self._normalize_session_id(session_id)
        session = self._get_session(normalized_session_id, create=False)
        if not session:
            return None
        return session.last_accessed
