from typing import List
from core.alerts.models import Alert
from core.alerts.triggers.base import AlertTrigger

class AlertEngine:
    def __init__(self):
        self.triggers: List[AlertTrigger] = []

    def register_trigger(self, trigger: AlertTrigger):
        self.triggers.append(trigger)

    def evaluate(self, market_data: dict) -> List[Alert]:
        alerts = []
        for trigger in self.triggers:
            alert = trigger.evaluate(market_data)
            if alert:
                alerts.append(alert)
        return alerts
