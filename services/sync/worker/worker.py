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
from services.providers.brs_provider import BrsProvider

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
        
        # Initialize collector and exporter with BrsProvider (quota-aware)
        provider = get_market_data_provider()
        if not isinstance(provider, BrsProvider):
            # Wrap with BrsProvider if needed for quota management
            provider = BrsProvider()
        self._collector = FundCollector(provider=provider, snapshot_dir='data/sync/snapshots')
        self._exporter = SyncExporter(default_chunk_size=config.SYNC_CHUNK_SIZE)
        
        logger.info("SyncWorker initialized with BrsProvider (quota-aware)")

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
        snapshots = self._collector.collect_all_funds(limit=None, include_nav=False)
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
        result = self._sender.send_batch(batch)        # ---------------------------------------------------
        # NAV HYBRID: SELECTIVE FETCH (POST-MARKET)
        # ---------------------------------------------------
        logger.info("Running selective NAV collection...")
        nav_symbols = [s.symbol for s in snapshots if hasattr(s, 'symbol')]
        if nav_symbols:
            nav_snapshots = self._collector.collect_nav_subset(
                symbols=nav_symbols,
                max_funds=50
            )
            if nav_snapshots:
                logger.info("Fetched NAV for %d funds", len(nav_snapshots))
                # Export NAV snapshots through the same official path
                nav_batch = self._exporter.export_batch(nav_snapshots)
                logger.info("Created NAV batch %s with %d snapshots",
                    nav_batch.batch_id, len(nav_batch.snapshots))
                # Store NAV batch payload and chunks
                self._batch_storage.save_batch_payload(
                    nav_batch.batch_id,
                    nav_batch._get_compressed_payload()
                )
                for chunk in nav_batch._chunks:
                    self._batch_storage.save_chunk(
                        nav_batch.batch_id,
                        chunk.chunk_index,
                        chunk.data,
                        chunk.checksum
                    )
                # Store batch state as pending
                self._state.save_batch_state(
                    nav_batch.batch_id,
                    "pending",
                    total_chunks=len(nav_batch._chunks),
                    checksum=nav_batch.checksum,
                )
                # Send the NAV batch
                nav_result = self._sender.send_batch(nav_batch)
                nav_success = 1 if nav_result.get("status") == "acked" else 0
                logger.info("NAV batch sent: %d acked / %d total",
                    nav_success, len(nav_batch._chunks))
            else:
                logger.info("No NAV snapshots to process")
        else:
            logger.info("No fund symbols available for NAV collection")

        return {
            "sent": 1 if result.get("status") == "acked" else 0,
            "resumed": 0,
            "failed": 1 if result.get("status") == "failed" else 0,
            "skipped": 0,
        }
