"""Multilingual embedding manager for RAG systems."""

import os
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.language_detector import Language, LanguageDetector, get_detector
from src.utils.config import config
from src.utils.logger import logger


class MultilingualEmbeddingManager:
    """Manages multilingual embedding models for RAG systems.

    Supports automatic language detection and model selection for optimal
    embedding generation across multiple languages.
    """

    # Model configurations
    MODELS = {
        "bge_m3": "BAAI/bge-m3",  # Primary: Supports 100+ languages
        "multilingual_mini": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # Fallback
        "chinese_large": "BAAI/bge-large-zh-v1.5",  # Chinese-specific (optional)
        "english_mini": "sentence-transformers/all-MiniLM-L6-v2",  # English-specific (optional)
    }

    def __init__(
        self,
        primary_model: str = "bge_m3",
        fallback_model: str = "multilingual_mini",
        cache_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the multilingual embedding manager.

        Args:
            primary_model: Key from MODELS dict for primary model
            fallback_model: Key from MODELS dict for fallback model
            cache_dir: Custom cache directory for models
        """
        self.language_detector = get_detector()
        self.models: dict[str, SentenceTransformer] = {}
        self.primary_model_key = primary_model
        self.fallback_model_key = fallback_model

        # Set HuggingFace mirror for faster downloads in China
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

        # Set cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        self.cache_dir = cache_dir

        # Initialize models
        self._init_models()

    def _init_models(self) -> None:
        """Initialize embedding models with fallback logic."""
        # Try to load primary model
        try:
            primary_name = self.MODELS[self.primary_model_key]
            logger.info(f"Loading primary model: {primary_name}")
            self.models["primary"] = SentenceTransformer(
                primary_name,
                cache_folder=str(self.cache_dir),
                trust_remote_code=True,
            )
            logger.info(f"Primary model loaded: {primary_name}")
        except Exception as e:
            logger.error(f"Failed to load primary model: {e}")
            # Try fallback model
            try:
                fallback_name = self.MODELS[self.fallback_model_key]
                logger.info(f"Trying fallback model: {fallback_name}")
                self.models["primary"] = SentenceTransformer(
                    fallback_name,
                    cache_folder=str(self.cache_dir),
                )
                logger.info(f"Fallback model loaded: {fallback_name}")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
                raise RuntimeError(
                    "Failed to load any embedding model. "
                    "Please check your internet connection or model cache."
                )

    def encode(
        self,
        text: str,
        detect_language: bool = True,
        normalize: bool = True,
    ) -> list[float]:
        """Encode a single text string to embedding vector.

        Args:
            text: Text to encode
            detect_language: Whether to detect language (for logging)
            normalize: Whether to normalize the embedding vector

        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for encoding")
            return []

        # Detect language for logging
        if detect_language:
            language = self.language_detector.detect(text)
            logger.debug(f"Detected language: {language.value} for text: {text[:50]}...")

        # Get model and encode
        model = self._select_model()
        embedding = model.encode(text, show_progress_bar=False)

        # Normalize if requested (helps with cosine similarity)
        if normalize:
            embedding = self._normalize(embedding)

        return embedding.tolist()

    def encode_batch(
        self,
        texts: list[str],
        detect_language: bool = True,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Encode multiple texts to embedding vectors.

        Args:
            texts: List of texts to encode
            detect_language: Whether to detect languages
            normalize: Whether to normalize embedding vectors
            batch_size: Batch size for encoding

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Log language distribution
        if detect_language:
            languages = self.language_detector.detect_batch(texts)
            lang_counts = {}
            for lang in languages:
                lang_counts[lang.value] = lang_counts.get(lang.value, 0) + 1
            logger.info(f"Encoding {len(texts)} texts with language distribution: {lang_counts}")

        # Get model and encode batch
        model = self._select_model()
        embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True)

        # Normalize if requested
        if normalize:
            embeddings = np.array([self._normalize(emb) for emb in embeddings])

        return embeddings.tolist()

    def _select_model(self, language: Optional[Language] = None) -> SentenceTransformer:
        """Select the appropriate model for the given language.

        Args:
            language: Target language (optional)

        Returns:
            Selected SentenceTransformer model
        """
        # Strategy: Use primary multilingual model for all languages
        # This ensures consistency and avoids embedding space mismatch
        return self.models.get("primary")

    def _normalize(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding vector to unit length.

        Args:
            embedding: Input embedding vector

        Returns:
            Normalized embedding vector
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        model = self._select_model()
        return model.get_sentence_embedding_dimension()

    def get_model_name(self) -> str:
        """Get the name of the currently active model.

        Returns:
            Model name/identifier
        """
        model = self._select_model()
        # Try to get model name from various attributes
        if hasattr(model, "_model_module_name"):
            return model._model_module_name
        return self.MODELS.get(self.primary_model_key, "unknown")


# Singleton instance for easy import
_manager: Optional[MultilingualEmbeddingManager] = None


def get_embedding_manager() -> MultilingualEmbeddingManager:
    """Get the singleton embedding manager instance.

    Returns:
        MultilingualEmbeddingManager instance
    """
    global _manager
    if _manager is None:
        _manager = MultilingualEmbeddingManager()
    return _manager
