"""
Sync V1 Worker — orchestrator.

Coordinates sync cycles by collecting data, creating batches, and sending them.
"""

from __future__ import annotations

import logging
from typing import Any

from services.sync.worker.config import WorkerConfig
from services.sync.worker.sender import SyncSender
from services.sync.worker.state import StateManager
from services.sync.worker.batch_storage import BatchStorage
from services.sync.collector import FundCollector
from services.sync.exporter import SyncExporter
from services.providers.factory import get_market_data_provider

logger = logging.getLogger(__name__)


class SyncWorker:
    """Orchestrates sync cycles: collect, export, store, send."""

    def __init__(
        self,
        sender: SyncSender,
        state: StateManager,
        config: WorkerConfig,
        batch_storage: BatchStorage,
    ) -> None:
        self._sender = sender
        self._state = state
        self._config = config
        self._batch_storage = batch_storage
        
        # Initialize collector and exporter
        provider = get_market_data_provider()
        self._collector = FundCollector(provider=provider, snapshot_dir='data/sync/snapshots')
        self._exporter = SyncExporter(default_chunk_size=config.SYNC_CHUNK_SIZE)
        
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

        # 1. Collect fresh fund data
        logger.info("Collecting fund snapshots...")
        snapshots = self._collector.collect_all_funds(limit=None)
        if not snapshots:
            logger.warning("No snapshots collected — skipping cycle")
            return {"sent": 0, "resumed": 0, "failed": 0, "skipped": 0}

        # 2. Export to batch
        batch = self._exporter.export_batch(snapshots)
        logger.info("Created batch %s with %d snapshots, %d chunks", batch.batch_id, len(batch.snapshots), len(batch._chunks))

        # 3. Store batch payload and chunks
        self._batch_storage.save_batch_payload(batch.batch_id, batch._get_compressed_payload())
        for chunk in batch._chunks:
            self._batch_storage.save_chunk(batch.batch_id, chunk.chunk_index, chunk.data, chunk.checksum)

        # 4. Store batch state as pending
        self._state.save_batch_state(
            batch.batch_id,
            "pending",
            total_chunks=len(batch._chunks),
            checksum=batch.checksum,
        )

        # 5. Send the batch
        result = self._sender.send_batch(batch)

        return {
            "sent": 1 if result.get("status") == "acked" else 0,
            "resumed": 0,
            "failed": 1 if result.get("status") == "failed" else 0,
            "skipped": 0,
        }
