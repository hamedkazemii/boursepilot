"""
Sync V1 — Receiver API

Receives sync chunks from the Iran gateway server.
Validates chunks, detects duplicates, reassembles batches,
and verifies final checksums.

This module is additive — it does not modify any
existing provider, telegram, core, or gateway code.
"""

from services.receiver.api import app
from services.receiver.models import ReceivedChunk, ReceivedBatch, SyncAck
from services.receiver.storage import ReceiverStorage
from services.receiver.validator import ChunkValidator

__all__ = [
    "app",
    "ReceivedChunk",
    "ReceivedBatch",
    "SyncAck",
    "ReceiverStorage",
    "ChunkValidator",
]
