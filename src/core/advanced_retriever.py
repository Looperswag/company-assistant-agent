"""Advanced RAG retriever with hybrid search and reranking."""

import math
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Tuple

import jieba
import numpy as np

from src.knowledge.vector_store import VectorStore
from src.utils.config import config
from src.utils.logger import logger


class BM25Retriever:
    """BM25 keyword-based retriever."""

    def __init__(self, documents: List[Tuple[str, dict]], k1: float = 1.5, b: float = 0.75) -> None:
        """Initialize BM25 retriever.

        Args:
            documents: List of (text, metadata) tuples
            k1: Term saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.doc_freqs = []
        self.idf = {}
        self.doc_lens = []

        self._build_index()

    def _build_index(self) -> None:
        """Build BM25 index from documents."""
        logger.info("Building BM25 index...")

        N = len(self.documents)
        avg_doc_len = 0

        for doc_text, _ in self.documents:
            tokens = list(jieba.cut(doc_text.lower()))
            self.doc_lens.append(len(tokens))
            avg_doc_len += len(tokens)

            freq = defaultdict(int)
            for token in tokens:
                freq[token] += 1
            self.doc_freqs.append(freq)

        if N > 0:
            avg_doc_len /= N

        for token in set(token for freq in self.doc_freqs for token in freq):
            df = sum(1 for freq in self.doc_freqs if token in freq)
            self.idf[token] = math.log((N - df + 0.5) / (df + 0.5) + 1)

        self.avg_doc_len = avg_doc_len
        logger.info(f"BM25 index built: {N} documents, {len(self.idf)} unique terms")

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        """Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of results with scores
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


class AdvancedRetriever:
    """Advanced RAG retriever with hybrid search and reranking."""

    def __init__(self, vector_store: Optional[VectorStore] = None) -> None:
        """Initialize the advanced retriever.

        Args:
            vector_store: Optional vector store instance
        """
        self.vector_store = vector_store or VectorStore()
        self.bm25_retriever: Optional[BM25Retriever] = None
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
                logger.info("BM25 retriever initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize BM25 retriever: {e}")

    def reciprocal_rank_fusion(
        self,
        results_list: List[List[dict]],
        k: int = 60,
        top_k: int = 10
    ) -> List[dict]:
        """Fuse multiple retrieval results using Reciprocal Rank Fusion.

        Args:
            results_list: List of result lists from different retrievers
            k: RRF constant (typically 60)
            top_k: Number of results to return

        Returns:
            Fused and ranked results
        """
        scores = defaultdict(float)
        doc_map = {}

        for results in results_list:
            for rank, result in enumerate(results):
                doc_id = result.get("metadata", {}).get("id") or hash(result.get("text", ""))

                if doc_id not in doc_map:
                    doc_map[doc_id] = result

                scores[doc_id] += 1.0 / (k + rank + 1)

        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        fused_results = []
        for doc_id, score in sorted_docs[:top_k]:
            result = doc_map[doc_id]
            result["fusion_score"] = score
            fused_results.append(result)

        return fused_results

    def expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms and related terms.

        Args:
            query: Original query

        Returns:
            List of expanded queries
        """
        expanded = [query]

        query_lower = query.lower()

        synonyms = {
            "请假": ["休假", "休年假", "调休", "事假"],
            "编码": ["代码", "编程", "开发"],
            "规范": ["标准", "准则", "规则"],
            "政策": ["规定", "制度", "条例"],
            "流程": ["步骤", "程序", "操作"],
            "公司": ["企业", "组织", "单位"],
            "员工": ["职员", "工作者", "同事"],
            "招聘": ["招聘", "录用", "入职"],
        }

        for term, syns in synonyms.items():
            if term in query_lower:
                for syn in syns:
                    if syn not in query_lower:
                        expanded.append(query.replace(term, syn))

        return expanded

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        use_expansion: bool = True,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5
    ) -> List[dict]:
        """Perform hybrid search combining vector and BM25 retrieval.

        Args:
            query: Search query
            top_k: Number of results to return
            use_expansion: Whether to use query expansion
            vector_weight: Weight for vector retrieval results
            bm25_weight: Weight for BM25 retrieval results

        Returns:
            Fused and ranked results
        """
        all_results = []

        if use_expansion:
            queries = self.expand_query(query)
        else:
            queries = [query]

        for q in queries:
            vector_results = self.vector_store.search(q, n_results=top_k)
            formatted_vector = []
            for i, res in enumerate(vector_results):
                res["type"] = "vector"
                res["score"] = res.get("similarity", 0.0) * vector_weight
                formatted_vector.append(res)
            all_results.extend(formatted_vector)

            if self.bm25_retriever:
                bm25_results = self.bm25_retriever.search(q, top_k=top_k)
                for res in bm25_results:
                    res["score"] = res.get("score", 0.0) * bm25_weight
                all_results.extend(bm25_results)

        if len(all_results) > 1:
            grouped_results = self._group_results(all_results)
            fused = self.reciprocal_rank_fusion(grouped_results, top_k=top_k)
        else:
            fused = all_results

        return fused[:top_k]

    def _group_results(self, results: List[dict]) -> List[List[dict]]:
        """Group results by retrieval type for fusion.

        Args:
            results: List of all results

        Returns:
            List of result lists grouped by type
        """
        vector_results = [r for r in results if r.get("type") == "vector"]
        bm25_results = [r for r in results if r.get("type") == "bm25"]

        grouped = []
        if vector_results:
            grouped.append(vector_results)
        if bm25_results:
            grouped.append(bm25_results)

        return grouped

    def retrieve_with_reranking(
        self,
        query: str,
        top_k: int = 10,
        rerank_top_k: int = 20,
        use_reranker: bool = False
    ) -> List[dict]:
        """Retrieve with optional reranking.

        Args:
            query: Search query
            top_k: Final number of results to return
            rerank_top_k: Number of results to retrieve before reranking
            use_reranker: Whether to use cross-encoder reranking

        Returns:
            Ranked results
        """
        results = self.hybrid_search(query, top_k=rerank_top_k)

        if use_reranker:
            results = self._rerank_results(query, results)

        return results[:top_k]

    def _rerank_results(self, query: str, results: List[dict]) -> List[dict]:
        """Rerank results using cross-encoder (placeholder).

        Args:
            query: Original query
            results: Retrieved results

        Returns:
            Reranked results
        """
        try:
            from FlagEmbedding import FlagReranker

            reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)

            pairs = [[query, result["text"]] for result in results]
            scores = reranker.compute_score(pairs)

            for i, score in enumerate(scores):
                results[i]["rerank_score"] = score

            results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            logger.info(f"Reranked {len(results)} results")

        except ImportError:
            logger.warning("FlagEmbedding not installed, skipping reranking")
        except Exception as e:
            logger.error(f"Reranking failed: {e}")

        return results

    def format_results(self, results: List[dict]) -> str:
        """Format retrieval results as context string.

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

            score_info = []
            if "similarity" in result:
                score_info.append(f"相似度: {result['similarity']:.2f}")
            if "fusion_score" in result:
                score_info.append(f"融合分数: {result['fusion_score']:.3f}")
            if "rerank_score" in result:
                score_info.append(f"重排分数: {result['rerank_score']:.3f}")

            formatted += f"{i}. [{title}] ({', '.join(score_info)})\n"
            formatted += f"   {result.get('text', '')}\n"
            formatted += f"   来源: {source}\n\n"

        return formatted
