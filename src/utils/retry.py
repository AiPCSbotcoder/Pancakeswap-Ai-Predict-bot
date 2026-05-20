"""
Retry logic for RPC calls using tenacity.
Provides decorators and utilities for handling transient failures.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.utils.logging_setup import get_logger

logger = get_logger("retry")

F = TypeVar("F", bound=Callable[..., Any])


def rpc_retry(
    max_attempts: int = 5,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    retry_on: tuple = (ConnectionError, TimeoutError, OSError),
) -> Callable[[F], F]:
    """
    Decorator for retrying RPC calls with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time in seconds between retries.
        max_wait: Maximum wait time in seconds between retries.
        retry_on: Tuple of exception types to retry on.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: F) -> F:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, log_level=20),
            reraise=True,
        )
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, log_level=20),
            reraise=True,
        )
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


async def retry_with_fallback(
    primary_fn: Callable,
    fallback_fn: Callable,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Try primary function, fall back to secondary on failure.

    Args:
        primary_fn: Primary async callable.
        fallback_fn: Fallback async callable.

    Returns:
        Result from whichever function succeeds.
    """
    try:
        return await primary_fn(*args, **kwargs)
    except Exception as exc:
        logger.warning(
            "Primary call failed (%s), trying fallback...", exc
        )
        return await fallback_fn(*args, **kwargs)
