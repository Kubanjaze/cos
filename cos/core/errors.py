"""COS error handling + retry system.

Provides error hierarchy, retry decorator, and safe execution wrapper.

Usage:
    from cos.core.errors import retry, safe_execute, TransientError, PermanentError

    @retry(max_attempts=3, backoff_base=0.1)
    def call_api():
        ...

    result = safe_execute(risky_function, default="fallback")
"""

import functools
import time
from typing import Callable, Optional, Type

from cos.core.logging import get_logger

logger = get_logger("cos.core.errors")


# ── Error Hierarchy ─────────────────────────────────────────────────────

class COSError(Exception):
    """Base error for all COS operations."""
    pass


class TransientError(COSError):
    """Retryable error — network timeouts, rate limits, temporary failures."""
    pass


class PermanentError(COSError):
    """Non-retryable error — invalid input, auth failure, missing resource."""
    pass


class RateLimitError(TransientError):
    """API rate limit hit — HTTP 429."""
    pass


class ValidationError(PermanentError):
    """Input validation failure."""
    pass


# ── HTTP status → error mapping ─────────────────────────────────────────

def classify_http_error(status_code: int, message: str = "") -> COSError:
    """Map HTTP status codes to COS error types."""
    if status_code == 429:
        return RateLimitError(f"Rate limited (429): {message}")
    elif status_code in (500, 502, 503, 504):
        return TransientError(f"Server error ({status_code}): {message}")
    elif status_code in (400, 422):
        return ValidationError(f"Bad request ({status_code}): {message}")
    elif status_code in (401, 403):
        return PermanentError(f"Auth error ({status_code}): {message}")
    elif status_code == 404:
        return PermanentError(f"Not found (404): {message}")
    else:
        return COSError(f"HTTP {status_code}: {message}")


# ── Retry Decorator ─────────────────────────────────────────────────────

def retry(
    max_attempts: int = 3,
    backoff_base: float = 0.1,
    max_delay: float = 60.0,
    retryable: tuple[Type[Exception], ...] = (TransientError,),
):
    """Decorator for automatic retry with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including first try)
        backoff_base: Base delay in seconds (doubles each attempt)
        max_delay: Maximum delay cap in seconds
        retryable: Tuple of exception types that trigger retry
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except retryable as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(backoff_base * (2 ** attempt), max_delay)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {fn.__name__}: {e} (waiting {delay:.2f}s)",
                            extra={"cost": 0},
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {fn.__name__}: {e}",
                        )
                except Exception as e:
                    # Non-retryable exception — fail immediately
                    logger.error(f"Non-retryable error in {fn.__name__}: {e}")
                    raise
            raise last_exception
        return wrapper
    return decorator


# ── Safe Execute ────────────────────────────────────────────────────────

def safe_execute(fn: Callable, *args, default=None, **kwargs):
    """Execute a function, returning default on any failure."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"safe_execute caught {type(e).__name__} in {fn.__name__}: {e}")
        return default
