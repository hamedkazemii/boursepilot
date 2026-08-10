"""
Sync V1 — ReceiverProcessor

Processes complete sync batches: decompress, parse, persist to database.
Runs after ChunkValidator confirms batch is complete and valid.
"""

from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core.database.connection import get_database
from core.database.schema import apply_schema
from services.receiver.models import ReceivedBatch
from services.receiver.storage import ReceiverStorage
from services.sync.exporter import SyncExporter

logger = logging.getLogger(__name__)


class ReceiverProcessor:
    """
    Processes completed sync batches into the database.

    Flow:
    1. Batch marked 'complete' in received_batches table
    2. Processor loads chunks from storage
    3. Reassembles + decompresses payload
    4. Parses FundSnapshot objects
    5. Upserts into funds, market_snapshot, history tables
    6. Marks batch as 'processed'
    """

    def __init__(self, storage: Optional[ReceiverStorage] = None) -> None:
        self.storage = storage or ReceiverStorage()
        self.exporter = SyncExporter()
        self.db = get_database()
        # Schema is applied automatically on first connection via Database._init_schema()

    def process_batch(self, batch_id: str) -> dict[str, object]:
        """
        Process a completed batch: decompress, parse, persist.

        Returns dict with processing results.
        """
        results: dict[str, object] = {
            "batch_id": batch_id,
            "status": "pending",
            "snapshots_processed": 0,
            "funds_upserted": 0,
            "market_snapshot_saved": False,
            "history_records": 0,
            "errors": [],
        }

        # Load batch from storage
        batch = self.storage.load_batch(batch_id)
        if batch is None:
            results["errors"].append(f"Batch {batch_id} not found in storage")
            results["status"] = "failed"
            return results

        if batch.status != "complete":
            results["errors"].append(f"Batch {batch_id} not complete (status={batch.status})")
            results["status"] = "failed"
            return results

        # Load all chunks
        chunks = self.storage.load_all_chunks(batch_id)
        if not chunks:
            results["errors"].append(f"No chunks found for batch {batch_id}")
            results["status"] = "failed"
            return results

        # Reassemble compressed payload
        try:
            compressed = self._reassemble_chunks(batch, chunks)
        except Exception as exc:
            results["errors"].append(f"Reassembly failed: {exc}")
            results["status"] = "failed"
            return results

        # Verify checksum
        if not self.exporter.verify_checksum(compressed, batch.expected_checksum):
            results["errors"].append("Final checksum mismatch after reassembly")
            results["status"] = "failed"
            return results

        # Decompress
        try:
            json_payload = gzip.decompress(compressed).decode("utf-8")
            snapshots_data = json.loads(json_payload)
        except Exception as exc:
            results["errors"].append(f"Decompression/JSON parse failed: {exc}")
            results["status"] = "failed"
            return results

        # Parse snapshots
        from services.sync.models import FundSnapshot
        snapshots: list[FundSnapshot] = []
        for item in snapshots_data:
            try:
                snapshots.append(FundSnapshot(**item))
            except Exception as exc:
                results["errors"].append(f"Snapshot parse error: {exc}")

        if not snapshots:
            results["errors"].append("No valid snapshots parsed")
            results["status"] = "failed"
            return results

        # Persist to database
        try:
            funds_count = self._upsert_funds(snapshots)
            results["funds_upserted"] = funds_count

            snapshot_result = self._save_market_snapshot(batch, snapshots)
            results["market_snapshot_saved"] = snapshot_result.get("saved", False)

            history_count = self._save_history(snapshots, batch)
            results["history_records"] = history_count

            results["snapshots_processed"] = len(snapshots)
            results["status"] = "processed"
        except Exception as exc:
            results["errors"].append(f"Database persistence failed: {exc}")
            results["status"] = "failed"

        # Mark batch as processed in database
        if results["status"] == "processed":
            self._mark_batch_processed(batch_id)

        logger.info(
            "Processed batch %s: %d snapshots, %d funds, %d history records",
            batch_id,
            results["snapshots_processed"],
            results["funds_upserted"],
            results["history_records"],
        )

        return results

    def _reassemble_chunks(self, batch: ReceivedBatch, chunks: list) -> bytes:
        """Reassemble chunks into compressed payload."""
        # Sort by chunk_number
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_number)

        # Validate each chunk checksum
        from hashlib import sha256
        for chunk in sorted_chunks:
            expected = sha256(chunk.payload).hexdigest()
            if chunk.checksum != expected:
                raise ValueError(f"Chunk {chunk.chunk_number} checksum mismatch")

        return b"".join(c.payload for c in sorted_chunks)

    def _upsert_funds(self, snapshots: list) -> int:
        """Upsert fund metadata into funds table."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        with self.db.transaction() as conn:
            for s in snapshots:
                conn.execute(
                    """
                    INSERT INTO funds (symbol, name, isin, sector, sector_id, board, ins_code, updated_at, first_seen_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        name=excluded.name,
                        isin=excluded.isin,
                        sector=excluded.sector,
                        sector_id=excluded.sector_id,
                        board=excluded.board,
                        ins_code=excluded.ins_code,
                        updated_at=excluded.updated_at,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        s.symbol,
                        s.name,
                        getattr(s, "isin", None),
                        getattr(s, "sector", None),
                        getattr(s, "sector_id", None),
                        getattr(s, "board", None),
                        getattr(s, "ins_code", ""),
                        now,
                        now,
                        now,
                    ),
                )
                count += 1
        return count

    def _save_market_snapshot(self, batch: ReceivedBatch, snapshots: list) -> dict:
        """Save market snapshot summary."""
        from core.analytics.market_summary import build_market_summary, MarketSummary
        from core.scoring.score_engine import ScoreEngine

        # Build assessments for summary
        engine = ScoreEngine()
        assessments = [engine.assess(self._snapshot_to_quote(s)) for s in snapshots]

        summary = build_market_summary(assessments)

        trade_date = batch.created_at[:10] if batch.created_at else datetime.now(timezone.utc).date().isoformat()

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO market_snapshot (
                    snapshot_at, trade_date, funds_count, market_status,
                    market_power, best_group, worst_group,
                    total_value, total_volume, avg_change_pct, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.created_at or datetime.now(timezone.utc).isoformat(),
                    trade_date,
                    len(snapshots),
                    summary.market_status,
                    summary.market_power,
                    summary.best_group,
                    summary.worst_group,
                    summary.total_value,
                    None,  # total_volume not in MarketSummary
                    summary.avg_change_pct,
                    json.dumps(summary.to_dict(), ensure_ascii=False, default=str),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return {"saved": True}

    def _snapshot_to_quote(self, snapshot):
        """Convert FundSnapshot to provider-like SymbolQuote for scoring."""
        from services.providers.models import SymbolQuote, OrderBookSnapshot, MoneyFlowSnapshot
        return SymbolQuote(
            symbol=snapshot.symbol,
            name=snapshot.name,
            ins_code=snapshot.ins_code or "",
            isin=getattr(snapshot, "isin", None),
            sector=snapshot.sector,
            sector_id=getattr(snapshot, "sector_id", None),
            board=snapshot.sector,  # use sector as board fallback
            state=None,
            last_price=snapshot.last_price,
            close_price=snapshot.close_price,
            yesterday_price=snapshot.yesterday_price,
            open_price=snapshot.close_price,  # FundSnapshot has no open_price; use close_price
            change_last=snapshot.change_last_pct,
            change_last_pct=snapshot.change_last_pct,
            change_close=snapshot.change_last_pct,
            change_close_pct=snapshot.change_last_pct,
            volume=snapshot.volume,
            value=snapshot.value,
            trade_count=None,
            avg_volume_1m=None,
            low=snapshot.last_price,
            high=snapshot.last_price,
            threshold_min=None,
            threshold_max=None,
            market_value=snapshot.value,
            shares=None,
            time=None,
            date=None,
            orderbook=OrderBookSnapshot(),
            money_flow=MoneyFlowSnapshot(),
            is_fund_like=True,
            raw={},
        )

    def _save_history(self, snapshots: list, batch: ReceivedBatch) -> int:
        """Save daily history records."""
        trade_date = batch.created_at[:10] if batch.created_at else datetime.now(timezone.utc).date().isoformat()
        now = datetime.now(timezone.utc).isoformat()
        count = 0

        with self.db.transaction() as conn:
            for s in snapshots:
                # Get fund_id from funds table
                fund_row = conn.execute(
                    "SELECT id FROM funds WHERE symbol = ?",
                    (s.symbol,)
                ).fetchone()
                
                if not fund_row:
                    logger.warning(f"Fund {s.symbol} not found in funds table, skipping history")
                    continue
                
                fund_id = fund_row["id"]
                
                conn.execute(
                    """
                    INSERT INTO history (
                        fund_id, trade_date, close_price, open_price,
                        high_price, low_price, yesterday_price,
                        change_pct, volume, value,
                        last_price, trade_count, source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fund_id, trade_date) DO UPDATE SET
                        close_price=excluded.close_price,
                        open_price=excluded.open_price,
                        high_price=excluded.high_price,
                        low_price=excluded.low_price,
                        yesterday_price=excluded.yesterday_price,
                        change_pct=excluded.change_pct,
                        volume=excluded.volume,
                        value=excluded.value,
                        last_price=excluded.last_price,
                        trade_count=excluded.trade_count
                    """,
                    (
                        fund_id,
                        trade_date,
                        s.close_price,
                        s.close_price,  # use close_price as open_price fallback
                        s.last_price,   # use last_price as high_price fallback
                        s.last_price,   # use last_price as low_price fallback
                        s.yesterday_price,
                        s.change_last_pct,  # change_last_pct is the closest
                        s.volume,
                        s.value,
                        s.last_price,
                        0,  # trade_count
                        "brs",  # source
                        now,
                    ),
                )
                count += 1
        return count

    def _mark_batch_processed(self, batch_id: str) -> None:
        """Mark batch as processed in database."""
        with self.db.transaction() as conn:
            # Check if batch exists in database
            existing = conn.execute(
                "SELECT id FROM received_batches WHERE batch_id = ?",
                (batch_id,)
            ).fetchone()
            
            if existing:
                conn.execute(
                    "UPDATE received_batches SET processed = 1 WHERE batch_id = ?",
                    (batch_id,),
                )
            else:
                # Insert batch record
                from services.receiver.storage import ReceiverStorage
                storage = ReceiverStorage()
                batch = storage.load_batch(batch_id)
                if batch:
                    conn.execute(
                        """
                        INSERT INTO received_batches (
                            batch_id, source_server, total_chunks, chunk_size,
                            record_count, checksum, status, completed_at,
                            error_message, received_at, processed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            batch.batch_id,
                            batch.source,
                            batch.total_chunks,
                            batch.chunk_size,
                            batch.snapshot_count,
                            batch.expected_checksum,
                            batch.status,
                            batch.completed_at,
                            batch.error_message,
                            batch.created_at,
                            1,
                        ),
                    )