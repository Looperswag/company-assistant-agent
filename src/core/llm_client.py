"""LLM client for ZhipuAI GLM-4 Flash."""

import time
from typing import List, Optional

from httpx import Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from zhipuai import ZhipuAI
from zhipuai.core._errors import APIStatusError

from src.utils.config import config
from src.utils.error_handler import (
    GLMAPIError,
    classify_zhipuai_error,
    is_retryable_error,
)
from src.utils.logger import logger


class LLMClient:
    """Client for interacting with ZhipuAI GLM-4 Flash API."""

    def __init__(self) -> None:
        """Initialize the LLM client."""
        self.client = ZhipuAI(
            api_key=config.zhipuai_api_key,
            base_url=config.zhipuai_base_url,
            timeout=Timeout(
                timeout=config.glm_api_timeout,
                connect=config.glm_connection_timeout
            ),
        )
        self.model = config.zhipuai_model
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.stream_enabled = config.stream_enabled
        self.thinking_enabled = config.thinking_enabled
        self.max_retries = config.glm_max_retries
        self.connection_timeout = config.glm_connection_timeout

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

        Raises:
            GLMAPIError: If API request fails after retries
        """
        stream = stream if stream is not None else self.stream_enabled
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        try:
            if stream:
                return self._generate_streaming_with_retry(messages, temperature, max_tokens)
            else:
                return self._generate_non_streaming_with_retry(messages, temperature, max_tokens)
        except GLMAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating response: {e}")
            raise classify_zhipuai_error(e)

    def _generate_non_streaming_with_retry(
        self, messages: List[dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate response without streaming with retry logic.

        Args:
            messages: List of message dictionaries
            temperature: Temperature setting
            max_tokens: Max tokens

        Returns:
            Generated response text

        Raises:
            GLMAPIError: If API request fails after retries
        """

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(GLMAPIError),
            before_sleep=before_sleep_log(logger, logger.level),
            reraise=True,
        )
        def _attempt() -> str:
            try:
                return self._generate_non_streaming(messages, temperature, max_tokens)
            except APIStatusError as e:
                classified_error = classify_zhipuai_error(e)
                if is_retryable_error(classified_error):
                    logger.warning(f"Retryable error: {classified_error}, will retry...")
                    raise classified_error
                else:
                    logger.error(f"Non-retryable error: {classified_error}")
                    raise classified_error
            except Exception as e:
                raise classify_zhipuai_error(e)

        return _attempt()

    def _generate_streaming_with_retry(
        self, messages: List[dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate response with streaming with retry logic.

        Args:
            messages: List of message dictionaries
            temperature: Temperature setting
            max_tokens: Max tokens

        Returns:
            Generated response text

        Raises:
            GLMAPIError: If API request fails after retries
        """

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(GLMAPIError),
            before_sleep=before_sleep_log(logger, logger.level),
            reraise=True,
        )
        def _attempt() -> str:
            try:
                return self._generate_streaming(messages, temperature, max_tokens)
            except APIStatusError as e:
                classified_error = classify_zhipuai_error(e)
                if is_retryable_error(classified_error):
                    logger.warning(f"Retryable error: {classified_error}, will retry...")
                    raise classified_error
                else:
                    logger.error(f"Non-retryable error: {classified_error}")
                    raise classified_error
            except Exception as e:
                raise classify_zhipuai_error(e)

        return _attempt()

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

        Raises:
            APIStatusError: If API request fails
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

        try:
            logger.debug(f"Sending non-streaming request to {self.model}")
            response = self.client.chat.completions.create(**request_params)
            logger.debug(f"Received response from {self.model}")

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            return ""
        except APIStatusError as e:
            logger.error(f"API status error in non-streaming: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in non-streaming: {e}")
            raise APIStatusError(message=str(e), body=None, response=None)

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

        Raises:
            APIStatusError: If API request fails
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

        try:
            logger.debug(f"Sending streaming request to {self.model}")
            response = self.client.chat.completions.create(**request_params)

            full_content = ""
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        full_content += delta.content

            logger.debug(f"Received {chunk_count} chunks from {self.model}")
            return full_content
        except APIStatusError as e:
            logger.error(f"API status error in streaming: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in streaming: {e}")
            raise APIStatusError(message=str(e), body=None, response=None)

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
        base_prompt = """你是小美，ZURU Melon 公司的专业智能客服助手。你可以回答有关公司政策、流程和一般知识的问题。

**重要规则:**
1. **仅基于提供的上下文信息回答** - 不要使用上下文之外的信息
2. **关键术语映射:**
   - "客户投诉" → 使用 helpdesk@zurumelon.com
   - "内部投诉" → 使用 hr@zurumelon.com
   - 当用户询问"客户投诉"时，仅回答关于**客户投诉**的内容，忽略内部投诉
3. 如果上下文包含多个选项，根据用户问题选择最相关的一个
4. 提供准确、简洁和有用的回答
5. 保持专业且友好的语气

自我介绍时，请说："你好！我是小美，ZURU Melon 的专业公司助理。"
"""

        if context:
            base_prompt += f"\n\n=== Knowledge Base Search Results ===\n{context}\n=== End of Search Results ===\n\nPlease answer the question **strictly based on the knowledge base search results above**. Carefully find the most relevant sections."
        else:
            base_prompt += "\n\nNo specific context information provided. Please use your general knowledge to answer the question."

        return base_prompt

    def health_check(self) -> bool:
        """Verify API connectivity and credentials.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            logger.debug("Performing GLM API health check...")
            # Send a minimal test request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            is_healthy = bool(response.choices and len(response.choices) > 0)
            logger.debug(f"Health check result: {'healthy' if is_healthy else 'unhealthy'}")
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
