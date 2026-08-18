from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

def _now_iso() -> str: return datetime.now(timezone.utc).isoformat()
def _sha256_hex(data: bytes): return hashlib.sha256(data).hexdigest()

@dataclass(frozen=True)
class FundSnapshot:
    symbol: str; name: str; ins_code: str; isin: Optional[str]=None; sector: Optional[str]=None; fund_type: Optional[str]=None
    last_price: Optional[float]=None; close_price: Optional[float]=None; yesterday_price: Optional[float]=None; change_last_pct: Optional[float]=None; volume: Optional[float]=None; value: Optional[float]=None
    nav_issue: Optional[float]=None; nav_redeem: Optional[float]=None; nav_date: Optional[str]=None; best_bid: Optional[float]=None; best_ask: Optional[float]=None; bid_volume: Optional[float]=None; ask_volume: Optional[float]=None
    source: str="brs"; captured_at: str=field(default_factory=_now_iso); raw: dict[str, Any]=field(default_factory=dict)
    def to_dict(self): d=asdict(self); d["raw"]={}; return d
    def checksum(self): return _sha256_hex(json.dumps(self.to_dict(), sort_keys=True).encode("utf-8"))

@dataclass(frozen=True)
class HistoryRecord:
    fund_id: int; trade_date: str; open: Optional[float]=None; high: Optional[float]=None; low: Optional[float]=None; close_price: Optional[float]=None; volume: Optional[float]=None; source: str="brs"
    def to_dict(self): return asdict(self)
    def checksum(self): return _sha256_hex(json.dumps(self.to_dict(), sort_keys=True).encode("utf-8"))

@dataclass(frozen=True)
class SyncBatch:
    batch_id: str; source: str="iran-gateway"; target: str="external-server"; snapshots: tuple[FundSnapshot, ...]=(); history_records: tuple[HistoryRecord, ...]=(); created_at: str=field(default_factory=_now_iso); checksum: str=""; compressed_size: int=0; compressed: bytes=b""; status: str="pending"
    def __post_init__(self):
        if not self.checksum:
            hashes = [s.checksum() for s in self.snapshots] + [h.checksum() for h in self.history_records]
            object.__setattr__(self, "checksum", _sha256_hex(json.dumps(hashes, sort_keys=True).encode("utf-8")))
    def to_dict(self): return {"batch_id": self.batch_id, "snapshot_count": len(self.snapshots), "history_record_count": len(self.history_records), "status": self.status}

@dataclass(frozen=True)
class SyncManifest:
    batch_id: str; total_chunks: int; chunk_size: int; checksum: str; created_at: str=field(default_factory=_now_iso); snapshot_count: int=0; history_record_count: int=0; source: str="iran-gateway"; target: str="external-server"
    def to_dict(self): return {"batch_id": self.batch_id, "total_chunks": self.total_chunks, "chunk_size": self.chunk_size, "checksum": self.checksum, "created_at": self.created_at, "snapshot_count": self.snapshot_count, "history_record_count": self.history_record_count, "source": self.source, "target": self.target}

@dataclass(frozen=True)
class SyncChunk:
    chunk_id: str; batch_id: str; chunk_index: int; total_chunks: int; data: bytes; checksum: str=""; size_bytes: int=0; attempts: int=0; last_attempt_at: Optional[str]=None; status: str="pending"
    def __post_init__(self):
        if self.size_bytes == 0:
            object.__setattr__(self, "size_bytes", len(self.data))
    def to_dict(self): return {"chunk_id": self.chunk_id, "batch_id": self.batch_id, "chunk_index": self.chunk_index, "total_chunks": self.total_chunks, "size_bytes": self.size_bytes, "checksum": self.checksum, "attempts": self.attempts, "status": self.status}
