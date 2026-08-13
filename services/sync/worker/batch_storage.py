"""
Sync V1 Worker — batch and chunk payload storage.

Persists SyncBatch payloads and SyncChunk data as binary files
outside JSON. Per-chunk checksums are stored separately for
integrity verification on resume. Uses atomic file operations
(write-to-temp, rename) to prevent partial writes on crash.

StateManager remains metadata-only; this class handles payload
persistence only.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class BatchStorage:
    """Hybrid storage layer for sync worker batch and chunk payloads."""

    def __init__(self, state_dir: str = "data/sync/worker") -> None:
        self._state_dir = Path(state_dir)
        self._payloads_dir = self._state_dir / "payloads"
        self._chunks_dir = self._state_dir / "chunks"
        self._payloads_dir.mkdir(parents=True, exist_ok=True)
        self._chunks_dir.mkdir(parents=True, exist_ok=True)
        logger.info("BatchStorage initialized — dir: %s", self._state_dir)

    # ------------------------------------------------------------------
    # Batch payload
    # ------------------------------------------------------------------

    def save_batch_payload(self, batch_id: str, payload: bytes) -> Path:
        """Persist full batch compressed payload atomically."""
        filepath = self._payloads_dir / f"{batch_id}.bin"
        self._atomic_write_bytes(filepath, payload)
        logger.debug("Saved batch payload: %s (%d bytes)", batch_id, len(payload))
        return filepath

    def load_batch_payload(self, batch_id: str) -> Optional[bytes]:
        """Load batch payload. Returns None if file missing."""
        filepath = self._payloads_dir / f"{batch_id}.bin"
        if not filepath.exists():
            return None
        try:
            return filepath.read_bytes()
        except OSError as exc:
            logger.warning("Failed to load batch payload %s: %s", batch_id, exc)
            return None

    def delete_batch_payload(self, batch_id: str) -> bool:
        """Delete batch payload file. Returns True if removed."""
        filepath = self._payloads_dir / f"{batch_id}.bin"
        if filepath.exists():
            filepath.unlink()
            logger.debug("Deleted batch payload: %s", batch_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Chunk data
    # ------------------------------------------------------------------

    def save_chunk(
        self,
        batch_id: str,
        chunk_index: int,
        data: bytes,
        checksum: str,
    ) -> Path:
        """Persist chunk binary data and checksum atomically."""
        chunk_dir = self._chunks_dir / batch_id
        chunk_dir.mkdir(parents=True, exist_ok=True)

        data_path = chunk_dir / f"{chunk_index}.bin"
        checksum_path = chunk_dir / f"{chunk_index}.chk"

        self._atomic_write_bytes(data_path, data)
        self._atomic_write_text(checksum_path, checksum)

        logger.debug(
            "Saved chunk %s index %d (%d bytes)",
            batch_id,
            chunk_index,
            len(data),
        )
        return data_path

    def load_chunk(
        self,
        batch_id: str,
        chunk_index: int,
    ) -> Optional[bytes]:
        """Load chunk binary data. Returns None if file missing."""
        filepath = self._chunks_dir / batch_id / f"{chunk_index}.bin"
        if not filepath.exists():
            return None
        try:
            return filepath.read_bytes()
        except OSError as exc:
            logger.warning(
                "Failed to load chunk %s index %d: %s",
                batch_id,
                chunk_index,
                exc,
            )
            return None

    def load_chunk_checksum(
        self,
        batch_id: str,
        chunk_index: int,
    ) -> Optional[str]:
        """Load per-chunk checksum. Returns None if file missing."""
        filepath = self._chunks_dir / batch_id / f"{chunk_index}.chk"
        if not filepath.exists():
            return None
        try:
            return filepath.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning(
                "Failed to load checksum for chunk %s index %d: %s",
                batch_id,
                chunk_index,
                exc,
            )
            return None

    def delete_chunk(
        self,
        batch_id: str,
        chunk_index: int,
    ) -> bool:
        """Delete chunk data and checksum files. Returns True if any removed."""
        chunk_dir = self._chunks_dir / batch_id
        data_path = chunk_dir / f"{chunk_index}.bin"
        checksum_path = chunk_dir / f"{chunk_index}.chk"

        removed = False
        for path in (data_path, checksum_path):
            if path.exists():
                path.unlink()
                removed = True

        if removed:
            logger.debug("Deleted chunk %s index %d", batch_id, chunk_index)
            # Clean up empty batch chunk directory
            self._cleanup_empty_chunk_dir(batch_id, chunk_dir)

        return removed

    # ------------------------------------------------------------------
    # Resume support
    # ------------------------------------------------------------------

    def get_stored_chunks(
        self,
        batch_id: str,
    ) -> list[Tuple[int, bytes, str]]:
        """Return all stored (chunk_index, data, checksum) tuples.

        Only returns chunks where both data and checksum files exist.
        Chunks missing either file are omitted with a warning.
        """
        chunk_dir = self._chunks_dir / batch_id
        if not chunk_dir.exists():
            return []

        results: list[Tuple[int, bytes, str]] = []

        # Collect all .bin files and match with .chk files
        bin_files = sorted(chunk_dir.glob("*.bin"))
        for bin_path in bin_files:
            chunk_index_str = bin_path.stem  # e.g. "3" from "3.bin"
            chk_path = chunk_dir / f"{chunk_index_str}.chk"

            if not chk_path.exists():
                logger.warning(
                    "Chunk %s index %s has data but no checksum — skipping",
                    batch_id,
                    chunk_index_str,
                )
                continue

            try:
                data = bin_path.read_bytes()
                checksum = chk_path.read_text(encoding="utf-8").strip()
                chunk_index = int(chunk_index_str)
                results.append((chunk_index, data, checksum))
            except (OSError, ValueError) as exc:
                logger.warning(
                    "Failed to load stored chunk %s index %s: %s",
                    batch_id,
                    chunk_index_str,
                    exc,
                )
                continue

        return results

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def delete_batch(self, batch_id: str) -> bool:
        """Delete all payload data for a completed batch.

        Removes batch payload file and all chunk files.
        Should only be called after full batch ACK.
        """
        removed_payload = self.delete_batch_payload(batch_id)

        chunk_dir = self._chunks_dir / batch_id
        removed_chunks = False
        if chunk_dir.exists():
            for f in chunk_dir.iterdir():
                f.unlink()
            chunk_dir.rmdir()
            removed_chunks = True

        if removed_payload or removed_chunks:
            logger.debug("Deleted all payload data for batch %s", batch_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _atomic_write_bytes(self, filepath: Path, data: bytes) -> None:
        """Write bytes atomically via temp-file + rename."""
        parent = filepath.parent
        parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_path, filepath)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _atomic_write_text(self, filepath: Path, text: str) -> None:
        """Write text atomically via temp-file + rename."""
        parent = filepath.parent
        parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp_path, filepath)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _cleanup_empty_chunk_dir(self, batch_id: str, chunk_dir: Path) -> None:
        """Remove chunk directory if empty after deleting a chunk."""
        try:
            if chunk_dir.exists() and not any(chunk_dir.iterdir()):
                chunk_dir.rmdir()
                logger.debug(
                    "Removed empty chunk directory for batch %s", batch_id
                )
        except OSError:
            pass
