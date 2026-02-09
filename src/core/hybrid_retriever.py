"""Hybrid retriever combining vector search and BM25 for multilingual RAG."""

import math
from collections import defaultdict
from typing import List, Optional

import jieba

from src.core.language_detector import Language, get_detector
from src.knowledge.vector_store import VectorStore
from src.utils.config import config
from src.utils.logger import logger


class BM25Retriever:
    """BM25 keyword-based retriever for multilingual document search."""

    def __init__(
        self,
        documents: List[tuple[str, dict]],
        k1: float = 1.5,
        b: float = 0.75
    ) -> None:
        """Initialize BM25 retriever.

        Args:
            documents: List of (text, metadata) tuples
            k1: Term saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.doc_freqs: List[dict] = []
        self.idf: dict = {}
        self.doc_lens: List[int] = []

        self._build_index()

    def _build_index(self) -> None:
        """Build BM25 index from documents."""
        logger.info("Building BM25 index...")

        n = len(self.documents)
        total_doc_len = 0

        for doc_text, _ in self.documents:
            tokens = list(jieba.cut(doc_text.lower()))
            self.doc_lens.append(len(tokens))
            total_doc_len += len(tokens)

            freq: dict = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1
            self.doc_freqs.append(freq)

        avg_doc_len = total_doc_len / n if n > 0 else 0

        # Calculate IDF for all unique tokens
        all_tokens = set()
        for freq in self.doc_freqs:
            all_tokens.update(freq.keys())

        for token in all_tokens:
            df = sum(1 for freq in self.doc_freqs if token in freq)
            self.idf[token] = math.log((n - df + 0.5) / (df + 0.5) + 1)

        self.avg_doc_len = avg_doc_len
        logger.info(f"BM25 index built: {n} documents, {len(self.idf)} unique terms")

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        """Search documents using BM25 algorithm.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of results with scores and metadata
        """
        query_tokens = list(jieba.cut(query.lower()))
        scores = []

        for idx, (doc_text, metadata) in enumerate(self.documents):
            score = 0.0
            doc_freq = self.doc_freqs[idx]
            doc_len = self.doc_lens[idx]

            for token in query_tokens:
                if token not in doc_freq:
                    continue

                tf = doc_freq[token]
                idf = self.idf.get(token, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                score += idf * (numerator / denominator)

            if score > 0:
                scores.append({
                    "text": doc_text,
                    "metadata": metadata,
                    "score": score,
                    "type": "bm25"
                })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]


class HybridRetriever:
    """Enterprise-grade hybrid retriever with vector + BM25 fusion.

    Features:
    - Automatic language detection
    - Query expansion with multilingual synonyms
    - Hybrid search combining vector and BM25
    - Reciprocal Rank Fusion (RRF) for result merging
    - Adaptive threshold filtering
    """

    # Multilingual synonym dictionaries for query expansion
    SYNONYMS = {
        # Chinese synonyms
        "投诉": ["抱怨", "不满", "申诉", "反馈问题"],
        "邮箱": ["邮件", "电子邮件", "email", "联系地址"],
        "客户": ["顾客", "用户"],
        "申请": ["请求", "寻求", "联系"],
        "流程": ["步骤", "程序", "操作"],
        "请假": ["休假", "休年假", "调休", "事假"],
        "政策": ["规定", "制度", "条例"],
        "编码": ["代码", "编程", "开发"],
        # English synonyms
        "complaint": ["issue", "problem", "grievance", "feedback"],
        "email": ["mail", "contact", "address"],
        "customer": ["client", "user"],
        "process": ["procedure", "workflow", "steps"],
        "leave": ["vacation", "time off", "holiday"],
        "policy": ["rule", "guideline", "standard"],
    }

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        rrf_k: int = 60,
    ) -> None:
        """Initialize the hybrid retriever.

        Args:
            vector_store: Vector store instance (creates new if None)
            vector_weight: Weight for vector search results (0-1)
            bm25_weight: Weight for BM25 results (0-1)
            rrf_k: RRF constant for fusion (typically 60)
        """
        self.vector_store = vector_store or VectorStore()
        self.language_detector = get_detector()
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k

        # Initialize BM25 index
        self._init_bm25()

    def _init_bm25(self) -> None:
        """Initialize BM25 retriever from vector store documents."""
        try:
            documents = []
            results = self.vector_store.collection.get(include=["documents", "metadatas"])

            if results["documents"]:
                for doc, meta in zip(results["documents"], results["metadatas"]):
                    documents.append((doc, meta))

                self.bm25_retriever = BM25Retriever(documents)
                logger.info("BM25 index initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize BM25: {e}")

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        strategy: str = "auto",
        min_similarity: float = 0.25,
        use_expansion: bool = True,
    ) -> List[dict]:
        """Perform intelligent hybrid retrieval.

        Args:
            query: Search query text
            top_k: Number of results to return
            strategy: Retrieval strategy ("auto", "vector", "bm25", "hybrid")
            min_similarity: Minimum similarity threshold
            use_expansion: Whether to use query expansion

        Returns:
            List of retrieved results with metadata
        """
        # Detect language
        language = self.language_detector.detect(query)
        logger.info(f"Query language detected: {language.value}")

        # Select strategy
        if strategy == "auto":
            strategy = self._select_strategy(query, language)
        logger.info(f"Retrieval strategy: {strategy}")

        # Expand query if enabled
        queries = [query]
        if use_expansion:
            queries = self.expand_query(query, language)
            if len(queries) > 1:
                logger.info(f"Query expanded to {len(queries)} variants")

        # Execute retrieval based on strategy
        if strategy == "vector":
            results = self._vector_search(queries, top_k * 2)
        elif strategy == "bm25":
            results = self._bm25_search(queries, top_k * 2)
        else:  # hybrid
            results = self._hybrid_search(queries, top_k * 2)

        # Filter by threshold
        filtered_results = [r for r in results if r.get("similarity", 0) >= min_similarity]

        # Adaptive threshold: if too few results, lower threshold
        if len(filtered_results) < 3 and min_similarity > 0.15:
            logger.warning(
                f"Only {len(filtered_results)} results above {min_similarity}, "
                f"lowering threshold to 0.15"
            )
            filtered_results = [r for r in results if r.get("similarity", 0) >= 0.15]

        # Sort by similarity and return top_k
        filtered_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        final_results = filtered_results[:top_k]

        # Log results
        if final_results:
            top_score = final_results[0].get("similarity", 0)
            logger.info(
                f"Retrieved {len(final_results)} results, top similarity: {top_score:.3f}"
            )
        else:
            logger.warning("No results retrieved")

        return final_results

    def _select_strategy(self, query: str, language: Language) -> str:
        """Automatically select the best retrieval strategy.

        Args:
            query: Search query
            language: Detected language

        Returns:
            Strategy name
        """
        # CRITICAL: Chinese queries against English documents MUST use vector search
        # BM25 does keyword matching and cannot bridge language gaps
        if language == Language.CHINESE:
            return "vector"  # Pure vector for cross-language retrieval

        # Short queries favor BM25 (keyword matching) - only for English
        word_count = len(query.split())
        if word_count < 5 and language == Language.ENGLISH:
            return "bm25"

        # Queries with specific entities favor BM25 - only for English
        if ("@" in query or "http" in query) and language == Language.ENGLISH:
            return "bm25"

        # Default to hybrid for English and other languages
        return "hybrid"

    def _vector_search(self, queries: List[str], top_k: int) -> List[dict]:
        """Perform pure vector search.

        Args:
            queries: List of query strings
            top_k: Number of results

        Returns:
            List of results
        """
        all_results = []

        for query in queries:
            results = self.vector_store.search(query, n_results=top_k, threshold=None)
            for r in results:
                r["type"] = "vector"
                r["score"] = r.get("similarity", 0) * self.vector_weight
            all_results.extend(results)

        # Deduplicate and sort
        unique_results = self._deduplicate_results(all_results)
        unique_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return unique_results[:top_k]

    def _bm25_search(self, queries: List[str], top_k: int) -> List[dict]:
        """Perform pure BM25 search.

        Args:
            queries: List of query strings
            top_k: Number of results

        Returns:
            List of results
        """
        if not self.bm25_retriever:
            logger.warning("BM25 not available, falling back to vector search")
            return self._vector_search(queries, top_k)

        all_results = []

        for query in queries:
            results = self.bm25_retriever.search(query, top_k=top_k)
            for r in results:
                r["type"] = "bm25"
                # Normalize BM25 score to 0-1 range
                r["score"] = r.get("score", 0)
                r["similarity"] = r["score"]  # For consistency
            all_results.extend(results)

        # Normalize scores
        max_score = max([r.get("score", 0) for r in all_results], default=1)
        if max_score > 0:
            for r in all_results:
                r["score"] = (r.get("score", 0) / max_score) * self.bm25_weight

        # Deduplicate and sort
        unique_results = self._deduplicate_results(all_results)
        unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return unique_results[:top_k]

    def _hybrid_search(self, queries: List[str], top_k: int) -> List[dict]:
        """Perform hybrid search with RRF fusion.

        Args:
            queries: List of query strings
            top_k: Number of results

        Returns:
            List of fused results
        """
        # Get results from both retrievers
        vector_results = self._vector_search(queries, top_k)
        bm25_results = self._bm25_search(queries, top_k)

        # RRF fusion
        fused = self._reciprocal_rank_fusion(
            [vector_results, bm25_results],
            top_k=top_k,
        )

        return fused

    def _reciprocal_rank_fusion(
        self,
        results_list: List[List[dict]],
        top_k: int = 10,
    ) -> List[dict]:
        """Fuse multiple retrieval result lists using RRF.

        Args:
            results_list: List of result lists from different retrievers
            top_k: Number of results to return

        Returns:
            Fused and ranked results
        """
        scores = defaultdict(float)
        doc_map: dict = {}

        for results in results_list:
            for rank, result in enumerate(results):
                # Use document text hash as ID
                doc_id = hash(result.get("text", ""))

                if doc_id not in doc_map:
                    doc_map[doc_id] = result

                # RRF formula: 1 / (k + rank + 1)
                scores[doc_id] += 1.0 / (self.rrf_k + rank + 1)

        # Sort by fusion score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        fused_results = []
        for doc_id, score in sorted_docs[:top_k]:
            result = doc_map[doc_id].copy()
            result["fusion_score"] = score
            # Keep original similarity, add fusion_score separately
            # The original similarity is already in result["similarity"]
            result["strategy"] = "hybrid"
            fused_results.append(result)

        return fused_results

    def _deduplicate_results(self, results: List[dict]) -> List[dict]:
        """Remove duplicate results based on document text.

        Args:
            results: List of results

        Returns:
            Deduplicated results
        """
        seen = set()
        unique_results = []

        for result in results:
            text = result.get("text", "")
            text_hash = hash(text)

            if text_hash not in seen:
                seen.add(text_hash)
                unique_results.append(result)

        return unique_results

    def expand_query(self, query: str, language: Language) -> List[str]:
        """Expand query with multilingual synonyms.

        Args:
            query: Original query
            language: Detected language

        Returns:
            List of expanded queries
        """
        expanded = [query]
        query_lower = query.lower()

        # Find applicable synonyms
        for term, syns in self.SYNONYMS.items():
            if term in query_lower:
                for syn in syns:
                    if syn.lower() not in query_lower:
                        # Replace term with synonym
                        expanded_query = query.replace(term, syn, 1)
                        expanded.append(expanded_query)

        return expanded

    def format_results(self, results: List[dict]) -> str:
        """Format retrieval results for context.

        Args:
            results: List of retrieval results

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        formatted = "知识库检索结果：\n\n"

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            title = metadata.get("title", "未知")
            source = metadata.get("source", "未知")
            similarity = result.get("similarity", 0)
            strategy = result.get("strategy", "unknown")

            formatted += f"{i}. [{title}] (相似度: {similarity:.2f}, 策略: {strategy})\n"
            formatted += f"   {result.get('text', '')}\n"
            formatted += f"   来源: {source}\n\n"

        return formatted
