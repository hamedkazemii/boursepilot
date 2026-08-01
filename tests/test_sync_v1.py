"""
Sync V1 — Local unit tests.

Tests the standalone sync prototype without any external dependencies.
No database, no network calls, no service restarts.
"""

from __future__ import annotations

import json
import gzip
import hashlib
import tempfile
from pathlib import Path

import pytest

from services.sync.models import FundSnapshot, SyncBatch, SyncChunk, SyncManifest
from services.sync.exporter import SyncExporter
from services.sync.chunker import SyncChunker
from services.sync.providers import MarketSnapshotProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def sample_snapshot() -> FundSnapshot:
    return FundSnapshot(
        symbol="صندوق ملت",
        name="صندوق سرمایه‌گذاری ملت",
        ins_code="1234567890",
        isin="IR1234567890",
        sector="صندوق‌ها",
        last_price=10500.0,
        close_price=10400.0,
        yesterday_price=10350.0,
        change_last_pct=1.45,
        volume=1000000.0,
        value=10500000000.0,
        nav_issue=10000.0,
        nav_redeem=9950.0,
        nav_date="2026-08-01",
        best_bid=10499.0,
        best_ask=10501.0,
        bid_volume=500000.0,
        ask_volume=300000.0,
        source="brs",
        raw={"symbol": "صندوق ملت", "ins_code": "1234567890"},
    )


def sample_snapshots(count: int = 3) -> list[FundSnapshot]:
    return [
        FundSnapshot(
            symbol=f"صندوق {i}",
            name=f"صندوق تست {i}",
            ins_code=f"123456789{i}",
            last_price=10000.0 + i * 100,
            close_price=9900.0 + i * 100,
            volume=1000000.0,
            source="brs",
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# FundSnapshot tests
# ---------------------------------------------------------------------------

class TestFundSnapshot:
    def test_creation(self):
        snap = sample_snapshot()
        assert snap.symbol == "صندوق ملت"
        assert snap.ins_code == "1234567890"
        assert snap.last_price == 10500.0

    def test_to_dict(self):
        snap = sample_snapshot()
        d = snap.to_dict()
        assert d["symbol"] == "صندوق ملت"
        assert d["ins_code"] == "1234567890"
        assert "raw" in d
        assert d["raw"] == {}  # raw stripped from serialization

    def test_to_json(self):
        snap = sample_snapshot()
        j = snap.to_json()
        parsed = json.loads(j)
        assert parsed["symbol"] == "صندوق ملت"

    def test_checksum(self):
        snap = sample_snapshot()
        cs = snap.checksum()
        assert len(cs) == 64  # SHA-256 hex length
        assert cs == snap.checksum()  # deterministic

    def test_immutable(self):
        snap = sample_snapshot()
        with pytest.raises(AttributeError):
            snap.symbol = "changed"  # type: ignore[misc]

    def test_frozen_dataclass(self):
        snap = sample_snapshot()
        assert isinstance(snap, FundSnapshot)


# ---------------------------------------------------------------------------
# SyncBatch tests
# ---------------------------------------------------------------------------

class TestSyncBatch:
    def test_creation(self):
        snaps = sample_snapshots(3)
        batch = SyncBatch(
            batch_id="test-batch-001",
            snapshots=tuple(snaps),
        )
        assert batch.batch_id == "test-batch-001"
        assert len(batch.snapshots) == 3
        assert batch.status == "pending"

    def test_checksum_auto_generated(self):
        snaps = sample_snapshots(2)
        batch = SyncBatch(
            batch_id="test-batch-002",
            snapshots=tuple(snaps),
        )
        assert batch.checksum != ""
        assert len(batch.checksum) == 64

    def test_to_dict(self):
        snaps = sample_snapshots(2)
        batch = SyncBatch(
            batch_id="test-batch-003",
            snapshots=tuple(snaps),
        )
        d = batch.to_dict()
        assert d["batch_id"] == "test-batch-003"
        assert d["snapshot_count"] == 2
        assert d["status"] == "pending"

    def test_to_json(self):
        snaps = sample_snapshots(1)
        batch = SyncBatch(
            batch_id="test-batch-004",
            snapshots=tuple(snaps),
        )
        j = batch.to_json()
        parsed = json.loads(j)
        assert parsed["batch_id"] == "test-batch-004"

    def test_empty_snapshots_raises(self):
        with pytest.raises(ValueError):
            SyncExporter().export_batch([])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SyncChunk tests
# ---------------------------------------------------------------------------

class TestSyncChunk:
    def test_creation(self):
        data = b"hello world"
        chunk = SyncChunk(
            chunk_id="chunk-001",
            batch_id="batch-001",
            chunk_index=0,
            total_chunks=1,
            data=data,
        )
        assert chunk.chunk_id == "chunk-001"
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 1
        assert chunk.size_bytes == 11
        assert chunk.checksum != ""
        assert chunk.status == "pending"

    def test_checksum_is_sha256(self):
        data = b"test data"
        chunk = SyncChunk(
            chunk_id="chunk-002",
            batch_id="batch-001",
            chunk_index=0,
            total_chunks=1,
            data=data,
        )
        expected = hashlib.sha256(data).hexdigest()
        assert chunk.checksum == expected

    def test_to_dict(self):
        data = b"test"
        chunk = SyncChunk(
            chunk_id="chunk-003",
            batch_id="batch-001",
            chunk_index=0,
            total_chunks=1,
            data=data,
        )
        d = chunk.to_dict()
        assert d["chunk_id"] == "chunk-003"
        assert d["chunk_index"] == 0
        assert d["size_bytes"] == 4


# ---------------------------------------------------------------------------
# SyncExporter tests
# ---------------------------------------------------------------------------

class TestSyncExporter:
    def test_export_batch(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(3)
        batch = exporter.export_batch(snaps, batch_id="test-batch-005")

        assert batch.batch_id == "test-batch-005"
        assert len(batch.snapshots) == 3
        assert batch.compressed_size > 0
        assert batch.checksum != ""
        assert batch.status == "pending"

    def test_export_single(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snap = sample_snapshot()
        batch = exporter.export_single(snap, chunk_size=5120)

        assert len(batch.snapshots) == 1
        assert batch.compressed_size > 0

    def test_json_serialization(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(2)
        json_payload = exporter._serialize(snaps)
        parsed = json.loads(json_payload)
        assert len(parsed) == 2
        assert parsed[0]["symbol"] == "صندوق 0"

    def test_gzip_compression(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(5)
        batch = exporter.export_batch(snaps, batch_id="test-batch-006", chunk_size=5120)

        # Get chunks from batch
        chunks = getattr(batch, "_chunks", [])
        assert len(chunks) > 0

        # Verify we can decompress
        all_data = b"".join(c.data for c in chunks)
        decompressed = exporter.decompress(all_data)
        parsed = json.loads(decompressed)
        assert len(parsed) == 5

    def test_checksum_verification(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(2)
        batch = exporter.export_batch(snaps, batch_id="test-batch-007", chunk_size=5120)

        chunks = getattr(batch, "_chunks", [])
        all_data = b"".join(c.data for c in chunks)

        assert exporter.verify_checksum(all_data, batch.checksum) is True

    def test_checksum_mismatch(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(2)
        batch = exporter.export_batch(snaps, batch_id="test-batch-008", chunk_size=5120)

        # Wrong checksum should fail
        assert exporter.verify_checksum(b"wrong data", batch.checksum) is False

    def test_validate_export(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(3)
        batch = exporter.export_batch(snaps, batch_id="test-batch-009", chunk_size=5120)

        results = exporter.validate_export(batch)
        assert results["checksum_valid"] is True
        assert results["reassembly_valid"] is True
        assert results["decompression_valid"] is True
        assert len(results["errors"]) == 0

    def test_batch_id_generation(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(2)
        batch = exporter.export_batch(snaps, chunk_size=5120)

        assert len(batch.batch_id) == 16  # first 16 chars of SHA-256

    def test_compression_ratio(self):
        exporter = SyncExporter(default_chunk_size=5120)
        snaps = sample_snapshots(10)
        batch = exporter.export_batch(snaps, chunk_size=5120)

        # Get original JSON size
        json_payload = exporter._serialize(snaps)
        original_size = len(json_payload)
        compressed_size = batch.compressed_size

        # Compression should reduce size (for repetitive data)
        # At minimum, compressed should not be larger than original
        assert compressed_size <= original_size * 1.1  # allow some overhead


# ---------------------------------------------------------------------------
# SyncChunker tests
# ---------------------------------------------------------------------------

class TestSyncChunker:
    def test_chunk_split(self):
        chunker = SyncChunker(chunk_size=5)  # 5 bytes per chunk
        data = b"hello world this is a test"
        chunks = chunker.chunk(data, batch_id="test-batch-010", checksum="abc123")
        manifest = chunker.last_manifest

        assert len(chunks) > 1  # should be split into multiple chunks
        assert all(c.chunk_index < len(chunks) for c in chunks)
        assert all(c.total_chunks == len(chunks) for c in chunks)
        assert isinstance(manifest, SyncManifest)

    def test_chunk_returns_manifest(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello world"
        chunks = chunker.chunk(data, batch_id="test-batch-manifest", checksum="def456")
        manifest = chunker.last_manifest

        assert isinstance(manifest, SyncManifest)
        assert manifest.batch_id == "test-batch-manifest"
        assert manifest.total_chunks == len(chunks)
        assert manifest.chunk_size == 5120
        assert manifest.checksum == "def456"

    def test_manifest_verify_chunk(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello world"
        chunks = chunker.chunk(data, batch_id="test-batch-verify", checksum="ghi789")
        manifest = chunker.last_manifest

        assert manifest.verify_chunk(chunks[0]) is True

    def test_manifest_verify_chunk_wrong_batch(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello world"
        chunks = chunker.chunk(data, batch_id="test-batch-wrong", checksum="jkl012")
        manifest = chunker.last_manifest

        wrong_manifest = SyncManifest(
            batch_id="wrong-batch",
            total_chunks=manifest.total_chunks,
            chunk_size=manifest.chunk_size,
            checksum=manifest.checksum,
        )
        assert wrong_manifest.verify_chunk(chunks[0]) is False

    def test_chunk_reassembly(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello world this is a test payload for chunking"
        chunks = chunker.chunk(data, batch_id="test-batch-011", checksum="def456")
        manifest = chunker.last_manifest

        assert manifest is not None
        assert manifest.batch_id == "test-batch-011"
        assert manifest.total_chunks == 1

        reassembled = chunker.reassemble(chunks)
        assert reassembled == data

    def test_chunk_reassembly_unsorted(self):
        """Chunks can be reassembled in any order."""
        chunker = SyncChunker(chunk_size=10)
        data = b"hello world this is a test"
        chunks = chunker.chunk(data, batch_id="test-batch-012", checksum="ghi789")
        manifest = chunker.last_manifest

        assert manifest is not None
        assert manifest.total_chunks == 3

        # Shuffle chunks
        import random
        shuffled = list(chunks)
        random.shuffle(shuffled)

        reassembled = chunker.reassemble(shuffled)
        assert reassembled == data

    def test_chunk_missing_raises(self):
        chunker = SyncChunker(chunk_size=10)
        data = b"hello world this is a test"
        chunks = chunker.chunk(data, batch_id="test-batch-013", checksum="jkl012")

        # Remove one chunk
        incomplete = chunks[:-1]
        with pytest.raises(ValueError, match="Missing chunks"):
            chunker.reassemble(incomplete)

    def test_empty_data_raises(self):
        chunker = SyncChunker(chunk_size=5120)
        with pytest.raises(ValueError, match="empty"):
            chunker.chunk(b"", batch_id="test-batch-014", checksum="mno345")

    def test_zero_chunk_size_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SyncChunker(chunk_size=0)

    def test_negative_chunk_size_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SyncChunker(chunk_size=-1)

    def test_default_chunk_size(self):
        chunker = SyncChunker()
        assert chunker.chunk_size == 5120  # 5KB default

    def test_pending_chunks(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello world"
        chunks = chunker.chunk(data, batch_id="test-batch-015", checksum="pqr678")
        manifest = chunker.last_manifest

        assert manifest is not None
        assert manifest.total_chunks == 1

        # All chunks should be pending initially
        pending = chunker.get_pending_chunks(chunks)
        assert len(pending) == len(chunks)

    def test_mark_chunk_sent(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello"
        chunks = chunker.chunk(data, batch_id="test-batch-016", checksum="stu901")
        manifest = chunker.last_manifest

        assert manifest is not None
        chunk = chunks[0]
        sent = chunker.mark_chunk_sent(chunk)
        assert sent.status == "sent"
        assert sent.attempts == 1

    def test_mark_chunk_acked(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello"
        chunks = chunker.chunk(data, batch_id="test-batch-017", checksum="vwx234")
        manifest = chunker.last_manifest

        assert manifest is not None
        chunk = chunks[0]
        sent = chunker.mark_chunk_sent(chunk)
        acked = chunker.mark_chunk_acked(sent)
        assert acked.status == "acked"
        assert acked.attempts == 1

    def test_mark_chunk_failed(self):
        chunker = SyncChunker(chunk_size=5120)
        data = b"hello"
        chunks = chunker.chunk(data, batch_id="test-batch-018", checksum="yza567")
        manifest = chunker.last_manifest

        assert manifest is not None
        chunk = chunks[0]
        failed = chunker.mark_chunk_failed(chunk, error_message="network error")
        assert failed.status == "failed"

    def test_retry_resume(self):
        """Simulate interrupted transfer and resume."""
        chunker = SyncChunker(chunk_size=5)
        data = b"hello world this is a test"
        chunks = chunker.chunk(data, batch_id="test-batch-019", checksum="bcd890")
        manifest = chunker.last_manifest

        assert isinstance(manifest, SyncManifest)

        # Simulate: first 2 chunks sent and acked, rest pending
        updated = []
        for i, chunk in enumerate(chunks):
            if i < 2:
                updated.append(chunker.mark_chunk_acked(chunker.mark_chunk_sent(chunk)))
            else:
                updated.append(chunk)

        # Resume: get pending chunks
        pending = chunker.get_pending_chunks(updated)
        assert len(pending) == len(chunks) - 2

        # Reassemble all chunks (including acked ones)
        reassembled = chunker.reassemble(updated)
        assert reassembled == data


# ---------------------------------------------------------------------------
# Integration tests (end-to-end pipeline)
# ---------------------------------------------------------------------------

class TestSyncPipeline:
    def test_full_pipeline(self):
        """Test the complete pipeline: snapshots → export → chunk → reassemble → validate."""
        exporter = SyncExporter(default_chunk_size=5120)
        chunker = SyncChunker(chunk_size=5120)

        # 1. Create snapshots
        snaps = sample_snapshots(5)

        # 2. Export to batch
        batch = exporter.export_batch(snaps, batch_id="pipeline-batch-001", chunk_size=5120)

        # 3. Get chunks
        chunks = getattr(batch, "_chunks", [])
        assert len(chunks) > 0

        # 4. Reassemble
        reassembled = chunker.reassemble(chunks)

        # 5. Decompress
        decompressed = exporter.decompress(reassembled)
        parsed = json.loads(decompressed)
        assert len(parsed) == 5

        # 6. Validate
        results = exporter.validate_export(batch)
        assert results["checksum_valid"] is True
        assert results["reassembly_valid"] is True
        assert results["decompression_valid"] is True
        assert len(results["errors"]) == 0

    def test_pipeline_with_large_snapshot_count(self):
        """Test pipeline with 20 snapshots to verify chunking works."""
        exporter = SyncExporter(default_chunk_size=100)  # small chunks for testing
        chunker = SyncChunker(chunk_size=100)

        snaps = sample_snapshots(20)
        batch = exporter.export_batch(snaps, batch_id="pipeline-batch-002", chunk_size=100)

        chunks = getattr(batch, "_chunks", [])
        assert len(chunks) > 1  # should be multiple chunks

        # Reassemble and verify
        reassembled = chunker.reassemble(chunks)
        decompressed = exporter.decompress(reassembled)
        parsed = json.loads(decompressed)
        assert len(parsed) == 20

        # Validate
        results = exporter.validate_export(batch)
        assert results["checksum_valid"] is True

    def test_pipeline_empty_snapshots_raises(self):
        """Empty snapshot list should raise ValueError."""
        exporter = SyncExporter(default_chunk_size=5120)
        with pytest.raises(ValueError, match="empty"):
            exporter.export_batch([])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# MarketSnapshotProvider interface tests
# ---------------------------------------------------------------------------

class MockProvider(MarketSnapshotProvider):
    """Mock provider for testing the interface."""

    def __init__(self, symbols=None, funds=None):
        self._symbols = symbols or []
        self._funds = funds or []
        self._data = {}

    def get_symbol(self, symbol):
        if symbol in self._data:
            return self._data[symbol]
        raise ValueError(f"Symbol not found: {symbol}")

    def get_nav(self, symbol):
        return self._data.get(symbol + "_nav", None)

    def get_all_symbols(self, symbol_type=None):
        return self._symbols

    def get_fund_symbols(self, symbol_type=None):
        return self._funds


class TestMarketSnapshotProvider:
    def test_interface_is_abstract(self):
        """MarketSnapshotProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MarketSnapshotProvider()

    def test_mock_provider_implements_interface(self):
        """A mock provider that implements all methods works."""
        provider = MockProvider()
        assert isinstance(provider, MarketSnapshotProvider)

    def test_mock_provider_get_symbol(self):
        """Mock provider returns data for known symbols."""
        mock_quote = object()
        provider = MockProvider()
        provider._data["test"] = mock_quote
        result = provider.get_symbol("test")
        assert result is mock_quote

    def test_mock_provider_get_symbol_missing(self):
        """Mock provider raises ValueError for unknown symbols."""
        provider = MockProvider()
        with pytest.raises(ValueError, match="not found"):
            provider.get_symbol("missing")

    def test_mock_provider_get_nav(self):
        """Mock provider returns NAV data."""
        mock_nav = object()
        provider = MockProvider()
        provider._data["test_nav"] = mock_nav
        result = provider.get_nav("test")
        assert result is mock_nav

    def test_mock_provider_get_nav_none(self):
        """Mock provider returns None when NAV is not available."""
        provider = MockProvider()
        result = provider.get_nav("test")
        assert result is None

    def test_mock_provider_get_all_symbols(self):
        """Mock provider returns all symbols."""
        symbols = ["sym1", "sym2"]
        provider = MockProvider(symbols=symbols)
        result = provider.get_all_symbols()
        assert result == symbols

    def test_mock_provider_get_fund_symbols(self):
        """Mock provider returns fund symbols."""
        funds = ["fund1", "fund2"]
        provider = MockProvider(funds=funds)
        result = provider.get_fund_symbols()
        assert result == funds


# ---------------------------------------------------------------------------
# SyncManifest tests
# ---------------------------------------------------------------------------

class TestSyncManifest:
    def test_creation(self):
        manifest = SyncManifest(
            batch_id="test-manifest-001",
            total_chunks=5,
            chunk_size=5120,
            checksum="abc123",
        )
        assert manifest.batch_id == "test-manifest-001"
        assert manifest.total_chunks == 5
        assert manifest.chunk_size == 5120
        assert manifest.checksum == "abc123"
        assert manifest.snapshot_count == 0
        assert manifest.source == "iran-gateway"
        assert manifest.target == "external-server"

    def test_to_dict(self):
        manifest = SyncManifest(
            batch_id="test-manifest-002",
            total_chunks=3,
            chunk_size=5120,
            checksum="def456",
            snapshot_count=10,
            source="test-source",
            target="test-target",
        )
        d = manifest.to_dict()
        assert d["batch_id"] == "test-manifest-002"
        assert d["total_chunks"] == 3
        assert d["snapshot_count"] == 10
        assert d["source"] == "test-source"
        assert d["target"] == "test-target"

    def test_to_json(self):
        manifest = SyncManifest(
            batch_id="test-manifest-003",
            total_chunks=2,
            chunk_size=5120,
            checksum="ghi789",
        )
        j = manifest.to_json()
        parsed = json.loads(j)
        assert parsed["batch_id"] == "test-manifest-003"
        assert parsed["total_chunks"] == 2

    def test_verify_chunk_valid(self):
        manifest = SyncManifest(
            batch_id="test-manifest-004",
            total_chunks=3,
            chunk_size=5120,
            checksum="jkl012",
        )
        chunk = SyncChunk(
            chunk_id="chunk-001",
            batch_id="test-manifest-004",
            chunk_index=0,
            total_chunks=3,
            data=b"test",
            checksum="jkl012",
        )
        assert manifest.verify_chunk(chunk) is True

    def test_verify_chunk_wrong_batch_id(self):
        manifest = SyncManifest(
            batch_id="test-manifest-005",
            total_chunks=3,
            chunk_size=5120,
            checksum="mno345",
        )
        chunk = SyncChunk(
            chunk_id="chunk-002",
            batch_id="wrong-batch",
            chunk_index=0,
            total_chunks=3,
            data=b"test",
            checksum="mno345",
        )
        assert manifest.verify_chunk(chunk) is False

    def test_verify_chunk_wrong_checksum(self):
        manifest = SyncManifest(
            batch_id="test-manifest-006",
            total_chunks=3,
            chunk_size=5120,
            checksum="pqr678",
        )
        chunk = SyncChunk(
            chunk_id="chunk-003",
            batch_id="test-manifest-006",
            chunk_index=0,
            total_chunks=3,
            data=b"test",
            checksum="wrong-checksum",
        )
        assert manifest.verify_chunk(chunk) is False

    def test_immutable(self):
        manifest = SyncManifest(
            batch_id="test-manifest-007",
            total_chunks=1,
            chunk_size=5120,
            checksum="stu901",
        )
        with pytest.raises(AttributeError):
            manifest.batch_id = "changed"  # type: ignore[misc]

    def test_frozen_dataclass(self):
        manifest = SyncManifest(
            batch_id="test-manifest-008",
            total_chunks=1,
            chunk_size=5120,
            checksum="vwx234",
        )
        assert isinstance(manifest, SyncManifest)
