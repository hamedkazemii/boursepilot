# Alert persistence
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Alert:
    symbol: str
    alert_type: str
    severity: str
    message: str
    timestamp: datetime = datetime.now()
    metadata: Optional[dict] = None
