import threading
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ProviderHealth:
    def __init__(self):
        self._lock = threading.Lock()
        self.stats: Dict[str, Dict] = {}

    def report_success(self, provider_name: str):
        with self._lock:
            if provider_name not in self.stats:
                self.stats[provider_name] = {"failures": 0, "open": False}
            self.stats[provider_name]["failures"] = 0
            self.stats[provider_name]["open"] = False
        logger.debug("Provider %s is healthy.", provider_name)

    def report_failure(self, provider_name: str):
        with self._lock:
            if provider_name not in self.stats:
                self.stats[provider_name] = {"failures": 0, "open": False}
            
            self.stats[provider_name]["failures"] += 1
            # Threshold: 5 failures to open circuit breaker
            if self.stats[provider_name]["failures"] >= 5:
                self.stats[provider_name]["open"] = True
                logger.error("Provider %s circuit breaker opened.", provider_name)

    def is_healthy(self, provider_name: str) -> bool:
        with self._lock:
            return not self.stats.get(provider_name, {}).get("open", False)

provider_health = ProviderHealth()
