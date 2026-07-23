from pydantic import BaseModel
from typing import Optional, List


class FundCard(BaseModel):
    symbol: str
    name: Optional[str] = None
    score: Optional[float] = None
    rank: Optional[int] = None
    recommendation: Optional[str] = None
    reasons: List[str] = []


class MarketSummary(BaseModel):
    source: str
    universe_size: int
    sane: bool
    gap: float
