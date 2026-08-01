"""
Sync V1 — ReceiverStorage

Temporary file-based storage for received chunks and batches.
No database tables. No production persistence changes.

Storage layout:
    data/receiver/
    ├── batches/           # Batch metadata JSON files
    │   └── {batch_id}.json
    └── chunks/            # Individual chunk files
        └── {batch_id}/{chunk_number}.bin
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from services.receiver.models import ReceivedChunk, ReceivedBatch

logger = logging.getLogger(__name__)


class ReceiverStorage:
    """
    File-based storage for received sync chunks and batches.

    All data is stored as JSON (metadata) and binary files (chunk payloads)
    in the data/receiver/ directory. No database is used.
    """

    def __init__(self, base_dir: str = "data/receiver") -> None:
        self.base_dir = Path(base_dir)
        self.batches_dir = self.base_dir / "batches"
        self.chunks_dir = self.base_dir / "chunks"
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ReceiverStorage initialized — dir: %s", self.base_dir)

    # ------------------------------------------------------------------
    # Batch storage
    # ------------------------------------------------------------------

    def save_batch(self, batch: ReceivedBatch) -> Path:
        """Save batch metadata as a JSON file."""
        filepath = self.batches_dir / f"{batch.batch_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(batch.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug("Saved batch metadata: %s", filepath)
        return filepath

    def load_batch(self, batch_id: str) -> Optional[ReceivedBatch]:
        """Load batch metadata from a JSON file."""
        filepath = self.batches_dir / f"{batch_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._batch_from_dict(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load batch %s: %s", batch_id, exc)
            return None

    def delete_batch(self, batch_id: str) -> bool:
        """Delete batch metadata and all associated chunk files."""
        # Delete metadata file
        meta_path = self.batches_dir / f"{batch_id}.json"
        if meta_path.exists():
            meta_path.unlink()

        # Delete chunk files
        chunk_dir = self.chunks_dir / batch_id
        if chunk_dir.exists():
            for f in chunk_dir.glob("*.bin"):
                f.unlink()
            chunk_dir.rmdir()

        logger.info("Deleted batch %s and all associated files", batch_id)
        return True

    # ------------------------------------------------------------------
    # Chunk storage
    # ------------------------------------------------------------------

    def save_chunk(self, chunk: ReceivedChunk) -> Path:
        """Save a chunk payload as a binary file."""
        chunk_dir = self.chunks_dir / chunk.batch_id
        chunk_dir.mkdir(parents=True, exist_ok=True)

        filepath = chunk_dir / f"{chunk.chunk_number}.bin"
        with open(filepath, "wb") as f:
            f.write(chunk.payload)

        logger.debug("Saved chunk %d for batch %s", chunk.chunk_number, chunk.batch_id)
        return filepath

    def load_chunk(self, batch_id: str, chunk_number: int) -> Optional[ReceivedChunk]:
        """Load a chunk payload from a binary file."""
        filepath = self.chunks_dir / batch_id / f"{chunk_number}.bin"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "rb") as f:
                payload = f.read()
            return ReceivedChunk(
                batch_id=batch_id,
                chunk_number=chunk_number,
                payload=payload,
                checksum="",  # Checksum stored in metadata, not file
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load chunk %d for batch %s: %s", chunk_number, batch_id, exc)
            return None

    def chunk_exists(self, batch_id: str, chunk_number: int) -> bool:
        """Check if a chunk file exists."""
        filepath = self.chunks_dir / batch_id / f"{chunk_number}.bin"
        return filepath.exists()

    def list_chunks(self, batch_id: str) -> list[int]:
        """List all chunk numbers for a batch."""
        chunk_dir = self.chunks_dir / batch_id
        if not chunk_dir.exists():
            return []
        return sorted(
            int(f.stem) for f in chunk_dir.glob("*.bin") if f.stem.isdigit()
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_old_batches(self, older_than_hours: int = 24) -> int:
        """Remove batch metadata and chunk files older than the given age."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        deleted = 0

        for meta_file in self.batches_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(
                meta_file.stat().st_mtime,
                tz=timezone.utc,
            )
            if mtime < cutoff:
                batch_id = meta_file.stem
                self.delete_batch(batch_id)
                deleted += 1

        logger.info("Cleaned up %d old batches", deleted)
        return deleted

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _batch_from_dict(self, d: dict[str, Any]) -> ReceivedBatch:
        """Reconstruct a ReceivedBatch from a dict."""
        chunks_data = d.pop("chunks", {})
        chunks: dict[int, ReceivedChunk] = {}
        for num_str, chunk_data in chunks_data.items():
            if isinstance(chunk_data, dict):
                # Payload is stored separately as binary chunk files.
                # Batch metadata JSON must never contain binary payload.
                chunk_file = (
                    self.chunks_dir
                    / chunk_data.get("batch_id", d["batch_id"])
                    / f"{chunk_data.get('chunk_number', int(num_str))}.bin"
                )

                payload = b""

                if chunk_file.exists():
                    with open(chunk_file, "rb") as cf:
                        payload = cf.read()
                chunk = ReceivedChunk(
                    batch_id=chunk_data.get("batch_id", d["batch_id"]),
                    chunk_number=chunk_data.get("chunk_number", int(num_str)),
                    payload=payload,
                    checksum=chunk_data.get("checksum", ""),
                    received_at=chunk_data.get("received_at", ""),
                    source=chunk_data.get("source", "iran-gateway"),
                )
                chunks[int(num_str)] = chunk

        return ReceivedBatch(
            batch_id=d["batch_id"],
            total_chunks=d["total_chunks"],
            chunk_size=d["chunk_size"],
            expected_checksum=d["expected_checksum"],
            snapshot_count=d.get("snapshot_count", 0),
            source=d.get("source", "iran-gateway"),
            target=d.get("target", "external-server"),
            created_at=d.get("created_at", ""),
            chunks=chunks,
            status=d.get("status", "pending"),
            completed_at=d.get("completed_at"),
            error_message=d.get("error_message"),
        )
