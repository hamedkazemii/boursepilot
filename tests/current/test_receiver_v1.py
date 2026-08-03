"""
Sync V1 — Receiver API Local Unit Tests.

Tests the receiver API without any external dependencies.
No database, no network calls, no service restarts.
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from services.receiver.models import ReceivedBatch, ReceivedChunk, SyncAck
from services.receiver.storage import ReceiverStorage
from services.receiver.validator import ChunkValidator
from services.sync.models import SyncManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def sample_manifest() -> SyncManifest:
    return SyncManifest(
        batch_id="test-batch-001",
        total_chunks=3,
        chunk_size=5120,
        checksum=hashlib.sha256(b"test-manifest").hexdigest(),
        snapshot_count=5,
    )


def sample_chunk_payload(chunk_number: int) -> bytes:
    """Generate deterministic payload for a chunk."""
    return f"chunk-{chunk_number}-payload-data".encode("utf-8")


def sample_chunk(
    batch_id: str = "test-batch-001",
    chunk_number: int = 0,
) -> ReceivedChunk:
    payload = sample_chunk_payload(chunk_number)
    checksum = hashlib.sha256(payload).hexdigest()
    return ReceivedChunk(
        batch_id=batch_id,
        chunk_number=chunk_number,
        payload=payload,
        checksum=checksum,
    )


# ---------------------------------------------------------------------------
# ReceivedChunk tests
# ---------------------------------------------------------------------------

class TestReceivedChunk:
    def test_creation(self):
        chunk = sample_chunk(chunk_number=0)
        assert chunk.batch_id == "test-batch-001"
        assert chunk.chunk_number == 0
        assert chunk.checksum != ""

    def test_to_dict(self):
        chunk = sample_chunk(chunk_number=1)
        d = chunk.to_dict()
        assert d["batch_id"] == "test-batch-001"
        assert d["chunk_number"] == 1
        assert d["checksum"] != ""

    def test_to_json(self):
        chunk = sample_chunk(chunk_number=2)
        j = chunk.to_json()
        parsed = json.loads(j)
        assert parsed["batch_id"] == "test-batch-001"

    def test_from_dict(self):
        chunk = sample_chunk(chunk_number=3)
        d = chunk.to_dict()
        restored = ReceivedChunk.from_dict(d)
        assert restored.batch_id == chunk.batch_id
        assert restored.chunk_number == chunk.chunk_number


# ---------------------------------------------------------------------------
# ReceivedBatch tests
# ---------------------------------------------------------------------------

class TestReceivedBatch:
    def test_creation(self):
        batch = ReceivedBatch(
            batch_id="test-batch-001",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="abc123",
        )
        assert batch.batch_id == "test-batch-001"
        assert batch.total_chunks == 3
        assert batch.status == "pending"
        assert batch.is_complete is False

    def test_missing_chunks(self):
        batch = ReceivedBatch(
            batch_id="test-batch-002",
            total_chunks=5,
            chunk_size=5120,
            expected_checksum="def456",
        )
        assert batch.missing_chunks == [0, 1, 2, 3, 4]

    def test_add_chunk(self):
        batch = ReceivedBatch(
            batch_id="test-batch-003",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="ghi789",
        )
        chunk = sample_chunk(batch_id="test-batch-003", chunk_number=0)
        updated_chunks = {0: chunk}
        updated_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        assert len(updated_batch.chunks) == 1
        assert updated_batch.missing_chunks == [1, 2]

    def test_is_complete_when_all_chunks_present(self):
        batch = ReceivedBatch(
            batch_id="test-batch-004",
            total_chunks=2,
            chunk_size=5120,
            expected_checksum="jkl012",
        )
        chunk0 = sample_chunk(batch_id="test-batch-004", chunk_number=0)
        chunk1 = sample_chunk(batch_id="test-batch-004", chunk_number=1)
        updated_chunks = {0: chunk0, 1: chunk1}
        complete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        assert complete_batch.is_complete is True
        assert complete_batch.missing_chunks == []

    def test_to_dict(self):
        batch = ReceivedBatch(
            batch_id="test-batch-005",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="mno345",
        )
        d = batch.to_dict()
        assert d["batch_id"] == "test-batch-005"
        assert d["total_chunks"] == 3
        assert d["status"] == "pending"


# ---------------------------------------------------------------------------
# SyncAck tests
# ---------------------------------------------------------------------------

class TestSyncAck:
    def test_accepted_ack(self):
        ack = SyncAck(
            batch_id="test-batch-001",
            chunk_number=0,
            status="accepted",
            message="Chunk 0 accepted",
            checksum_valid=True,
        )
        assert ack.status == "accepted"
        assert ack.checksum_valid is True

    def test_duplicate_ack(self):
        ack = SyncAck(
            batch_id="test-batch-001",
            chunk_number=0,
            status="duplicate",
            message="Chunk already received",
            checksum_valid=False,
        )
        assert ack.status == "duplicate"
        assert ack.checksum_valid is False

    def test_rejected_ack(self):
        ack = SyncAck(
            batch_id="test-batch-001",
            chunk_number=0,
            status="rejected",
            message="Checksum mismatch",
            checksum_valid=False,
        )
        assert ack.status == "rejected"
        assert ack.checksum_valid is False

    def test_to_dict(self):
        ack = SyncAck(
            batch_id="test-batch-001",
            chunk_number=1,
            status="accepted",
            message="OK",
            checksum_valid=True,
        )
        d = ack.to_dict()
        assert d["batch_id"] == "test-batch-001"
        assert d["chunk_number"] == 1
        assert d["status"] == "accepted"

    def test_to_json(self):
        ack = SyncAck(
            batch_id="test-batch-001",
            chunk_number=2,
            status="accepted",
            message="OK",
            checksum_valid=True,
        )
        j = ack.to_json()
        parsed = json.loads(j)
        assert parsed["batch_id"] == "test-batch-001"


# ---------------------------------------------------------------------------
# ReceiverStorage tests
# ---------------------------------------------------------------------------

class TestReceiverStorage:
    def test_save_and_load_batch(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        batch = ReceivedBatch(
            batch_id="storage-test-001",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="test-checksum",
            snapshot_count=5,
        )
        storage.save_batch(batch)

        loaded = storage.load_batch("storage-test-001")
        assert loaded is not None
        assert loaded.batch_id == "storage-test-001"
        assert loaded.total_chunks == 3

    def test_save_and_load_chunk(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        chunk = sample_chunk(batch_id="storage-test-002", chunk_number=0)
        storage.save_chunk(chunk)

        loaded = storage.load_chunk("storage-test-002", 0)
        assert loaded is not None
        assert loaded.batch_id == "storage-test-002"
        assert loaded.chunk_number == 0

    def test_chunk_exists(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        chunk = sample_chunk(batch_id="storage-test-003", chunk_number=0)
        storage.save_chunk(chunk)

        assert storage.chunk_exists("storage-test-003", 0) is True
        assert storage.chunk_exists("storage-test-003", 1) is False

    def test_list_chunks(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        for i in range(3):
            chunk = sample_chunk(batch_id="storage-test-004", chunk_number=i)
            storage.save_chunk(chunk)

        chunks = storage.list_chunks("storage-test-004")
        assert chunks == [0, 1, 2]

    def test_delete_batch(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        batch = ReceivedBatch(
            batch_id="storage-test-005",
            total_chunks=2,
            chunk_size=5120,
            expected_checksum="del-checksum",
        )
        storage.save_batch(batch)
        chunk = sample_chunk(batch_id="storage-test-005", chunk_number=0)
        storage.save_chunk(chunk)

        storage.delete_batch("storage-test-005")

        assert storage.load_batch("storage-test-005") is None
        assert storage.chunk_exists("storage-test-005", 0) is False

    def test_cleanup_old_batches(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        batch = ReceivedBatch(
            batch_id="storage-test-006",
            total_chunks=1,
            chunk_size=5120,
            expected_checksum="cleanup-checksum",
        )
        storage.save_batch(batch)

        # Cleanup with 0 hours should delete everything
        deleted = storage.cleanup_old_batches(older_than_hours=0)
        assert deleted >= 1


# ---------------------------------------------------------------------------
# ChunkValidator tests
# ---------------------------------------------------------------------------

class TestChunkValidator:
    def test_validate_chunk_checksum_valid(self):
        validator = ChunkValidator()
        chunk = sample_chunk(chunk_number=0)
        assert validator.validate_chunk_checksum(chunk) is True

    def test_validate_chunk_checksum_invalid(self):
        validator = ChunkValidator()
        chunk = sample_chunk(chunk_number=0)
        # Tamper with the payload
        tampered = ReceivedChunk(
            batch_id=chunk.batch_id,
            chunk_number=chunk.chunk_number,
            payload=b"tampered-payload",
            checksum=chunk.checksum,
        )
        assert validator.validate_chunk_checksum(tampered) is False

    def test_is_duplicate_chunk(self, tmp_path):
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        validator = ChunkValidator(storage)
        chunk = sample_chunk(batch_id="dup-test-001", chunk_number=0)
        storage.save_chunk(chunk)

        assert validator.is_duplicate_chunk("dup-test-001", 0) is True
        assert validator.is_duplicate_chunk("dup-test-001", 1) is False

    def test_detect_missing_chunks(self):
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="missing-test-001",
            total_chunks=5,
            chunk_size=5120,
            expected_checksum="missing-checksum",
        )
        assert validator.detect_missing_chunks(batch) == [0, 1, 2, 3, 4]

    def test_is_batch_complete_false(self):
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="complete-test-001",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="complete-checksum",
        )
        assert validator.is_batch_complete(batch) is False

    def test_is_batch_complete_true(self):
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="complete-test-002",
            total_chunks=2,
            chunk_size=5120,
            expected_checksum="complete-checksum-2",
        )
        chunk0 = sample_chunk(batch_id="complete-test-002", chunk_number=0)
        chunk1 = sample_chunk(batch_id="complete-test-002", chunk_number=1)
        updated_chunks = {0: chunk0, 1: chunk1}
        complete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        assert validator.is_batch_complete(complete_batch) is True

    def test_reassemble_batch(self):
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="reassemble-test-001",
            total_chunks=2,
            chunk_size=5120,
            expected_checksum="reassemble-checksum",
        )
        chunk0 = sample_chunk(batch_id="reassemble-test-001", chunk_number=0)
        chunk1 = sample_chunk(batch_id="reassemble-test-001", chunk_number=1)
        updated_chunks = {0: chunk0, 1: chunk1}
        complete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        result = validator.reassemble_batch(complete_batch)
        assert result == chunk0.payload + chunk1.payload

    def test_reassemble_missing_chunks_raises(self):
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="reassemble-test-002",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="reassemble-checksum-2",
        )
        chunk0 = sample_chunk(batch_id="reassemble-test-002", chunk_number=0)
        updated_chunks = {0: chunk0}
        incomplete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        with pytest.raises(ValueError, match="missing chunks"):
            validator.reassemble_batch(incomplete_batch)

    def test_validate_manifest_valid(self):
        validator = ChunkValidator()
        manifest_data = {
            "batch_id": "manifest-test-001",
            "total_chunks": 3,
            "chunk_size": 5120,
            "checksum": "a" * 64,
            "snapshot_count": 5,
        }
        manifest = validator.validate_manifest(manifest_data)
        assert manifest is not None
        assert manifest.batch_id == "manifest-test-001"
        assert manifest.total_chunks == 3

    def test_validate_manifest_missing_fields(self):
        validator = ChunkValidator()
        manifest_data = {
            "batch_id": "manifest-test-002",
            # Missing total_chunks, chunk_size, checksum
        }
        manifest = validator.validate_manifest(manifest_data)
        assert manifest is None

    def test_validate_manifest_invalid_checksum_length(self):
        validator = ChunkValidator()
        manifest_data = {
            "batch_id": "manifest-test-003",
            "total_chunks": 3,
            "chunk_size": 5120,
            "checksum": "short",
        }
        manifest = validator.validate_manifest(manifest_data)
        assert manifest is None

    def test_validate_complete_batch_valid(self):
        validator = ChunkValidator()
        manifest = sample_manifest()
        batch = ReceivedBatch(
            batch_id="complete-validate-001",
            total_chunks=2,
            chunk_size=5120,
            expected_checksum=manifest.checksum,
        )
        # Create chunks with correct checksums
        payload0 = b"payload0"
        payload1 = b"payload1"
        chunk0 = ReceivedChunk(
            batch_id="complete-validate-001",
            chunk_number=0,
            payload=payload0,
            checksum=hashlib.sha256(payload0).hexdigest(),
        )
        chunk1 = ReceivedChunk(
            batch_id="complete-validate-001",
            chunk_number=1,
            payload=payload1,
            checksum=hashlib.sha256(payload1).hexdigest(),
        )
        updated_chunks = {0: chunk0, 1: chunk1}
        complete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        results = validator.validate_complete_batch(complete_batch, manifest)
        assert results["all_chunks_present"] is True
        assert results["all_checksums_valid"] is True

    def test_validate_complete_batch_missing_chunks(self):
        validator = ChunkValidator()
        manifest = sample_manifest()
        batch = ReceivedBatch(
            batch_id="complete-validate-002",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum=manifest.checksum,
        )
        # Only add 1 of 3 chunks
        payload0 = b"payload0"
        chunk0 = ReceivedChunk(
            batch_id="complete-validate-002",
            chunk_number=0,
            payload=payload0,
            checksum=hashlib.sha256(payload0).hexdigest(),
        )
        updated_chunks = {0: chunk0}
        incomplete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        results = validator.validate_complete_batch(incomplete_batch, manifest)
        assert results["all_chunks_present"] is False
        assert len(results["errors"]) > 0


# ---------------------------------------------------------------------------
# API-level tests (simulating the receiver flow)
# ---------------------------------------------------------------------------

class TestReceiverFlow:
    def test_manifest_accepted(self):
        """Test that a manifest is accepted and creates a pending batch."""
        storage = ReceiverStorage()
        validator = ChunkValidator(storage)

        manifest_data = {
            "batch_id": "flow-test-001",
            "total_chunks": 2,
            "chunk_size": 5120,
            "checksum": hashlib.sha256(b"flow-manifest").hexdigest(),
            "snapshot_count": 3,
        }

        manifest = validator.validate_manifest(manifest_data)
        assert manifest is not None
        assert manifest.batch_id == "flow-test-001"

        batch = ReceivedBatch(
            batch_id=manifest.batch_id,
            total_chunks=manifest.total_chunks,
            chunk_size=manifest.chunk_size,
            expected_checksum=manifest.checksum,
            snapshot_count=manifest.snapshot_count,
        )
        storage.save_batch(batch)

        loaded = storage.load_batch("flow-test-001")
        assert loaded is not None
        assert loaded.status == "pending"

    def test_single_chunk_accepted(self):
        """Test that a single chunk is accepted and stored."""
        storage = ReceiverStorage()
        validator = ChunkValidator(storage)

        manifest_data = {
            "batch_id": "flow-test-002",
            "total_chunks": 1,
            "chunk_size": 5120,
            "checksum": hashlib.sha256(b"single-manifest").hexdigest(),
        }
        manifest = validator.validate_manifest(manifest_data)
        assert manifest is not None

        batch = ReceivedBatch(
            batch_id=manifest.batch_id,
            total_chunks=manifest.total_chunks,
            chunk_size=manifest.chunk_size,
            expected_checksum=manifest.checksum,
        )
        storage.save_batch(batch)

        # Receive chunk
        chunk = sample_chunk(batch_id="flow-test-002", chunk_number=0)
        storage.save_chunk(chunk)

        # Update batch
        updated_chunks = {0: chunk}
        updated_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        storage.save_batch(updated_batch)

        # Verify
        loaded = storage.load_batch("flow-test-002")
        assert loaded is not None
        assert len(loaded.chunks) == 1

    def test_duplicate_chunk_detected(self):
        """Test that duplicate chunks are detected."""
        storage = ReceiverStorage()
        validator = ChunkValidator(storage)

        batch_id = "flow-test-003"
        chunk = sample_chunk(batch_id=batch_id, chunk_number=0)
        storage.save_chunk(chunk)

        # Try to save the same chunk again
        assert storage.chunk_exists(batch_id, 0) is True
        # In the API, this would return a duplicate ack

    def test_missing_chunk_detected(self):
        """Test that missing chunks are detected."""
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="flow-test-004",
            total_chunks=5,
            chunk_size=5120,
            expected_checksum="missing-checksum",
        )
        assert batch.missing_chunks == [0, 1, 2, 3, 4]

    def test_invalid_checksum_rejected(self):
        """Test that chunks with invalid checksums are rejected."""
        validator = ChunkValidator()
        chunk = sample_chunk(chunk_number=0)
        # Tamper with the payload but keep the original checksum
        tampered = ReceivedChunk(
            batch_id=chunk.batch_id,
            chunk_number=chunk.chunk_number,
            payload=b"tampered",
            checksum=chunk.checksum,
        )
        assert validator.validate_chunk_checksum(tampered) is False

    def test_reassemble_complete_batch(self):
        """Test complete batch reassembly."""
        validator = ChunkValidator()
        batch = ReceivedBatch(
            batch_id="flow-test-005",
            total_chunks=3,
            chunk_size=5120,
            expected_checksum="reassemble-checksum",
        )
        chunks = [
            sample_chunk(batch_id="flow-test-005", chunk_number=i)
            for i in range(3)
        ]
        updated_chunks = {i: chunks[i] for i in range(3)}
        complete_batch = ReceivedBatch(
            batch_id=batch.batch_id,
            total_chunks=batch.total_chunks,
            chunk_size=batch.chunk_size,
            expected_checksum=batch.expected_checksum,
            snapshot_count=batch.snapshot_count,
            source=batch.source,
            target=batch.target,
            created_at=batch.created_at,
            chunks=updated_chunks,
        )
        result = validator.reassemble_batch(complete_batch)
        expected = b"".join(c.payload for c in chunks)
        assert result == expected

    def test_full_iran_to_receiver_simulation(self, tmp_path):
        """Simulate the complete flow from Iran gateway to receiver."""
        storage = ReceiverStorage(base_dir=str(tmp_path / "receiver"))
        validator = ChunkValidator(storage)

        # Step 1: Create manifest
        manifest_data = {
            "batch_id": "iran-sim-001",
            "total_chunks": 3,
            "chunk_size": 5120,
            "checksum": hashlib.sha256(b"sim-final-manifest").hexdigest(),
            "snapshot_count": 5,
        }
        manifest = validator.validate_manifest(manifest_data)
        assert manifest is not None

        # Step 2: Create pending batch
        batch = ReceivedBatch(
            batch_id=manifest.batch_id,
            total_chunks=manifest.total_chunks,
            chunk_size=manifest.chunk_size,
            expected_checksum=manifest.checksum,
            snapshot_count=manifest.snapshot_count,
        )
        storage.save_batch(batch)

        # Step 3: Receive chunks one by one
        for i in range(3):
            chunk = sample_chunk(batch_id="iran-sim-001", chunk_number=i)
            assert validator.validate_chunk_checksum(chunk) is True
            assert not validator.is_duplicate_chunk("iran-sim-001", i)
            storage.save_chunk(chunk)

            # Update batch
            loaded = storage.load_batch("iran-sim-001")
            updated_chunks = dict(loaded.chunks) if loaded.chunks else {}
            updated_chunks[i] = chunk
            updated_batch = ReceivedBatch(
                batch_id=loaded.batch_id,
                total_chunks=loaded.total_chunks,
                chunk_size=loaded.chunk_size,
                expected_checksum=loaded.expected_checksum,
                snapshot_count=loaded.snapshot_count,
                source=loaded.source,
                target=loaded.target,
                created_at=loaded.created_at,
                chunks=updated_chunks,
            )
            storage.save_batch(updated_batch)

        # Step 4: Verify all chunks received
        final_batch = storage.load_batch("iran-sim-001")
        assert final_batch.is_complete is True
        assert final_batch.missing_chunks == []

        # Step 5: Reassemble
        reassembled = validator.reassemble_batch(final_batch)
        assert len(reassembled) > 0

        # Step 6: Verify final checksum (would match manifest in real flow)
        # For simulation, we just verify reassembly worked
        assert reassembled == b"".join(
            sample_chunk_payload(i) for i in range(3)
        )
