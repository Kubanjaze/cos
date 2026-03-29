"""COS rate limit manager — token bucket throttling.

Enforces per-API call limits to prevent hitting external rate limits.

Usage:
    from cos.core.ratelimit import get_limiter, rate_limited

    limiter = get_limiter("anthropic", rate=5.0, capacity=5)
    limiter.acquire()  # blocks until token available

    @rate_limited("anthropic")
    def call_api():
        ...
"""

import functools
import time
from dataclasses import dataclass, field
from typing import Callable

from cos.core.logging import get_logger

logger = get_logger("cos.core.ratelimit")


@dataclass
class RateLimiterStats:
    total_requests: int = 0
    total_waits: int = 0
    total_wait_time_s: float = 0.0


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float = 5.0, capacity: int = 5):
        """
        Args:
            rate: tokens added per second
            capacity: maximum tokens in bucket
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self.stats = RateLimiterStats()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def acquire(self) -> float:
        """Block until a token is available. Returns wait time in seconds."""
        self._refill()
        self.stats.total_requests += 1

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return 0.0

        # Need to wait for a token
        wait = (1.0 - self._tokens) / self._rate
        self.stats.total_waits += 1
        self.stats.total_wait_time_s += wait
        logger.debug(f"Rate limited: waiting {wait:.3f}s")
        time.sleep(wait)

        self._refill()
        self._tokens -= 1.0
        return wait

    def try_acquire(self) -> bool:
        """Non-blocking acquire. Returns True if token available."""
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            self.stats.total_requests += 1
            return True
        return False

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self._tokens


# ── Global registry of rate limiters ────────────────────────────────────

_limiters: dict[str, TokenBucket] = {}

DEFAULT_LIMITS = {
    "anthropic": (5.0, 5),     # 5 req/s
    "pubchem": (4.0, 4),       # ~4 req/s
    "chembl": (10.0, 10),      # generous
    "default": (10.0, 10),
}


def get_limiter(name: str, rate: float = None, capacity: int = None) -> TokenBucket:
    """Get or create a rate limiter by name."""
    if name not in _limiters:
        defaults = DEFAULT_LIMITS.get(name, DEFAULT_LIMITS["default"])
        r = rate or defaults[0]
        c = capacity or defaults[1]
        _limiters[name] = TokenBucket(rate=r, capacity=c)
        logger.info(f"Rate limiter created: {name} (rate={r}/s, capacity={c})")
    return _limiters[name]


def rate_limited(name: str) -> Callable:
    """Decorator to apply rate limiting to a function."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            limiter = get_limiter(name)
            limiter.acquire()
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def all_stats() -> dict[str, dict]:
    """Get stats for all rate limiters."""
    return {
        name: {
            "rate": limiter._rate,
            "capacity": limiter._capacity,
            "available_tokens": round(limiter.available_tokens, 1),
            "total_requests": limiter.stats.total_requests,
            "total_waits": limiter.stats.total_waits,
            "total_wait_time_s": round(limiter.stats.total_wait_time_s, 3),
        }
        for name, limiter in _limiters.items()
    }
