# Phase 1: Receiver Persistence Layer — Technical Design

**Date:** 2026-08-01
**Branch:** feature/architecture-v2-sync
**Status:** DRAFT — pending approval

---

## 1. Database Schema Additions

### 1.1 New Tables (additive only, `CREATE TABLE IF NOT EXISTS`)

All new tables go into `core/database/schema.py`'s `SCHEMA_SQL` string, appended at the end.

#### `sync_batches`

Stores batch-level metadata for each received sync batch.

```sql
CREATE TABLE IF NOT EXISTS sync_batches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL UNIQUE,
    total_chunks    INTEGER NOT NULL,
    chunk_size      INTEGER NOT NULL,
    expected_checksum TEXT NOT NULL,
    snapshot_count  INTEGER NOT NULL DEFAULT 0,
    source          TEXT NOT NULL DEFAULT 'iran-gateway',
    target          TEXT NOT NULL DEFAULT 'external-server',
    status          TEXT NOT NULL DEFAULT 'pending',
    received_at     TEXT NOT NULL,
    completed_at    TEXT,
    error_message   TEXT,
    final_checksum  TEXT,
    final_size      INTEGER,
    UNIQUE(batch_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_batches_status ON sync_batches(status);
CREATE INDEX IF NOT EXISTS idx_sync_batches_received_at ON sync_batches(received_at);
CREATE INDEX IF NOT EXISTS idx_sync_batches_source ON sync_batches(source);
```

#### `sync_chunks`

Stores individual chunk payloads and metadata. Payloads are stored as BLOBs.

```sql
CREATE TABLE IF NOT EXISTS sync_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    chunk_number    INTEGER NOT NULL,
    payload         BLOB NOT NULL,
    payload_size    INTEGER NOT NULL,
    checksum        TEXT NOT NULL,
    received_at     TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'iran-gateway',
    FOREIGN KEY(batch_id) REFERENCES sync_batches(batch_id) ON DELETE CASCADE,
    UNIQUE(batch_id, chunk_number)
);

CREATE INDEX IF NOT EXISTS idx_sync_chunks_batch ON sync_chunks(batch_id);
CREATE INDEX IF NOT EXISTS idx_sync_chunks_chunk_number ON sync_chunks(chunk_number);
```

#### `sync_batch_acknowledgements`

Audit trail for every chunk ACK sent back to the sender. Enables replay/debugging.

```sql
CREATE TABLE IF NOT EXISTS sync_batch_acknowledgements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    chunk_number    INTEGER,
    status          TEXT NOT NULL,
    checksum_valid  INTEGER NOT NULL DEFAULT 0,
    message         TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES sync_batches(batch_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sync_ack_batch ON sync_batch_acknowledgements(batch_id);
CREATE INDEX IF NOT EXISTS idx_sync_ack_chunk ON sync_batch_acknowledgements(batch_id, chunk_number);
```

### 1.2 Schema Version Bump

- `SCHEMA_VERSION` in `core/database/schema.py` increments from `2` → `3`.
- The `schema_meta` table is updated via the existing `apply_schema()` path.
- Migration is purely additive — no `DROP`, no `ALTER ... RENAME`, no data deletion.

### 1.3 Why These Tables

| Table | Purpose |
|---|---|
| `sync_batches` | Track batch lifecycle (pending → complete → failed) |
| `sync_chunks` | Persist chunk payloads in DB instead of files |
| `sync_batch_acknowledgements` | Audit trail for sender-facing ACKs |

---

## 2. ReceiverPersistence API

### 2.1 Class Definition

```python
class ReceiverPersistence:
    """Thread-safe persistence layer for received sync batches and chunks."""

    def __init__(self, db: Database) -> None
```

Takes the existing `Database` singleton — no new connection, no new DB file.

### 2.2 Methods

#### Batch Operations

| Method | Signature | Description |
|---|---|---|
| `save_batch` | `(batch: ReceivedBatch) -> None` | Upsert batch metadata. Uses `INSERT OR REPLACE`. |
| `get_batch` | `(batch_id: str) -> Optional[ReceivedBatch]` | Load batch metadata + chunk count. |
| `update_batch_status` | `(batch_id: str, status: str, error_message: Optional[str] = None) -> None` | Update status + optional error. |
| `mark_batch_complete` | `(batch_id: str, final_checksum: str, final_size: int) -> None` | Transition to `complete` with final checksum. |
| `list_batches` | `(status: Optional[str] = None) -> list[ReceivedBatch]` | List batches, optionally filtered by status. |
| `delete_batch` | `(batch_id: str) -> None` | Hard delete batch + chunks (cascade via FK). |

#### Chunk Operations

| Method | Signature | Description |
|---|---|---|
| `save_chunk` | `(chunk: ReceivedChunk) -> bool` | Upsert chunk payload. Returns `True` if new, `False` if duplicate. |
| `get_chunk` | `(batch_id: str, chunk_number: int) -> Optional[ReceivedChunk]` | Load a single chunk by batch + number. |
| `chunk_exists` | `(batch_id: str, chunk_number: int) -> bool` | Check if chunk exists in DB. |
| `list_chunks` | `(batch_id: str) -> list[int]` | Return sorted list of chunk numbers for a batch. |
| `delete_chunks` | `(batch_id: str) -> None` | Delete all chunks for a batch (cascade). |

#### Acknowledgement Operations

| Method | Signature | Description |
|---|---|---|
| `save_ack` | `(ack: SyncAck) -> None` | Persist an ACK record for audit. |
| `get_acks` | `(batch_id: str) -> list[SyncAck]` | Retrieve all ACKs for a batch. |

### 2.3 Design Decisions

- **No ORM** — uses raw SQL via the existing `Database` class. Keeps it lightweight and consistent with the rest of the project.
- **`INSERT OR REPLACE`** for batch upsert — handles re-delivery of manifest data gracefully.
- **`INSERT OR IGNORE`** for chunks — duplicate chunks are silently skipped (idempotency handled at the API layer too).
- **Returns `bool` for `save_chunk`** — caller knows if the chunk was new or a duplicate.

---

## 3. Storage Flow

### 3.1 Current Flow (File-Based)

```
Sender → HTTPS → API endpoint → ReceiverStorage.save_chunk() → .bin file
                                                              → ReceiverStorage.save_batch() → .json file
```

### 3.2 New Flow (DB-Persisted)

```
Sender → HTTPS → API endpoint
                      │
                      ├── 1. Validate chunk checksum (unchanged)
                      ├── 2. Check duplicate via ReceiverPersistence.chunk_exists() (NEW)
                      ├── 3. If new: save chunk to DB via ReceiverPersistence.save_chunk() (NEW)
                      ├── 4. Update batch metadata in DB via ReceiverPersistence.save_batch() (NEW)
                      ├── 5. Persist ACK to DB via ReceiverPersistence.save_ack() (NEW)
                      └── 6. Return ACK to sender (unchanged)
```

### 3.3 Dual-Write During Transition

During the transition period, `ReceiverStorage` (file-based) remains the primary write path for backward compatibility. `ReceiverPersistence` is written in parallel. This ensures:

- No data loss if DB write fails mid-batch.
- File-based storage remains the source of truth until all batches are migrated.
- The API layer calls both `ReceiverStorage` and `ReceiverPersistence` independently.

### 3.4 Migration of Existing File Data

A one-time backfill script reads all existing `.json` batch files and `.bin` chunk files from `data/receiver/` and inserts them into the new DB tables. This runs once on first startup of the persistence layer.

---

## 4. Transaction Strategy

### 4.1 Per-Chunk Transaction

Each chunk write is a single transaction:

```
BEGIN
  1. INSERT OR IGNORE INTO sync_chunks (...) VALUES (...)
  2. INSERT OR REPLACE INTO sync_batches (...) VALUES (...)
  3. INSERT INTO sync_batch_acknowledgements (...) VALUES (...)
COMMIT
```

If any step fails, the entire transaction rolls back — no partial state.

### 4.2 Per-Batch Transaction (Completion)

When a batch is complete and validated:

```
BEGIN
  1. UPDATE sync_batches SET status = 'complete', completed_at = ..., final_checksum = ..., final_size = ...
  2. INSERT INTO sync_batch_acknowledgements (...) VALUES (...)
COMMIT
```

### 4.3 WAL Mode

The existing `Database` class already uses `PRAGMA journal_mode = WAL`. This is critical for the persistence layer because:

- WAL allows concurrent reads during writes (the API can serve status requests while chunks are being persisted).
- WAL provides crash safety — if the process is killed mid-transaction, the DB recovers on next open.

### 4.4 Connection Handling

- Uses the existing `Database` singleton via `get_database()`.
- No new connection pool, no new DB file.
- Each `ReceiverPersistence` method uses `db.transaction()` for write operations and `db.connect()` for read operations.

---

## 5. Failure Recovery

### 5.1 Chunk Write Failure

If a chunk write fails mid-transaction:

- The transaction rolls back automatically (via `Database.transaction()` context manager).
- The API returns `500` to the sender, which triggers a retry.
- The sender's retry mechanism (existing) will re-send the chunk.
- `save_chunk` returns `False` for duplicates, so a retry of an already-persisted chunk is a no-op.

### 5.2 Batch Status Inconsistency

If a batch has chunks in the DB but the batch metadata is missing (e.g., crash after chunk writes but before batch metadata update):

- On next `save_batch` call, `INSERT OR REPLACE` upserts the batch metadata.
- A background reconciliation check (optional, Phase 2) can detect and fix orphaned chunks.

### 5.3 Database Corruption

- SQLite WAL mode + `PRAGMA foreign_keys = ON` provides integrity guarantees.
- The existing `data/database.db` is never deleted or recreated.
- If corruption is detected (`sqlite3.DatabaseError`), the system logs the error and raises — no silent data loss.
- The operator can recover using the standard SQLite `.recover` command or by restoring from a backup.

### 5.4 Duplicate Chunk Handling

- `chunk_exists()` checks the DB before writing.
- If a duplicate is detected, the transaction is not started — the API returns a `duplicate` ACK immediately.
- This avoids unnecessary DB writes and keeps the ACK path fast.

---

## 6. Idempotency Strategy

### 6.1 Chunk-Level Idempotency

- **Key:** `(batch_id, chunk_number)` — unique constraint in `sync_chunks`.
- **Mechanism:** `INSERT OR IGNORE` + `UNIQUE(batch_id, chunk_number)`.
- **Result:** Re-sending the same chunk is a silent no-op. The existing duplicate check in `api.py` (`storage.chunk_exists()`) is replaced by the DB-level check.

### 6.2 Batch-Level Idempotency

- **Key:** `batch_id` — unique constraint in `sync_batches`.
- **Mechanism:** `INSERT OR REPLACE` for batch metadata.
- **Result:** Re-sending a manifest for an existing batch updates metadata (e.g., if the sender retries with updated info) without creating duplicates.

### 6.3 ACK-Level Idempotency

- **Key:** `(batch_id, chunk_number, status)` — no unique constraint, but `save_ack` uses `INSERT` without `OR REPLACE`.
- **Result:** Duplicate ACKs are allowed (they represent the same logical event from the sender's perspective). The audit trail is intentionally append-only.

### 6.4 Why Not a Dedup Token?

The existing `(batch_id, chunk_number)` unique constraint is sufficient for idempotency. Adding a separate dedup token would add complexity without benefit for this phase.

---

## 7. Migration Strategy

### 7.1 Schema Migration (Additive)

1. Increment `SCHEMA_VERSION` from `2` to `3` in `core/database/schema.py`.
2. Append new table DDL (`sync_batches`, `sync_chunks`, `sync_batch_acknowledgements`) to `SCHEMA_SQL`.
3. All DDL uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.
4. The existing `apply_schema()` function handles the version bump automatically.
5. No `ALTER TABLE`, no `DROP TABLE`, no data deletion.

### 7.2 Data Migration (Backfill)

A one-time backfill script `scripts/backfill_sync_persistence.py`:

1. Reads all `.json` batch files from `data/receiver/batches/`.
2. Reads all `.bin` chunk files from `data/receiver/chunks/{batch_id}/`.
3. Inserts them into `sync_batches` and `sync_chunks` tables.
4. Logs progress and any errors.
5. After successful backfill, moves the `data/receiver/` directory to `data/receiver/legacy/` (not deleted).
6. The backfill script is run manually by the operator, not automatically.

### 7.3 Dual-Write Phase

After schema migration and backfill:

1. The API layer writes to both `ReceiverStorage` (files) and `ReceiverPersistence` (DB).
2. This phase runs for at least one production batch cycle.
3. The operator verifies DB data matches file data.
4. After verification, the file-based write path is removed.

### 7.4 Cutover

1. Remove `ReceiverStorage` writes from the API layer.
2. Remove `ReceiverStorage` reads from status endpoint (switch to DB reads).
3. Keep `ReceiverStorage` class in code for now (marked as deprecated) in case rollback is needed.
4. After one week of stable operation, remove `ReceiverStorage` entirely.

### 7.5 Rollback Plan

If the persistence layer causes issues:

1. Revert the API layer to use `ReceiverStorage` only (file-based).
2. The DB tables remain but are unused — no data is lost.
3. The `sync_batches`, `sync_chunks`, and `sync_batch_acknowledgements` tables can be dropped later if needed (`DROP TABLE IF EXISTS`).

### 7.6 Safety Guarantees

| Guarantee | How |
|---|---|
| Never delete `data/database.db` | No code touches the file directly — only via `Database` class |
| Never recreate the database | `Database.__init__` only opens existing or creates new file if missing — never deletes |
| Never require manual DB deletion | All migrations are additive |
| Never create a second DB file | Single `Database` singleton, single path |
| Preserve all existing data | `CREATE TABLE IF NOT EXISTS`, `INSERT OR REPLACE`, no `DROP` |
| Additive column changes only | `ALTER TABLE ADD COLUMN` only when column is missing (checked at runtime) |

---

## Summary

This design extends the existing SQLite database with three new tables for sync persistence, uses the existing `Database` singleton (no new connections or files), and follows a safe additive migration strategy. The persistence layer is designed to be a drop-in replacement for file-based storage with full idempotency, transaction safety, and a clear rollback path.
