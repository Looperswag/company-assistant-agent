"""Error handling module for GLM API integration.

This module provides custom exception classes and error handling utilities
for interacting with the ZhipuAI GLM API.
"""

from typing import Optional


class GLMAPIError(Exception):
    """Base exception for all GLM API errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """Initialize GLM API error.

        Args:
            message: User-friendly error message
            original_error: Original exception that caused this error
        """
        self.original_error = original_error
        super().__init__(message)


class GLMConnectionError(GLMAPIError):
    """Raised when there's a connection error with the GLM API.

    This error is retryable and typically caused by network issues.
    """

    pass


class GLMTimeoutError(GLMAPIError):
    """Raised when an API request times out.

    This error is retryable and may be caused by slow network or API response.
    """

    pass


class GLMAuthenticationError(GLMAPIError):
    """Raised when API authentication fails.

    This error is NOT retryable and indicates invalid API credentials.
    """

    pass


class GLMRateLimitError(GLMAPIError):
    """Raised when the API rate limit is exceeded.

    This error requires backoff before retrying.
    """

    pass


class GLMServerError(GLMAPIError):
    """Raised when the GLM API server returns an error.

    This error is typically retryable and caused by temporary server issues.
    """

    pass


class GLMQuotaExceededError(GLMAPIError):
    """Raised when the API quota is exceeded.

    This error is NOT retryable and indicates insufficient balance.
    """

    pass


# User-friendly error message mapping
ERROR_MESSAGES = {
    "connection_error": "无法连接到AI服务，请检查网络连接后重试。",
    "timeout_error": "请求超时，请稍后重试。",
    "authentication_error": "API认证失败，请联系管理员。",
    "rate_limit_error": "请求过于频繁，请稍后再试。",
    "server_error": "AI服务暂时不可用，请稍后重试。",
    "quota_exceeded": "API配额已用完，请联系管理员充值。",
}


def classify_zhipuai_error(error: Exception) -> GLMAPIError:
    """Classify a ZhipuAI exception into a custom GLM error type.

    Args:
        error: Original exception from ZhipuAI SDK

    Returns:
        Appropriate GLMAPIError subclass
    """
    error_message = str(error).lower()
    error_type = type(error).__name__

    # Check for quota exceeded first (code 1113 or Chinese error message)
    if (
        "1113" in error_message
        or "余额不足" in error_message
        or "无可用资源包" in error_message
        or "quota" in error_message
        or "balance" in error_message
        or "insufficient" in error_message
    ):
        return GLMQuotaExceededError(
            ERROR_MESSAGES["quota_exceeded"],
            original_error=error
        )

    # Check for connection errors
    if "connection" in error_message or "network" in error_message:
        return GLMConnectionError(
            ERROR_MESSAGES["connection_error"],
            original_error=error
        )

    # Check for timeout errors
    if "timeout" in error_message or "timed out" in error_message:
        return GLMTimeoutError(
            ERROR_MESSAGES["timeout_error"],
            original_error=error
        )

    # Check for authentication errors
    if "auth" in error_message or "unauthorized" in error_message or "401" in error_message:
        return GLMAuthenticationError(
            ERROR_MESSAGES["authentication_error"],
            original_error=error
        )

    # Check for rate limit errors (but NOT quota exceeded)
    if ("rate limit" in error_message or "429" in error_message) and "1113" not in error_message:
        return GLMRateLimitError(
            ERROR_MESSAGES["rate_limit_error"],
            original_error=error
        )

    # Check for server errors
    if "500" in error_message or "502" in error_message or "503" in error_message:
        return GLMServerError(
            ERROR_MESSAGES["server_error"],
            original_error=error
        )

    # Default to server error for unclassified errors
    return GLMServerError(
        ERROR_MESSAGES["server_error"],
        original_error=error
    )


def is_retryable_error(error: GLMAPIError) -> bool:
    """Check if an error is retryable.

    Args:
        error: GLMAPIError instance

    Returns:
        True if the error should be retried
    """
    retryable_errors = (
        GLMConnectionError,
        GLMTimeoutError,
        GLMServerError,
    )
    return isinstance(error, retryable_errors)
