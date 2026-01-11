"""LLM client for ZhipuAI GLM-4 Flash."""

from typing import List, Optional

from zhipuai import ZhipuAI

from src.utils.config import config
from src.utils.logger import logger


class LLMClient:
    """Client for interacting with ZhipuAI GLM-4 Flash API."""

    def __init__(self) -> None:
        """Initialize the LLM client."""
        self.client = ZhipuAI(api_key=config.zhipuai_api_key)
        self.model = config.zhipuai_model
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.stream_enabled = config.stream_enabled
        self.thinking_enabled = config.thinking_enabled

    def generate_response(
        self,
        messages: List[dict],
        stream: Optional[bool] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to use streaming (overrides config)
            temperature: Temperature setting (overrides config)
            max_tokens: Max tokens (overrides config)

        Returns:
            Generated response text
        """
        stream = stream if stream is not None else self.stream_enabled
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        try:
            if stream:
                return self._generate_streaming(messages, temperature, max_tokens)
            else:
                return self._generate_non_streaming(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def _generate_non_streaming(
        self, messages: List[dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate response without streaming.

        Args:
            messages: List of message dictionaries
            temperature: Temperature setting
            max_tokens: Max tokens

        Returns:
            Generated response text
        """
        # Build request parameters
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add thinking parameter if enabled
        if self.thinking_enabled:
            request_params["thinking"] = {"type": "enabled"}

        response = self.client.chat.completions.create(**request_params)

        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        return ""

    def _generate_streaming(
        self, messages: List[dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate response with streaming.

        Args:
            messages: List of message dictionaries
            temperature: Temperature setting
            max_tokens: Max tokens

        Returns:
            Generated response text
        """
        # Build request parameters
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        # Add thinking parameter if enabled
        if self.thinking_enabled:
            request_params["thinking"] = {"type": "enabled"}

        response = self.client.chat.completions.create(**request_params)

        full_content = ""
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_content += delta.content

        return full_content

    def generate_with_context(
        self,
        query: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """Generate response with context and conversation history.

        Args:
            query: User query
            context: Additional context (e.g., from knowledge base)
            conversation_history: Previous conversation messages

        Returns:
            Generated response
        """
        messages: List[dict] = []

        # System message
        system_prompt = self._build_system_prompt(context)
        messages.append({"role": "system", "content": system_prompt})

        # Conversation history
        if conversation_history:
            messages.extend(conversation_history)

        # Current query
        messages.append({"role": "user", "content": query})

        return self.generate_response(messages)

    def _build_system_prompt(self, context: Optional[str] = None) -> str:
        """Build system prompt with optional context.

        Args:
            context: Optional context from knowledge base

        Returns:
            System prompt string
        """
        base_prompt = """You are a professional company assistant that can answer questions about company policies, procedures, and general knowledge.

**Important Rules:**
1. **Answer based ONLY on the provided context information** - do not use information outside of the context
2. **Key Term Mapping:**
   - "Client Complaints" → use helpdesk@zurumelon.com
   - "Internal Complaints" → use hr@zurumelon.com
   - When users ask about "client complaints", only answer regarding **Client Complaints**, ignore Internal Complaints
3. If the context contains multiple options, select the most relevant one based on the user's question
4. Provide accurate, concise, and helpful responses
5. Maintain a professional and friendly tone
"""

        if context:
            base_prompt += f"\n\n=== Knowledge Base Search Results ===\n{context}\n=== End of Search Results ===\n\nPlease answer the question **strictly based on the knowledge base search results above**. Carefully find the most relevant sections."
        else:
            base_prompt += "\n\nNo specific context information provided. Please use your general knowledge to answer the question."

        return base_prompt
