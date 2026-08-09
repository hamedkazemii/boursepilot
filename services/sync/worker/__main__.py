#!/usr/bin/env python3
"""Sync Worker — daemon entry point."""

from __future__ import annotations

import logging
import signal
import sys
import time

from services.sync.worker.config import WorkerConfig
from services.sync.worker.sender import SyncSender
from services.sync.worker.state import StateManager
from services.sync.worker.retry import RetryPolicy
from services.sync.worker.batch_storage import BatchStorage
from services.sync.worker.worker import SyncWorker
from services.sync.transport import SyncTransport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    config = WorkerConfig()

    if not config.SYNC_ENABLED:
        logger.info("SYNC_ENABLED=false — exiting")
        return 0

    transport = SyncTransport(
        target_url=config.SYNC_TARGET_URL,
        api_key=config.SYNC_API_KEY,
        timeout=300,
    )
    state = StateManager(config.SYNC_STATE_DIR)
    retry = RetryPolicy()
    batch_storage = BatchStorage(config.SYNC_STATE_DIR)
    sender = SyncSender(transport, state, retry, batch_storage)
    worker = SyncWorker(sender, state, config, batch_storage)

    logger.info("Sync Worker started — interval: %ds", config.SYNC_SCHEDULE_SECONDS)

    shutdown = False

    def _signal_handler(signum, frame):
        nonlocal shutdown
        logger.info("Received signal %s — shutting down", signum)
        shutdown = True

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    while not shutdown:
        try:
            result = worker.run_cycle()
            logger.info("Sync cycle result: %s", result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Sync cycle failed: %s", exc)

        # Sleep with periodic shutdown check
        for _ in range(config.SYNC_SCHEDULE_SECONDS):
            if shutdown:
                break
            time.sleep(1)

    logger.info("Sync Worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())