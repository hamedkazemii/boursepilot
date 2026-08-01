"""
Sync V1 — Receiver Models

Dataclasses for received chunks, batches, and acknowledgments.
No database dependencies. No ORM. No persistence layer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ReceivedChunk:
    """
    A single chunk received from the Iran gateway.

    Stored as a file in data/receiver/ for temporary validation
    before reassembly. No database tables are created.
    """

    batch_id: str
    chunk_number: int
    payload: bytes
    checksum: str
    received_at: str = field(default_factory=_now_iso)
    source: str = "iran-gateway"

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "chunk_number": self.chunk_number,
            "checksum": self.checksum,
            "received_at": self.received_at,
            "source": self.source,
            "payload": self.payload.decode("utf-8", errors="replace"),
            "payload_size": len(self.payload),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReceivedChunk":
        payload = d.get("payload", b"")
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        return cls(
            batch_id=d["batch_id"],
            chunk_number=d["chunk_number"],
            payload=payload,
            checksum=d["checksum"],
            received_at=d.get("received_at", _now_iso()),
            source=d.get("source", "iran-gateway"),
        )


@dataclass(frozen=True)
class ReceivedBatch:
    """
    A complete batch of received chunks.

    Tracks the state of all chunks for a given batch.
    Used by the validator to detect missing/duplicate chunks
    and reassemble the final payload.
    """

    batch_id: str
    total_chunks: int
    chunk_size: int
    expected_checksum: str
    snapshot_count: int = 0
    source: str = "iran-gateway"
    target: str = "external-server"
    created_at: str = field(default_factory=_now_iso)
    chunks: dict[int, ReceivedChunk] = field(default_factory=dict)
    status: str = "pending"  # pending | complete | incomplete | failed
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_chunks": self.total_chunks,
            "chunk_size": self.chunk_size,
            "expected_checksum": self.expected_checksum,
            "snapshot_count": self.snapshot_count,
            "source": self.source,
            "target": self.target,
            "created_at": self.created_at,
            "chunks": {
                str(num): chunk.to_dict()
                for num, chunk in sorted(self.chunks.items())
            },
            "chunk_count": len(self.chunks),
            "status": self.status,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @property
    def missing_chunks(self) -> list[int]:
        """Return list of chunk indices that have not been received."""
        expected = set(range(self.total_chunks))
        received = set(self.chunks.keys())
        return sorted(expected - received)

    @property
    def is_complete(self) -> bool:
        """Return True if all chunks have been received."""
        return len(self.chunks) == self.total_chunks and self.total_chunks > 0


@dataclass(frozen=True)
class SyncAck:
    """
    Acknowledgment sent back to the Iran gateway after
    a chunk or batch is successfully processed.
    """

    batch_id: str
    chunk_number: Optional[int] = None
    status: str = "accepted"  # accepted | duplicate | rejected | error
    message: str = ""
    checksum_valid: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "chunk_number": self.chunk_number,
            "status": self.status,
            "message": self.message,
            "checksum_valid": self.checksum_valid,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
