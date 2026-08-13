import threading
from typing import Dict

class QuotaManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.failures: Dict[str, int] = {}
        self.threshold = 3 # model switch threshold

    def report_failure(self, model: str):
        with self._lock:
            self.failures[model] = self.failures.get(model, 0) + 1

    def should_fallback(self, model: str) -> bool:
        with self._lock:
            return self.failures.get(model, 0) >= self.threshold

quota_manager = QuotaManager()
