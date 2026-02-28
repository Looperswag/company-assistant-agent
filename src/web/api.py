"""FastAPI web API for the assistant."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.core.assistant import Assistant
from src.knowledge.parser import MarkdownParser
from src.knowledge.vector_store import VectorStore
from src.utils.config import config
from src.utils.logger import logger

app = FastAPI(
    title="小美智能客服API",
    description="AI驱动的公司客服助手Web API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = Assistant()
_kb_init_lock = Lock()


class SourceItem(BaseModel):
    """Citation/source item for an assistant response."""

    title: str
    source: str
    chunk_index: int = 0
    similarity: float = 0.0
    strategy: str = "vector"
    snippet: str = ""


class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    query: str = Field(min_length=1)
    use_history: bool = True
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    response: str
    session_id: str
    sources: List[SourceItem] = Field(default_factory=list)
    latency_ms: int = 0


class ClearHistoryRequest(BaseModel):
    """Request model for clearing history."""

    session_id: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    status: str
    message: str


class KnowledgeSearchRequest(BaseModel):
    """Request model for knowledge search endpoint."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=8, ge=1, le=30)
    min_similarity: float = Field(default=0.2, ge=0.0, le=1.0)


class KnowledgeItem(BaseModel):
    """Knowledge search result item."""

    title: str
    source: str
    chunk_index: int
    snippet: str
    similarity: float
    strategy: str


class KnowledgeSearchResponse(BaseModel):
    """Response model for knowledge search endpoint."""

    items: List[KnowledgeItem]


class KnowledgeDocument(BaseModel):
    """Document overview item for knowledge panel."""

    source: str
    title: str
    chunks: int


class KnowledgeOverviewResponse(BaseModel):
    """Response model for knowledge overview endpoint."""

    total_chunks: int
    total_documents: int
    documents: List[KnowledgeDocument]


class SessionHistoryResponse(BaseModel):
    """Response model for per-session history."""

    session_id: str
    history: List[dict]
    last_accessed_at: Optional[datetime] = None


def _normalize_session_id(session_id: Optional[str]) -> str:
    """Normalize session id for API responses."""
    normalized = (session_id or Assistant.DEFAULT_SESSION_ID).strip()
    return normalized or Assistant.DEFAULT_SESSION_ID


def _get_assistant_vector_store() -> VectorStore:
    """Get the active vector store used by assistant components."""
    if getattr(assistant, "hybrid_retriever", None) and getattr(
        assistant.hybrid_retriever, "vector_store", None
    ):
        return assistant.hybrid_retriever.vector_store
    if getattr(assistant, "retriever", None) and getattr(
        assistant.retriever, "vector_store", None
    ):
        return assistant.retriever.vector_store
    return VectorStore()


def _ensure_knowledge_initialized() -> None:
    """Lazy-initialize vector store from markdown files if empty."""
    vector_store = _get_assistant_vector_store()
    if vector_store.get_collection_size() > 0:
        return

    with _kb_init_lock:
        vector_store = _get_assistant_vector_store()
        if vector_store.get_collection_size() > 0:
            return

        parser = MarkdownParser(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        chunks = parser.parse_directory(config.knowledge_base_path)
        if not chunks:
            logger.warning(
                f"Auto-init skipped: no markdown files found in {config.knowledge_base_path}"
            )
            return

        logger.info(f"Auto-initializing knowledge base with {len(chunks)} chunks...")
        vector_store.add_documents(chunks)


def _sse_event(event: str, payload: dict) -> str:
    """Format Server-Sent Event payload."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Process a user query and return non-streaming response."""
    session_id = _normalize_session_id(request.session_id)
    start = time.perf_counter()

    try:
        _ensure_knowledge_initialized()
        result = assistant.process_query_with_metadata(
            query=request.query,
            use_history=request.use_history,
            session_id=session_id,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        sources = [SourceItem(**source) for source in result.get("sources", [])]

        return QueryResponse(
            response=result["response"],
            session_id=session_id,
            sources=sources,
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/stream")
async def query_stream(request: QueryRequest) -> StreamingResponse:
    """Process a user query and return SSE streaming response."""
    session_id = _normalize_session_id(request.session_id)

    async def event_generator():
        start = time.perf_counter()
        try:
            _ensure_knowledge_initialized()
            stream_iter, sources = assistant.stream_query_with_metadata(
                query=request.query,
                use_history=request.use_history,
                session_id=session_id,
            )

            yield _sse_event("sources", {"session_id": session_id, "sources": sources})

            for chunk in stream_iter:
                if chunk:
                    yield _sse_event("chunk", {"content": chunk})

            latency_ms = int((time.perf_counter() - start) * 1000)
            yield _sse_event(
                "done",
                {
                    "session_id": session_id,
                    "latency_ms": latency_ms,
                },
            )
        except Exception as e:
            logger.error(f"Streaming query failed: {e}")
            yield _sse_event(
                "error",
                {
                    "session_id": session_id,
                    "message": f"流式响应失败: {str(e)}",
                },
            )

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


@app.post("/api/knowledge/search", response_model=KnowledgeSearchResponse)
async def knowledge_search(request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    """Search knowledge base directly for UI knowledge panel."""
    try:
        _ensure_knowledge_initialized()
        results = assistant.search_knowledge(
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )

        items: List[KnowledgeItem] = []
        for result in results:
            metadata = result.get("metadata", {})
            similarity = float(result.get("similarity", result.get("score", 0.0)))
            items.append(
                KnowledgeItem(
                    title=str(metadata.get("title", "未知")),
                    source=str(metadata.get("source", "未知")),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    snippet=str(result.get("text", "")).replace("\n", " ")[:320],
                    similarity=similarity,
                    strategy=str(result.get("strategy", result.get("type", "vector"))),
                )
            )

        return KnowledgeSearchResponse(items=items)
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/overview", response_model=KnowledgeOverviewResponse)
async def knowledge_overview() -> KnowledgeOverviewResponse:
    """Get high-level knowledge base overview."""
    try:
        _ensure_knowledge_initialized()
        vector_store = _get_assistant_vector_store()
        overview = vector_store.get_document_overview()

        documents = [KnowledgeDocument(**doc) for doc in overview.get("documents", [])]
        return KnowledgeOverviewResponse(
            total_chunks=int(overview.get("total_chunks", 0)),
            total_documents=int(overview.get("total_documents", 0)),
            documents=documents,
        )
    except Exception as e:
        logger.error(f"Error getting knowledge overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str) -> SessionHistoryResponse:
    """Get history for the specified session."""
    try:
        normalized = _normalize_session_id(session_id)
        history = assistant.get_history(normalized)
        last_accessed = assistant.get_session_last_access(normalized)

        return SessionHistoryResponse(
            session_id=normalized,
            history=history,
            last_accessed_at=last_accessed,
        )
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}/history", response_model=StatusResponse)
async def clear_session_history(session_id: str) -> StatusResponse:
    """Clear history for the specified session."""
    try:
        normalized = _normalize_session_id(session_id)
        assistant.clear_history(normalized)
        return StatusResponse(status="success", message="会话历史已清空")
    except Exception as e:
        logger.error(f"Error clearing session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-history", response_model=StatusResponse)
async def clear_history(request: ClearHistoryRequest) -> StatusResponse:
    """Legacy endpoint: clear history for session (default session if omitted)."""
    try:
        session_id = _normalize_session_id(request.session_id)
        assistant.clear_history(session_id)
        return StatusResponse(status="success", message="对话历史已清空")
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history() -> dict:
    """Legacy endpoint: get default session history."""
    try:
        history = assistant.get_history(Assistant.DEFAULT_SESSION_ID)
        return {"history": history}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Get system status."""
    try:
        _ensure_knowledge_initialized()
        vector_store = _get_assistant_vector_store()
        count = vector_store.get_collection_size()

        message = f"系统运行正常。知识库包含 {count} 个文档块。"
        if count == 0:
            message += " 请先运行初始化命令。"

        return StatusResponse(status="ok", message=message)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return StatusResponse(status="error", message=str(e))


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def web_ui() -> str:
    """Serve the web UI."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
