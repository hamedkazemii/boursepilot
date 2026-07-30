import time
import logging
import functools
from typing import Callable, Any
from services.providers.exceptions import ProviderAuthError, ProviderHTTPError
from services.providers.health import provider_health

logger = logging.getLogger(__name__)

def reliable_provider(provider_name: str):
    """
    Decorator for provider methods to add retry, exponential backoff,
    and circuit breaker protection.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # 1. Circuit Breaker check
            if not provider_health.is_healthy(provider_name):
                logger.warning("Circuit breaker active for %s. Attempting fallback.", provider_name)
                if hasattr(self, 'fallback_get_json'):
                     return self.fallback_get_json(*args, **kwargs)
                raise Exception(f"Provider {provider_name} is unhealthy and no fallback available.")

            # 2. Retry Logic with Exponential Backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = func(self, *args, **kwargs)
                    provider_health.report_success(provider_name)
                    return result
                except Exception as e:
                    logger.warning("Attempt %s failed for %s: %s", attempt + 1, provider_name, e)
                    
                    # If this was the last attempt, mark failure and try fallback
                    if attempt == max_retries - 1:
                        provider_health.report_failure(provider_name)
                        if hasattr(self, 'fallback_get_json'):
                             return self.fallback_get_json(*args, **kwargs)
                        raise e
                        
                    time.sleep(2 ** attempt) # Exponential backoff
            return None
        return wrapper
    return decorator
