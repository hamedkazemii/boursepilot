"""
Sync V1 Worker — retry engine with exponential backoff.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryPolicy:
    """Configurable retry policy with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier

    def next_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for the given attempt."""
        if attempt <= 0:
            return 0.0
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, exception: Optional[Exception] = None) -> bool:
        """Decide whether to retry based on attempt count and exception type."""
        if attempt >= self.max_retries:
            return False
        return True

    def execute_with_retry(
        self,
        func: Callable[[], T],
        *,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Callable to execute.
            on_retry: Optional callback called on each retry with (attempt, exception).

        Returns:
            Result of func().

        Raises:
            Last exception after exhausting retries.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except Exception as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    delay = self.next_delay(attempt)
                    logger.warning(
                        "Attempt %d/%d failed: %s — retrying in %.1fs",
                        attempt,
                        self.max_retries,
                        exc,
                        delay,
                    )
                    if on_retry is not None:
                        on_retry(attempt, exc)
                    time.sleep(delay)
                else:
                    logger.error(
                        "Attempt %d/%d failed: %s — no more retries",
                        attempt,
                        self.max_retries,
                        exc,
                    )

        raise last_exception  # type: ignore[misc]
