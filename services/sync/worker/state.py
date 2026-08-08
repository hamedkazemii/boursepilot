"""
Sync V1 Worker — file-based local state manager.

Tracks pending, sent, and failed batches using JSON files
under the configured state directory. No database required.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StateManager:
    """File-based state manager for sync worker batches."""

    def __init__(self, state_dir: str = "data/sync/worker") -> None:
        self._state_dir = Path(state_dir)
        self._batches_dir = self._state_dir / "batches"
        self._chunks_dir = self._state_dir / "chunks"
        self._batches_dir.mkdir(parents=True, exist_ok=True)
        self._chunks_dir.mkdir(parents=True, exist_ok=True)
        logger.info("StateManager initialized — dir: %s", self._batches_dir)

    # ------------------------------------------------------------------
    # Batch state
    # ------------------------------------------------------------------

    def save_batch_state(
        self,
        batch_id: str,
        status: str,
        *,
        total_chunks: int = 0,
        received_chunks: int = 0,
        checksum: str = "",
        error_message: str = "",
    ) -> Path:
        """Save or update batch state."""
        filepath = self._batches_dir / f"{batch_id}.json"
        existing: dict[str, Any] = {}
        if filepath.exists():
            try:
                existing = json.loads(filepath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = {}

        now = datetime.now(timezone.utc).isoformat()
        state: dict[str, Any] = {
            **existing,
            "batch_id": batch_id,
            "status": status,
            "total_chunks": total_chunks,
            "received_chunks": received_chunks,
            "checksum": checksum,
            "error_message": error_message,
            "updated_at": now,
        }
        if "created_at" not in existing:
            state["created_at"] = now

        filepath.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Saved batch state: %s → %s", batch_id, status)
        return filepath

    def load_batch_state(self, batch_id: str) -> Optional[dict[str, Any]]:
        """Load batch state from file."""
        filepath = self._batches_dir / f"{batch_id}.json"
        if not filepath.exists():
            return None
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load batch state %s: %s", batch_id, exc)
            return None

    def list_batch_states(self) -> list[dict[str, Any]]:
        """List all batch states."""
        states: list[dict[str, Any]] = []
        if not self._batches_dir.exists():
            return states
        for filepath in sorted(self._batches_dir.glob("*.json")):
            try:
                state = json.loads(filepath.read_text(encoding="utf-8"))
                states.append(state)
            except (json.JSONDecodeError, OSError):
                continue
        return states

    def get_pending_batches(self) -> list[dict[str, Any]]:
        """Return batches with status pending or failed (resume candidates)."""
        return [
            s
            for s in self.list_batch_states()
            if s.get("status") in ("pending", "failed", "sending")
        ]

    def get_unacked_chunks(
        self, batch_id: str, total_chunks: int
    ) -> list[int]:
        """Return chunk indices that have not been acknowledged."""
        state = self.load_batch_state(batch_id)
        if state is None:
            return list(range(total_chunks))
        received = state.get("received_chunks", 0)
        if received >= total_chunks:
            return []
        # Return all chunk indices not yet confirmed acked
        return list(range(received, total_chunks))

    def delete_batch_state(self, batch_id: str) -> bool:
        """Delete batch state file."""
        filepath = self._batches_dir / f"{batch_id}.json"
        if filepath.exists():
            filepath.unlink()
            logger.debug("Deleted batch state: %s", batch_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Chunk state
    # ------------------------------------------------------------------

    def save_chunk_state(
        self,
        batch_id: str,
        chunk_index: int,
        payload: bytes,
    ) -> Path:
        """Save chunk payload as a separate binary file.

        Stores chunk data outside JSON to avoid encoding overhead
        and binary-in-JSON issues.
        """
        filepath = self._chunks_dir / f"{batch_id}.{chunk_index}"
        filepath.write_bytes(payload)
        logger.debug("Saved chunk state: %s chunk %d", batch_id, chunk_index)
        return filepath

    def load_chunk_state(
        self,
        batch_id: str,
        chunk_index: int,
    ) -> Optional[bytes]:
        """Load chunk payload from binary file.

        Returns None if the chunk file does not exist.
        """
        filepath = self._chunks_dir / f"{batch_id}.{chunk_index}"
        if not filepath.exists():
            return None
        try:
            return filepath.read_bytes()
        except OSError as exc:
            logger.warning("Failed to load chunk state %s chunk %d: %s", batch_id, chunk_index, exc)
            return None

    def get_unacked_chunks_with_data(
        self,
        batch_id: str,
        total_chunks: int,
    ) -> list[tuple[int, bytes]]:
        """Return unacked chunk indices with their payload data.

        Only returns chunks where payload data is available.
        Chunks without stored payload are omitted.
        """
        unacked = self.get_unacked_chunks(batch_id, total_chunks)
        result: list[tuple[int, bytes]] = []
        for idx in unacked:
            payload = self.load_chunk_state(batch_id, idx)
            if payload is not None:
                result.append((idx, payload))
            else:
                logger.warning(
                    "Chunk %d payload missing for batch %s — cannot resume",
                    idx,
                    batch_id,
                )
        return result
