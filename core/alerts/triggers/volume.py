from typing import Optional
from core.alerts.models import Alert
from core.alerts.triggers.base import AlertTrigger

class VolumeAnomalyTrigger(AlertTrigger):
    def __init__(self, threshold: float):
        self.threshold = threshold

    def evaluate(self, market_data: dict) -> Optional[Alert]:
        volume = market_data.get("volume", 0)
        if volume > self.threshold:
            return Alert(
                symbol=market_data.get("symbol", "UNKNOWN"),
                alert_type="volume_anomaly",
                severity="medium",
                message=f"Volume spike detected: {volume}"
            )
        return None
