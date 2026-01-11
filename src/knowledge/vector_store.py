"""Vector store for knowledge base embeddings."""

import hashlib
import os
from pathlib import Path
from typing import List, Optional, Tuple

import chromadb
from chromadb.config import Settings

from src.core.multilingual_embedding import get_embedding_manager
from src.utils.config import config
from src.utils.logger import logger


class VectorStore:
    """Vector store for semantic search over knowledge base with multilingual support."""

    def __init__(self) -> None:
        """Initialize the vector store."""
        self.collection_name = "knowledge_base"

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(config.vector_db_path),
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Created new collection: {self.collection_name}")

        # Initialize multilingual embedding manager
        self.embedding_manager = get_embedding_manager()
        logger.info(f"Using embedding model: {self.embedding_manager.get_model_name()}")

    @property
    def embedding_model(self):
        """Compatibility property for backward compatibility."""
        return self.embedding_manager

    def add_documents(self, chunks: List[Tuple[str, dict]]) -> None:
        """Add documents to the vector store.

        Args:
            chunks: List of tuples containing (text, metadata)
        """
        if not chunks:
            logger.warning("No chunks to add")
            return

        texts = [chunk[0] for chunk in chunks]
        metadatas = [chunk[1] for chunk in chunks]

        # Generate embeddings using multilingual manager
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_manager.encode_batch(texts)

        # Generate IDs based on content hash to ensure uniqueness
        ids = [
            hashlib.md5(f"{meta['source']}_{meta['chunk_index']}_{text[:100]}".encode()).hexdigest()
            for text, meta in chunks
        ]

        # encode_batch already returns list format
        embeddings_list = embeddings

        # Add to collection
        try:
            self.collection.add(
                embeddings=embeddings_list,
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(f"Added {len(chunks)} chunks to vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def search(
        self, query: str, n_results: int = 5, threshold: Optional[float] = None
    ) -> List[dict]:
        """Search for similar documents.

        Args:
            query: Search query
            n_results: Number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of search results with text, metadata, and distance
        """
        # Generate query embedding using multilingual manager
        query_embedding = self.embedding_manager.encode(query)

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        # Format results
        formatted_results: List[dict] = []
        all_similarities = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                similarity = 1.0 - distance  # Convert distance to similarity
                all_similarities.append(similarity)

                # Apply threshold filter
                if threshold is not None and similarity < threshold:
                    logger.debug(f"Result {i+1} filtered out: similarity={similarity:.3f} < threshold={threshold}")
                    continue

                formatted_results.append(
                    {
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": similarity,
                        "distance": distance,
                    }
                )

        # Log detailed info for debugging
        if all_similarities:
            logger.info(f"Found {len(all_similarities)} raw results, similarities: {[f'{s:.3f}' for s in all_similarities]}")
        if threshold is not None:
            logger.info(f"Threshold filter ({threshold}): {len(all_similarities)} -> {len(formatted_results)} results")
        logger.info(f"Found {len(formatted_results)} results for query")
        return formatted_results

    def clear(self) -> None:
        """Clear all documents from the vector store."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Cleared vector store")
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")

    def get_collection_size(self) -> int:
        """Get the number of documents in the collection.

        Returns:
            Number of documents
        """
        try:
            count = self.collection.count()
            return count
        except Exception:
            return 0
