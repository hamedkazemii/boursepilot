from abc import ABC, abstractmethod
from core.alerts.models import Alert

class AlertDispatcher(ABC):
    @abstractmethod
    def dispatch(self, alert: Alert):
        pass
