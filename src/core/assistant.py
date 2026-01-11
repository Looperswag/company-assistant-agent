"""Main assistant orchestrator."""

from typing import List, Optional

from src.core.classifier import QueryClassifier, QueryType
from src.core.hybrid_retriever import HybridRetriever
from src.core.llm_client import LLMClient
from src.core.retriever import KnowledgeRetriever
from src.core.safety_filter import SafetyFilter
from src.core.searcher import WebSearcher
from src.utils.config import config
from src.utils.logger import logger


class Assistant:
    """Main assistant class that orchestrates all components."""

    def __init__(self, use_hybrid_retriever: bool = True) -> None:
        """Initialize the assistant.

        Args:
            use_hybrid_retriever: Whether to use the new HybridRetriever (default: True)
        """
        self.classifier = QueryClassifier()
        self.safety_filter = SafetyFilter() if config.safety_filter_enabled else None

        # Use hybrid retriever for multilingual support
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
        self.conversation_history: List[dict] = []

    def process_query(self, query: str, use_history: bool = True) -> str:
        """Process a user query and generate a response.

        Args:
            query: User query string
            use_history: Whether to use conversation history

        Returns:
            Assistant response
        """
        # Safety check
        if self.safety_filter:
            is_safe, reason = self.safety_filter.check(query)
            if not is_safe:
                return f"Sorry, I cannot process this request. {reason}"

        # Classify query
        query_type = self.classifier.classify(query)
        logger.info(f"Query classified as: {query_type.value}")

        # Route based on query type
        if query_type == QueryType.HARMFUL:
            return "Sorry, I cannot process this request. Please ensure your query complies with company policies and ethical guidelines."

        context = ""
        needs_clarification = False

        if query_type == QueryType.COMPANY_INTERNAL:
            # Retrieve from knowledge base using hybrid retriever
            if self.hybrid_retriever:
                results = self.hybrid_retriever.retrieve(query, top_k=config.max_results)
                context = self.hybrid_retriever.format_results(results) if results else ""
            else:
                context = self.retriever.retrieve(query)

            if not context:
                # Fallback to web search if no KB results
                logger.info("No KB results, trying web search")
                search_results = self.searcher.search(query)
                if search_results:
                    context = self.searcher.format_search_results(search_results)
                else:
                    logger.info("No search results either, using general knowledge")
        elif query_type == QueryType.EXTERNAL_KNOWLEDGE:
            # Search the web
            search_results = self.searcher.search(query)
            if search_results:
                context = self.searcher.format_search_results(search_results)
            else:
                logger.info("No search results, using general knowledge")
        elif query_type == QueryType.AMBIGUOUS:
            # Try both knowledge base and web search
            if self.hybrid_retriever:
                results = self.hybrid_retriever.retrieve(query, top_k=5)
                context = self.hybrid_retriever.format_results(results) if results else ""
            else:
                kb_context = self.retriever.retrieve(query)
                context = kb_context if kb_context else ""

            if not context:
                search_results = self.searcher.search(query)
                if search_results:
                    context = self.searcher.format_search_results(search_results)
                else:
                    # Ask for clarification
                    needs_clarification = True

        # Generate response
        if needs_clarification:
            response = self._ask_clarification(query)
        else:
            messages = self.conversation_history if use_history and self.conversation_history else []
            try:
                response = self.llm_client.generate_with_context(
                    query=query, context=context if context else None, conversation_history=messages
                )
            except Exception as e:
                # LLM call failed - try to provide a response based on context
                logger.error(f"LLM generation failed: {e}")
                if context:
                    # If we have context, try to extract and format the answer
                    response = self._format_context_response(query, context)
                else:
                    response = f"Sorry, I am currently unable to generate a response. This may be due to insufficient API balance or network issues.\n\nError: {str(e)}\n\nPlease try again later or contact the administrator."

        # Update conversation history
        if use_history:
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": response})
            # Keep only last 10 exchanges to manage context length
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

        return response

    def _format_context_response(self, query: str, context: str) -> str:
        """Format a response based on context when LLM is unavailable.

        Args:
            query: Original query
            context: Retrieved context from knowledge base

        Returns:
            Formatted response
        """
        # Clean up the context and present it directly
        response = f"Based on the knowledge base, I found the following relevant information:\n\n{context}\n\n"
        response += "Note: Due to temporary API service unavailability, the above is the raw content retrieved directly from the knowledge base."
        return response

    def _ask_clarification(self, query: str) -> str:
        """Ask user for clarification on ambiguous queries.

        Args:
            query: Original query

        Returns:
            Clarification request message
        """
        return f"""Your question "{query}" may relate to company internal information or external knowledge.

Please let me know:
1. If you want to know about company policies, procedures, or regulations, please specify
2. If you want to know about general knowledge or latest information, I can search the web for you

Alternatively, you can rephrase your question to be more specific."""

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_history(self) -> List[dict]:
        """Get conversation history.

        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()
