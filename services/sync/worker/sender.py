"""
Sync V1 Worker — sender orchestration.

Coordinates manifest + chunk transmission via SyncTransport,
tracks per-chunk progress in StateManager, and applies
RetryPolicy for resilience.
"""

from __future__ import annotations

import logging
from typing import Any

from services.sync.models import SyncBatch, SyncChunk
from services.sync.transport import SyncTransport
from services.sync.worker.state import StateManager
from services.sync.worker.retry import RetryPolicy
from services.sync.worker.batch_storage import BatchStorage

logger = logging.getLogger(__name__)


class SyncSender:
    """Orchestrates sending a SyncBatch to the receiver."""

    def __init__(
        self,
        transport: SyncTransport,
        state: StateManager,
        retry: RetryPolicy,
        batch_storage: BatchStorage,
    ) -> None:
        self._transport = transport
        self._state = state
        self._retry = retry
        self._batch_storage = batch_storage
        logger.info("SyncSender initialized")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def send_batch(self, batch: SyncBatch) -> dict[str, Any]:
        """Send a batch: manifest first, then chunks.

        Args:
            batch: The SyncBatch to send.

        Returns:
            dict with 'manifest' and 'chunks' results.
        """
        total_chunks = len(batch._chunks)
        self._state.save_batch_state(
            batch.batch_id,
            "sending",
            total_chunks=total_chunks,
        )

        manifest_result = self._send_manifest(batch)

        chunks_result = self._send_chunks(batch, batch._chunks)

        acked = sum(1 for r in chunks_result if r.get("status") == "acked")
        final_status = "acked" if acked == total_chunks else "failed"

        self._state.save_batch_state(
            batch.batch_id,
            final_status,
            total_chunks=total_chunks,
            received_chunks=acked,
        )

        return {
            "manifest": manifest_result,
            "chunks": chunks_result,
            "status": final_status,
        }

    def resume_batch(self, batch_id: str) -> dict[str, Any] | None:
        """Resume an interrupted batch by re-sending unacked chunks.

        Args:
            batch_id: The batch to resume.

        Returns:
            dict with resume results, or None if no pending state found.
        """
        state = self._state.load_batch_state(batch_id)
        if state is None:
            logger.warning("No state found for batch %s — cannot resume", batch_id)
            return None

        total_chunks = state.get("total_chunks", 0)
        if total_chunks == 0:
            logger.warning("Batch %s has 0 total chunks — skipping resume", batch_id)
            return None

        unacked = self._state.get_unacked_chunks(batch_id, total_chunks)
        if not unacked:
            logger.info("Batch %s has no unacked chunks — already complete", batch_id)
            return {"batch_id": batch_id, "status": "already_complete", "chunks": []}

        logger.info(
            "Resuming batch %s: %d unacked chunks out of %d",
            batch_id,
            len(unacked),
            total_chunks,
        )

        self._state.save_batch_state(batch_id, "sending", total_chunks=total_chunks)

        # Build minimal chunk objects for unacked indices
        chunks = [
            SyncChunk(
                chunk_id=f"resume-{batch_id}-{idx}",
                batch_id=batch_id,
                chunk_index=idx,
                total_chunks=total_chunks,
                data=b"",
                checksum=state.get("checksum", ""),
                status="pending",
            )
            for idx in unacked
        ]

        results = self._send_chunks(None, chunks)

        acked = sum(1 for r in results if r.get("status") == "acked")
        self._state.save_batch_state(
            batch_id,
            "acked" if acked == len(results) else "failed",
            total_chunks=total_chunks,
            received_chunks=acked,
        )

        return {
            "batch_id": batch_id,
            "status": "resumed",
            "chunks": results,
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _send_manifest(self, batch: SyncBatch) -> dict[str, Any]:
        """Send the manifest and return the response."""
        logger.info("Sending manifest for batch %s", batch.batch_id)
        result = self._transport.send_manifest(batch)
        logger.debug("Manifest sent for batch %s: %s", batch.batch_id, result)
        return result

    def _send_chunks(
        self,
        batch: SyncBatch | None,
        chunks: list[SyncChunk],
    ) -> list[dict[str, Any]]:
        """Send chunks with per-chunk retry.

        Args:
            batch: The parent batch (may be None for resume).
            chunks: Chunks to send.

        Returns:
            List of chunk send results.
        """
        results: list[dict[str, Any]] = []

        for chunk in chunks:
            result = self._send_chunk_with_retry(batch, chunk)
            results.append(result)

        return results

    def _send_chunk_with_retry(
        self,
        batch: SyncBatch | None,
        chunk: SyncChunk,
    ) -> dict[str, Any]:
        """Send a single chunk with retry logic.

        Creates a minimal SyncBatch containing only the target chunk
        and calls SyncTransport.send_chunks() on it.

        Args:
            batch: The parent batch (may be None for resume).
            chunk: The single chunk to send.

        Returns:
            dict with 'status' and chunk metadata.
        """
        batch_id = chunk.batch_id

        # Build a minimal batch containing only this chunk
        mini_batch = SyncBatch(
            batch_id=batch_id,
            source=batch.source if batch else "resume",
            target=batch.target if batch else "external-server",
            checksum=chunk.checksum,
        )
        # Bypass frozen restriction to set private attributes
        object.__setattr__(mini_batch, "_chunks", [chunk])

        def _do_send() -> dict[str, Any]:
            response = self._transport.send_chunks(mini_batch)
            return {"status": "acked", "chunk_index": chunk.chunk_index}

        try:
            result = self._retry.execute_with_retry(
                _do_send,
                on_retry=lambda attempt, exc: logger.warning(
                    "Chunk %s attempt %d failed: %s",
                    chunk.chunk_id,
                    attempt,
                    exc,
                ),
            )
            logger.info("Chunk %s sent successfully", chunk.chunk_id)
            return result
        except Exception as exc:
            logger.error(
                "Chunk %s failed after retries: %s",
                chunk.chunk_id,
                exc,
            )
            return {
                "status": "failed",
                "chunk_index": chunk.chunk_index,
                "error": str(exc),
            }
