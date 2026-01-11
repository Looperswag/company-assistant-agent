"""FastAPI web API for the assistant."""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.core.assistant import Assistant
from src.utils.logger import logger

app = FastAPI(
    title="Company Assistant Agent API",
    description="AI-powered company assistant web API",
    version="0.1.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global assistant instance
assistant = Assistant()


class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    query: str
    use_history: bool = True
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    response: str
    session_id: str


class ClearHistoryRequest(BaseModel):
    """Request model for clearing history."""

    session_id: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    status: str
    message: str


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Process a user query.

    Args:
        request: Query request with query text and options

    Returns:
        Query response with assistant's answer
    """
    try:
        response = assistant.process_query(request.query, use_history=request.use_history)
        session_id = request.session_id or "default"

        return QueryResponse(response=response, session_id=session_id)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-history")
async def clear_history(request: ClearHistoryRequest) -> StatusResponse:
    """Clear conversation history.

    Args:
        request: Clear history request

    Returns:
        Status response
    """
    try:
        assistant.clear_history()
        return StatusResponse(status="success", message="对话历史已清空")
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history() -> dict:
    """Get conversation history.

    Returns:
        Conversation history
    """
    try:
        history = assistant.get_history()
        return {"history": history}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Get system status.

    Returns:
        System status
    """
    try:
        from src.knowledge.vector_store import VectorStore

        vector_store = VectorStore()
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
    from pathlib import Path

    html_path = Path(__file__).parent / "templates" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
