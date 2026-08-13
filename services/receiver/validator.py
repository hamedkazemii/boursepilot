"""
Sync V1 — ChunkValidator

Validates received chunks against manifests and checksums.
Detects duplicates, missing chunks, and reassembles complete batches.

No database dependencies. No production persistence changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from services.receiver.models import ReceivedChunk, ReceivedBatch, SyncAck
from services.sync.models import SyncManifest

logger = logging.getLogger(__name__)


class ChunkValidator:
    """
    Validates sync chunks and reassembles complete batches.

    Responsibilities:
    - Validate chunk checksums
    - Validate manifest integrity
    - Detect duplicate chunks
    - Detect missing chunks
    - Reassemble complete batches
    - Verify final batch checksum
    """

    def __init__(self, storage=None) -> None:
        self.storage = storage

    # ------------------------------------------------------------------
    # Checksum validation
    # ------------------------------------------------------------------

    def validate_chunk_checksum(self, chunk: ReceivedChunk) -> bool:
        """
        Validate that a chunk's checksum matches its payload.

        The checksum is SHA-256 of the raw payload bytes.
        """
        actual = hashlib.sha256(chunk.payload).hexdigest()
        return actual == chunk.checksum

    def validate_manifest_checksum(
        self,
        manifest: SyncManifest,
        reassembled_data: bytes,
    ) -> bool:
        """
        Validate that reassembled data matches the manifest checksum.

        The manifest checksum is SHA-256 of the compressed payload
        before chunking.
        """
        actual = hashlib.sha256(reassembled_data).hexdigest()
        return actual == manifest.checksum

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def is_duplicate_chunk(
        self,
        batch_id: str,
        chunk_number: int,
    ) -> bool:
        """
        Check if a chunk has already been received for this batch.

        Uses storage to check if a chunk file already exists.
        """
        if self.storage is None:
            return False
        return self.storage.chunk_exists(batch_id, chunk_number)

    # ------------------------------------------------------------------
    # Missing chunk detection
    # ------------------------------------------------------------------

    def detect_missing_chunks(
        self,
        batch: ReceivedBatch,
    ) -> list[int]:
        """
        Return list of chunk indices that have not been received.

        Args:
            batch: The batch to check.

        Returns:
            Sorted list of missing chunk indices.
        """
        return batch.missing_chunks

    def is_batch_complete(self, batch: ReceivedBatch) -> bool:
        """
        Check if all chunks for a batch have been received.

        Args:
            batch: The batch to check.

        Returns:
            True if all chunks are present.
        """
        return batch.is_complete

    # ------------------------------------------------------------------
    # Reassembly
    # ------------------------------------------------------------------

    def reassemble_batch(
        self,
        batch: ReceivedBatch,
    ) -> bytes:
        """
        Reassemble a complete batch from its chunks.

        Chunks are sorted by chunk_number to ensure correct order.

        Args:
            batch: The batch with all chunks received.

        Returns:
            Reassembled compressed byte payload.

        Raises:
            ValueError: If chunks are missing or checksums don't match.
        """
        if not batch.is_complete:
            missing = batch.missing_chunks
            raise ValueError(
                f"Cannot reassemble batch {batch.batch_id}: "
                f"missing chunks {missing}"
            )

        # Sort chunks by number
        sorted_chunks = [
            batch.chunks[i] for i in sorted(batch.chunks.keys())
        ]

        # Validate each chunk's checksum
        for chunk in sorted_chunks:
            if not self.validate_chunk_checksum(chunk):
                raise ValueError(
                    f"Chunk {chunk.chunk_number} in batch {batch.batch_id} "
                    f"has invalid checksum"
                )

        # Concatenate payloads
        return b"".join(chunk.payload for chunk in sorted_chunks)

    # ------------------------------------------------------------------
    # Manifest validation
    # ------------------------------------------------------------------

    def validate_manifest(
        self,
        manifest_data: dict,
    ) -> Optional[SyncManifest]:
        """
        Validate manifest data and create a SyncManifest object.

        Args:
            manifest_data: Dict with batch_id, total_chunks, chunk_size,
                checksum, snapshot_count, created_at.

        Returns:
            SyncManifest if valid, None if invalid.
        """
        required_fields = [
            "batch_id",
            "total_chunks",
            "chunk_size",
            "checksum",
        ]

        for field in required_fields:
            if field not in manifest_data:
                logger.warning("Manifest missing required field: %s", field)
                return None

        try:
            manifest = SyncManifest(
                batch_id=manifest_data["batch_id"],
                total_chunks=int(manifest_data["total_chunks"]),
                chunk_size=int(manifest_data["chunk_size"]),
                checksum=manifest_data["checksum"],
                created_at=manifest_data.get("created_at", ""),
                snapshot_count=int(manifest_data.get("snapshot_count", 0)),
                source=manifest_data.get("source", "iran-gateway"),
                target=manifest_data.get("target", "external-server"),
            )
        except (ValueError, TypeError) as exc:
            logger.warning("Invalid manifest data: %s", exc)
            return None

        # Validate manifest integrity
        if manifest.total_chunks <= 0:
            logger.warning("Manifest has invalid total_chunks: %d", manifest.total_chunks)
            return None

        if manifest.chunk_size <= 0:
            logger.warning("Manifest has invalid chunk_size: %d", manifest.chunk_size)
            return None

        if len(manifest.checksum) != 64:
            logger.warning("Manifest has invalid checksum length")
            return None

        return manifest

    # ------------------------------------------------------------------
    # Full batch validation
    # ------------------------------------------------------------------

    def validate_complete_batch(
        self,
        batch: ReceivedBatch,
        manifest: SyncManifest,
    ) -> dict[str, object]:
        """
        Validate a complete batch against its manifest.

        Checks:
        - All chunks present
        - All chunk checksums valid
        - Reassembled data matches manifest checksum

        Args:
            batch: The received batch.
            manifest: The manifest for this batch.

        Returns:
            Dict with validation results.
        """
        results: dict[str, object] = {
            "batch_id": batch.batch_id,
            "manifest_valid": True,
            "all_chunks_present": batch.is_complete,
            "all_checksums_valid": True,
            "final_checksum_valid": False,
            "reassembled_size": 0,
            "errors": [],
        }

        # 1. Check all chunks present
        if not batch.is_complete:
            results["all_chunks_present"] = False
            results["errors"].append(
                f"Missing chunks: {batch.missing_chunks}"
            )
            return results

        # 2. Validate each chunk checksum
        for chunk_num in sorted(batch.chunks.keys()):
            chunk = batch.chunks[chunk_num]
            if not self.validate_chunk_checksum(chunk):
                results["all_checksums_valid"] = False
                results["errors"].append(
                    f"Chunk {chunk_num} has invalid checksum"
                )

        # 3. Reassemble and verify final checksum
        if results["all_checksums_valid"]:
            try:
                reassembled = self.reassemble_batch(batch)
                results["reassembled_size"] = len(reassembled)
                results["final_checksum_valid"] = (
                    self.validate_manifest_checksum(manifest, reassembled)
                )
                if not results["final_checksum_valid"]:
                    results["errors"].append(
                        "Final checksum does not match manifest"
                    )
            except ValueError as exc:
                results["errors"].append(str(exc))

        return results
