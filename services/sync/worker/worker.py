"""
Sync V1 Worker — orchestrator.

Coordinates sync cycles by delegating to SyncSender,
StateManager, and WorkerConfig. Does not collect data,
create batches, handle transport, or manage retry logic.
"""

from __future__ import annotations

import logging
from typing import Any

from services.sync.worker.config import WorkerConfig
from services.sync.worker.sender import SyncSender
from services.sync.worker.state import StateManager

logger = logging.getLogger(__name__)


class SyncWorker:
    """Orchestrates sync cycles: find pending, send, resume, report."""

    def __init__(
        self,
        sender: SyncSender,
        state: StateManager,
        config: WorkerConfig,
    ) -> None:
        self._sender = sender
        self._state = state
        self._config = config
        logger.info("SyncWorker initialized")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run_cycle(self) -> dict[str, Any]:
        """Run one sync cycle.

        Returns:
            dict with counts of sent, resumed, failed, skipped.
        """
        if not self._config.SYNC_ENABLED:
            logger.info("SyncWorker disabled — skipping cycle")
            return {"sent": 0, "resumed": 0, "failed": 0, "skipped": 0}

        pending = self._find_pending()
        deduped = self._deduplicate(pending)

        sent = self._send_pending(deduped)
        resumed = self._resume_pending(deduped)

        failed = sum(
            1 for b in deduped
            if b.get("status") == "failed"
        )
        skipped = len(pending) - len(deduped)

        result = {
            "sent": sent,
            "resumed": resumed,
            "failed": failed,
            "skipped": skipped,
        }
        logger.info("Sync cycle complete: %s", result)
        return result

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _find_pending(self) -> list[dict[str, Any]]:
        """Return all batches with pending, failed, or sending status."""
        return self._state.get_pending_batches()

    def _deduplicate(self, batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove batches already in final acked state."""
        return [
            b
            for b in batches
            if b.get("status") != "acked"
        ]

    def _send_pending(self, batches: list[dict[str, Any]]) -> int:
        """Send each pending batch via SyncSender. Returns count sent."""
        count = 0
        for batch in batches:
            if batch.get("status") != "pending":
                continue
            batch_id = batch["batch_id"]
            logger.info("Sending batch %s", batch_id)
            try:
                result = self._sender.send_batch(batch)
                if result.get("status") == "acked":
                    count += 1
                else:
                    logger.warning("Batch %s failed to send", batch_id)
            except Exception as exc:
                logger.error("Error sending batch %s: %s", batch_id, exc)
        return count

    def _resume_pending(self, batches: list[dict[str, Any]]) -> int:
        """Resume each failed or sending batch via SyncSender. Returns count resumed."""
        count = 0
        for batch in batches:
            status = batch.get("status")
            if status not in ("failed", "sending"):
                continue
            batch_id = batch["batch_id"]
            logger.info("Resuming batch %s (status: %s)", batch_id, status)
            try:
                result = self._sender.resume_batch(batch_id)
                if result is not None and result.get("status") in ("resumed", "already_complete"):
                    count += 1
                else:
                    logger.warning("Batch %s resume returned no result", batch_id)
            except Exception as exc:
                logger.error("Error resuming batch %s: %s", batch_id, exc)
        return count
