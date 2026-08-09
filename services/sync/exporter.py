"""
Sync V1 — SyncExporter

Creates JSON snapshot batches, gzip compression, and checksum
generation for the sync pipeline.

No database dependencies. No production persistence changes.
All output is in-memory bytes or local temp files for validation.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
from typing import Optional

from services.sync.models import FundSnapshot, SyncBatch, SyncChunk, SyncManifest

logger = logging.getLogger(__name__)


class SyncExporter:
    """
    Exports fund snapshots into compressed, checksummed batches
    ready for chunked transfer.

    Pipeline:
        FundSnapshots → JSON → gzip → checksum → chunks
    """

    def __init__(self, default_chunk_size: int = 5120) -> None:
        """
        Args:
            default_chunk_size: Maximum chunk size in bytes.
                Default 5120 = 5KB.
        """
        self.default_chunk_size = default_chunk_size

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_batch(
        self,
        snapshots: list[FundSnapshot],
        batch_id: Optional[str] = None,
        chunk_size: Optional[int] = None,
    ) -> SyncBatch:
        """
        Export a list of FundSnapshots into a compressed, chunked batch.

        Args:
            snapshots: List of FundSnapshot objects to export.
            batch_id: Optional batch identifier. Auto-generated if None.
            chunk_size: Optional chunk size override in bytes.

        Returns:
            SyncBatch with compressed payload and chunk metadata.
        """
        from services.sync.chunker import SyncChunker

        if not snapshots:
            raise ValueError("Cannot export empty snapshot list")

        batch_id = batch_id or self._generate_batch_id(snapshots)
        chunk_size = chunk_size or self.default_chunk_size

        # Step 1: Serialize to JSON
        json_payload = self._serialize(snapshots)
        logger.info(
            "Serialized %d snapshots → %d bytes JSON",
            len(snapshots),
            len(json_payload),
        )

        # Step 2: Compress with gzip
        compressed = self._compress(json_payload)
        logger.info(
            "Compressed → %d bytes (%.1f%% reduction)",
            len(compressed),
            (1 - len(compressed) / len(json_payload)) * 100
            if len(json_payload) > 0
            else 0,
        )

        # Step 3: Generate checksum
        checksum = self._checksum(compressed)

        # Step 4: Create batch metadata
        batch = SyncBatch(
            batch_id=batch_id,
            snapshots=tuple(snapshots),
            checksum=checksum,
            compressed_size=len(compressed),
            compressed=compressed,
        )

        # Step 5: Chunk the compressed payload
        chunker = SyncChunker(chunk_size=chunk_size)
        chunks = chunker.chunk(
            data=compressed,
            batch_id=batch_id,
            checksum=checksum,
        )

        # Retrieve manifest from chunker and update snapshot count
        manifest = chunker.last_manifest
        if manifest is not None:
            object.__setattr__(manifest, "snapshot_count", len(snapshots))

        # Step 6: Generate manifest
        manifest = SyncManifest(
            batch_id=batch_id,
            total_chunks=len(chunks),
            chunk_size=chunk_size,
            checksum=checksum,
            snapshot_count=len(snapshots),
        )

        logger.info(
            "Batch %s: %d snapshots, %d bytes compressed, %d chunks",
            batch_id,
            len(snapshots),
            len(compressed),
            len(chunks),
        )

        # Store chunk metadata and manifest on the batch for reference
        object.__setattr__(batch, "_chunks", chunks)
        object.__setattr__(batch, "_manifest", manifest)

        return batch

    def export_single(
        self,
        snapshot: FundSnapshot,
        chunk_size: Optional[int] = None,
    ) -> SyncBatch:
        """
        Export a single FundSnapshot as a batch.

        Convenience wrapper around export_batch().
        """
        return self.export_batch([snapshot], chunk_size=chunk_size)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize(self, snapshots: list[FundSnapshot]) -> str:
        """Convert snapshots to JSON string."""
        return json.dumps(
            [s.to_dict() for s in snapshots],
            ensure_ascii=False,
            default=str,
        )

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    def _compress(self, payload: str) -> bytes:
        """Compress a string payload using gzip."""
        return gzip.compress(payload.encode("utf-8"))

    def decompress(self, compressed: bytes) -> str:
        """Decompress gzip bytes back to string."""
        return gzip.decompress(compressed).decode("utf-8")

    # ------------------------------------------------------------------
    # Checksum
    # ------------------------------------------------------------------

    def _checksum(self, data: bytes) -> str:
        """Generate SHA-256 hex checksum of bytes."""
        return hashlib.sha256(data).hexdigest()

    def verify_checksum(
        self, data: bytes, expected_checksum: str
    ) -> bool:
        """Verify that data matches the expected checksum."""
        return self._checksum(data) == expected_checksum

    # ------------------------------------------------------------------
    # Batch ID generation
    # ------------------------------------------------------------------

    def _generate_batch_id(self, snapshots: list[FundSnapshot]) -> str:
        """Generate a unique batch ID from snapshot symbols and timestamp."""
        from datetime import datetime, timezone

        symbols = "_".join(s.symbol for s in snapshots[:5])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        raw = f"{symbols}_{timestamp}_{len(snapshots)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Validation (local file-based)
    # ------------------------------------------------------------------

    def validate_export(self, batch: SyncBatch) -> dict[str, object]:
        """
        Validate an exported batch without sending it.

        Checks:
        - Checksum matches compressed data
        - Chunks can be reassembled
        - Reassembled data decompresses correctly
        - All snapshots are present

        Returns:
            Dict with validation results.
        """
        chunks = getattr(batch, "_chunks", [])

        results: dict[str, object] = {
            "batch_id": batch.batch_id,
            "snapshot_count": len(batch.snapshots),
            "compressed_size": batch.compressed_size,
            "chunk_count": len(chunks),
            "checksum_valid": False,
            "reassembly_valid": False,
            "decompression_valid": False,
            "errors": [],
        }

        # 1. Checksum validation
        if chunks:
            all_data = b"".join(c.data for c in chunks)
            results["checksum_valid"] = self.verify_checksum(
                all_data,
                batch.checksum,
            )
        else:
            results["errors"].append("No chunks found")

        # 4. Manifest validation
        manifest = getattr(batch, "_manifest", None)
        if manifest is not None:
            results["manifest_valid"] = True
            results["manifest"] = manifest.to_dict()
        else:
            results["manifest_valid"] = False
            results["errors"].append("No manifest found")

        # 2. Reassembly validation
        if chunks:
            try:
                reassembled = b"".join(c.data for c in chunks)
                results["reassembly_valid"] = len(reassembled) == batch.compressed_size
            except Exception as exc:  # noqa: BLE001
                results["errors"].append(f"Reassembly failed: {exc}")

        # 3. Decompression validation
        if chunks and results["reassembly_valid"]:
            try:
                reassembled = b"".join(c.data for c in chunks)
                decompressed = self.decompress(reassembled)
                parsed = json.loads(decompressed)
                results["decompression_valid"] = len(parsed) == len(batch.snapshots)
            except Exception as exc:  # noqa: BLE001
                results["errors"].append(f"Decompression failed: {exc}")

        return results
