"""Knowledge base retriever for RAG operations."""

from typing import List, Optional

from src.knowledge.vector_store import VectorStore
from src.utils.config import config
from src.utils.logger import logger


class KnowledgeRetriever:
    """Retrieves relevant information from the knowledge base."""

    def __init__(self, vector_store: Optional[VectorStore] = None) -> None:
        """Initialize the retriever.

        Args:
            vector_store: Optional vector store instance (creates new if None)
        """
        self.vector_store = vector_store or VectorStore()
        self.threshold = config.similarity_threshold

    def retrieve(self, query: str, n_results: int = 5) -> str:
        """Retrieve relevant context from knowledge base.

        Args:
            query: Search query
            n_results: Number of results to retrieve

        Returns:
            Formatted context string
        """
        try:
            results = self.vector_store.search(
                query, n_results=n_results, threshold=self.threshold
            )

            if not results:
                logger.info("No relevant knowledge base results found")
                return ""

            # Format results
            formatted = "知识库相关信息：\n\n"
            for i, result in enumerate(results, 1):
                metadata = result.get("metadata", {})
                title = metadata.get("title", "未知")
                source = metadata.get("source", "未知")
                similarity = result.get("similarity", 0.0)

                formatted += f"{i}. [{title}] (相似度: {similarity:.2f})\n"
                formatted += f"   {result.get('text', '')}\n"
                formatted += f"   来源: {source}\n\n"

            return formatted

        except Exception as e:
            logger.error(f"Error retrieving from knowledge base: {e}")
            return ""

    def get_relevant_chunks(self, query: str, n_results: int = 5) -> List[dict]:
        """Get relevant chunks with metadata.

        Args:
            query: Search query
            n_results: Number of results to retrieve

        Returns:
            List of result dictionaries
        """
        try:
            return self.vector_store.search(query, n_results=n_results, threshold=self.threshold)
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
