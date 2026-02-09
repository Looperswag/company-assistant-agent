"""Configuration management module."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration manager."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        # 智谱AI配置
        self.zhipuai_api_key: str = os.getenv("ZHIPUAI_API_KEY", "")
        self.zhipuai_base_url: str = os.getenv("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.zhipuai_model: str = os.getenv("ZHIPUAI_MODEL", "glm-4.7")
        self.glm_api_timeout: int = int(os.getenv("GLM_API_TIMEOUT", "60"))
        self.glm_max_retries: int = int(os.getenv("GLM_MAX_RETRIES", "3"))
        self.glm_connection_timeout: int = int(os.getenv("GLM_CONNECTION_TIMEOUT", "30"))

        # Embedding配置
        self.embedding_model: str = os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )

        # 知识库配置
        base_path = Path(__file__).parent.parent.parent
        self.knowledge_base_path: Path = base_path / os.getenv(
            "KNOWLEDGE_BASE_PATH", "Knowledge Base"
        )
        self.vector_db_path: Path = base_path / os.getenv("VECTOR_DB_PATH", "chroma_db")
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
        self.similarity_threshold: float = float(
            os.getenv("SIMILARITY_THRESHOLD", "0.3")
        )
        self.min_similarity: float = float(
            os.getenv("MIN_SIMILARITY", "0.25")
        )
        self.max_results: int = int(os.getenv("MAX_RESULTS", "10"))
        self.top_k: int = int(os.getenv("TOP_K", "5"))
        self.retrieval_strategy: str = os.getenv("RETRIEVAL_STRATEGY", "auto")

        # 搜索配置
        self.search_enabled: bool = os.getenv("SEARCH_ENABLED", "true").lower() == "true"
        self.max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
        self.search_provider: str = os.getenv("SEARCH_PROVIDER", "auto").lower()  # "glm", "duckduckgo", "auto"
        self.search_strategy: str = os.getenv("SEARCH_STRATEGY", "auto").lower()  # "auto", "glm_first", "ddg_first", "glm_only", "ddg_only"
        self.search_recency_filter: str = os.getenv("SEARCH_RECENCY_FILTER", "")  # e.g., "7d", "30d"
        self.search_fallback_enabled: bool = os.getenv("SEARCH_FALLBACK_ENABLED", "true").lower() == "true"
        self.search_cache_enabled: bool = os.getenv("SEARCH_CACHE_ENABLED", "true").lower() == "true"
        self.search_cache_ttl: int = int(os.getenv("SEARCH_CACHE_TTL", "3600"))  # seconds, default 1 hour
        self.search_quality_threshold: float = float(os.getenv("SEARCH_QUALITY_THRESHOLD", "0.3"))

        # 安全配置
        self.safety_filter_enabled: bool = (
            os.getenv("SAFETY_FILTER_ENABLED", "true").lower() == "true"
        )

        # LLM配置
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "65536"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
        self.stream_enabled: bool = (
            os.getenv("STREAM_ENABLED", "true").lower() == "true"
        )
        self.thinking_enabled: bool = (
            os.getenv("THINKING_ENABLED", "true").lower() == "true"
        )

        # 日志配置
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: Optional[str] = os.getenv("LOG_FILE", "assistant.log")

    def validate(self) -> bool:
        """Validate configuration settings."""
        if not self.zhipuai_api_key:
            raise ValueError("ZHIPUAI_API_KEY is required")
        if not self.knowledge_base_path.exists():
            raise ValueError(f"Knowledge base path does not exist: {self.knowledge_base_path}")
        return True


# Global configuration instance
config = Config()
