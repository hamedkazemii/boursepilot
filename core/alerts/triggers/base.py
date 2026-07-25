from abc import ABC, abstractmethod
from typing import Optional
from core.alerts.models import Alert

class AlertTrigger(ABC):
    @abstractmethod
    def evaluate(self, market_data: dict) -> Optional[Alert]:
        pass
