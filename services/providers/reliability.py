"""
ارائه دهنده مکانیسم‌های پایداری (Retry/Backoff/CircuitBreaker).
"""
import time
import logging
import functools
from typing import Callable, Any
from services.providers.health import provider_health
from services.providers.exceptions import ProviderHTTPError, ProviderAuthError

logger = logging.getLogger(__name__)

def reliable_provider(provider_name: str):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not provider_health.is_healthy(provider_name):
                logger.warning("Circuit breaker active for %s.", provider_name)
                # Here, we could try to call self.fallback_get_json if it exists
                if hasattr(self, 'fallback_get_json'):
                     return self.fallback_get_json(*args, **kwargs)
                raise Exception(f"Circuit breaker active for {provider_name}")

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = func(self, *args, **kwargs)
                    provider_health.report_success(provider_name)
                    return result
                except (ProviderAuthError) as e:
                    logger.error("Permanent error for %s: %s", provider_name, e)
                    raise
                except (Exception) as e:
                    logger.warning("Attempt %s failed for %s: %s", attempt + 1, provider_name, e)
                    if attempt == max_retries - 1:
                        provider_health.report_failure(provider_name)
                        if hasattr(self, 'fallback_get_json'):
                             return self.fallback_get_json(*args, **kwargs)
                        raise
                    time.sleep(2 ** attempt) # Exponential backoff
            return None
        return wrapper
    return decorator
