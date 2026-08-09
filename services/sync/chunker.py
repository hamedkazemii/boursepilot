"""
Sync V1 — SyncChunker

Splits compressed payloads into configurable chunks for
resumable, retry-capable transfer.

Default chunk size: 4.8KB (4800 bytes) — safe for MTU 1500
Prevents IP fragmentation on cross-server transfers.
Supports retry/resume metadata for interrupted transfers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from services.sync.models import SyncChunk, SyncManifest

logger = logging.getLogger(__name__)


class SyncChunker:
    """
    Splits a compressed byte payload into fixed-size chunks
    with retry/resume metadata.

    Each chunk is independently checksummed so that
    failed chunks can be retransmitted without resending
    the entire batch.
    """

    def __init__(self, chunk_size: int = 4800) -> None:
        """
        Args:
            chunk_size: Maximum size of each chunk in bytes.
                Default 4800 = 4.8KB (safe for MTU 1500).
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def chunk(
        self,
        data: bytes,
        batch_id: str,
        checksum: str,
    ) -> list[SyncChunk]:
        """
        Split a compressed payload into chunks.

        Args:
            data: Compressed byte payload to split.
            batch_id: Parent batch identifier.
            checksum: Parent batch checksum (SHA-256 hex).

        Returns:
            List of SyncChunk objects, one per chunk.
        """
        if not data:
            raise ValueError("Cannot chunk empty data")

        total_chunks = self._calculate_total_chunks(len(data))
        chunks: list[SyncChunk] = []

        for i in range(total_chunks):
            start = i * self.chunk_size
            end = min(start + self.chunk_size, len(data))
            chunk_data = data[start:end]

            chunk_id = self._generate_chunk_id(batch_id, i)

            chunk = SyncChunk(
                chunk_id=chunk_id,
                batch_id=batch_id,
                chunk_index=i,
                total_chunks=total_chunks,
                data=chunk_data,
                # No checksum here - let SyncChunk.__post_init__ compute chunk-level SHA256
                status="pending",
            )
            chunks.append(chunk)

        # Generate manifest for this batch
        manifest = SyncManifest(
            batch_id=batch_id,
            total_chunks=total_chunks,
            chunk_size=self.chunk_size,
            checksum=checksum,
            snapshot_count=0,  # Not known at chunking time; set by exporter
        )

        logger.info(
            "Chunked %d bytes into %d chunks (chunk_size=%d)",
            len(data),
            total_chunks,
            self.chunk_size,
        )

        # Store manifest as instance attribute for exporter to retrieve
        self._last_manifest = manifest
        return chunks

    # ------------------------------------------------------------------
    # Resume / Retry
    # ------------------------------------------------------------------

    def get_pending_chunks(
        self,
        chunks: list[SyncChunk],
    ) -> list[SyncChunk]:
        """
        Return only chunks that have not yet been acknowledged.

        Used for retry/resume: after an interrupted transfer,
        re-send only the chunks that are still pending.

        Args:
            chunks: Full list of chunks from a batch.

        Returns:
            List of chunks with status != 'acked'.
        """
        pending = [c for c in chunks if c.status != "acked"]
        logger.info(
            "Pending chunks: %d of %d",
            len(pending),
            len(chunks),
        )
        return pending

    def mark_chunk_sent(
        self,
        chunk: SyncChunk,
    ) -> SyncChunk:
        """
        Mark a chunk as sent (attempt recorded).

        Returns a new SyncChunk with updated status and attempt count.
        """
        updated = SyncChunk(
            chunk_id=chunk.chunk_id,
            batch_id=chunk.batch_id,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            data=chunk.data,
            checksum=chunk.checksum,
            size_bytes=chunk.size_bytes,
            attempts=chunk.attempts + 1,
            last_attempt_at=datetime.now(timezone.utc).isoformat(),
            status="sent",
        )
        logger.debug("Chunk %s marked as sent (attempt %d)", chunk.chunk_id, updated.attempts)
        return updated

    def mark_chunk_acked(
        self,
        chunk: SyncChunk,
    ) -> SyncChunk:
        """
        Mark a chunk as successfully acknowledged.
        """
        updated = SyncChunk(
            chunk_id=chunk.chunk_id,
            batch_id=chunk.batch_id,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            data=chunk.data,
            checksum=chunk.checksum,
            size_bytes=chunk.size_bytes,
            attempts=chunk.attempts,
            last_attempt_at=chunk.last_attempt_at,
            status="acked",
        )
        logger.debug("Chunk %s acknowledged", chunk.chunk_id)
        return updated

    def mark_chunk_failed(
        self,
        chunk: SyncChunk,
        error_message: str = "",
    ) -> SyncChunk:
        """
        Mark a chunk as failed after exhausting retries.
        """
        updated = SyncChunk(
            chunk_id=chunk.chunk_id,
            batch_id=chunk.batch_id,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            data=chunk.data,
            checksum=chunk.checksum,
            size_bytes=chunk.size_bytes,
            attempts=chunk.attempts,
            last_attempt_at=datetime.now(timezone.utc).isoformat(),
            status="failed",
        )
        logger.warning(
            "Chunk %s failed: %s",
            chunk.chunk_id,
            error_message or "unknown error",
        )
        return updated

    # ------------------------------------------------------------------
    # Reassembly
    # ------------------------------------------------------------------

    @property
    def last_manifest(self) -> Optional[SyncManifest]:
        """Return the manifest from the most recent chunk() call."""
        return getattr(self, "_last_manifest", None)

    def reassemble(
        self,
        chunks: list[SyncChunk],
    ) -> bytes:
        """
        Reassemble chunks into the original compressed payload.

        Chunks are sorted by chunk_index to ensure correct order.

        Args:
            chunks: List of SyncChunk objects (any order).

        Returns:
            Reassembled compressed byte payload.

        Raises:
            ValueError: If chunks are missing or have mismatched checksums.
        """
        if not chunks:
            raise ValueError("Cannot reassemble empty chunk list")

        # Sort by index
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)

        # Validate all chunks are present
        expected_indices = set(range(sorted_chunks[0].total_chunks))
        actual_indices = {c.chunk_index for c in sorted_chunks}
        missing = expected_indices - actual_indices
        if missing:
            raise ValueError(f"Missing chunks: {sorted(missing)}")

        # Validate checksums
        parent_checksum = sorted_chunks[0].checksum
        for chunk in sorted_chunks:
            if chunk.checksum != parent_checksum:
                raise ValueError(
                    f"Chunk {chunk.chunk_id} checksum mismatch "
                    f"(expected {parent_checksum}, got {chunk.checksum})"
                )

        # Concatenate
        return b"".join(c.data for c in sorted_chunks)

    def reassemble_with_manifest(
        self,
        chunks: list[SyncChunk],
        manifest: SyncManifest,
    ) -> bytes:
        """
        Reassemble chunks and validate against a manifest.

        Args:
            chunks: List of SyncChunk objects (any order).
            manifest: SyncManifest to validate against.

        Returns:
            Reassembled compressed byte payload.

        Raises:
            ValueError: If manifest validation fails or chunks are invalid.
        """
        if chunks and not manifest.verify_chunk(chunks[0]):
            raise ValueError(
                f"Manifest mismatch: chunk {chunks[0].chunk_id} "
                f"does not belong to manifest {manifest.batch_id}"
            )

        return self.reassemble(chunks)
        """
        Reassemble chunks into the original compressed payload.

        Chunks are sorted by chunk_index to ensure correct order.

        Args:
            chunks: List of SyncChunk objects (any order).

        Returns:
            Reassembled compressed byte payload.

        Raises:
            ValueError: If chunks are missing or have mismatched checksums.
        """
        if not chunks:
            raise ValueError("Cannot reassemble empty chunk list")

        # Sort by index
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)

        # Validate all chunks are present
        expected_indices = set(range(sorted_chunks[0].total_chunks))
        actual_indices = {c.chunk_index for c in sorted_chunks}
        missing = expected_indices - actual_indices
        if missing:
            raise ValueError(f"Missing chunks: {sorted(missing)}")

        # Validate checksums
        parent_checksum = sorted_chunks[0].checksum
        for chunk in sorted_chunks:
            if chunk.checksum != parent_checksum:
                raise ValueError(
                    f"Chunk {chunk.chunk_id} checksum mismatch "
                    f"(expected {parent_checksum}, got {chunk.checksum})"
                )

        # Concatenate
        return b"".join(c.data for c in sorted_chunks)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calculate_total_chunks(self, data_length: int) -> int:
        """Calculate how many chunks are needed for the given data length."""
        import math

        return math.ceil(data_length / self.chunk_size)

    def _generate_chunk_id(self, batch_id: str, index: int) -> str:
        """Generate a unique chunk ID."""
        import hashlib

        raw = f"{batch_id}:{index}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
