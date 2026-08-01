# Sync V1 Design Document
## Incremental Migration — Phase 4 Slice 1

**Date:** 2026-08-01  
**Status:** Draft  
**Scope:** Standalone sync prototype (no receiver API, no DB changes)

---

## 1. Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  BrsProvider    │────▶│  FundCollector  │────▶│  Local JSON     │
│  (existing)     │     │  (NEW)          │     │  Snapshots      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  SyncExporter   │
                        │  (NEW)          │
                        │  - JSON serialize│
                        │  - gzip compress │
                        │  - SHA-256 hash  │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  SyncChunker    │
                        │  (NEW)          │
                        │  - Split 5KB    │
                        │  - Per-chunk    │
                        │    checksum      │
                        │  - Retry metadata│
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Push to        │
                        │  External Server│
                        │  (future V2)    │
                        └─────────────────┘
```

### Step-by-Step

1. **Collector** reads from `BrsProvider.get_symbol()`, `BrsProvider.get_nav()`, `BrsProvider.get_fund_symbols()` — existing interfaces only.
2. **Collector** builds `FundSnapshot` dataclasses from the provider DTOs (`SymbolQuote`, `NavData`).
3. **Collector** stores snapshots as local JSON files in `data/snapshots/` for validation.
4. **Exporter** serializes `FundSnapshot` objects to JSON.
5. **Exporter** compresses the JSON with gzip.
6. **Exporter** computes SHA-256 checksum of the compressed payload.
7. **Chunker** splits the compressed payload into 5KB chunks.
8. **Chunker** attaches per-chunk metadata (index, total, checksum, attempt count).
9. **Chunker** supports retry/resume: pending chunks can be retransmitted without resending the entire batch.

---

## 2. Data Models (Python Dataclasses)

### FundSnapshot

```python
@dataclass(frozen=True)
class FundSnapshot:
    symbol: str
    name: str
    ins_code: str
    isin: Optional[str] = None
    sector: Optional[str] = None
    last_price: Optional[float] = None
    close_price: Optional[float] = None
    yesterday_price: Optional[float] = None
    change_last_pct: Optional[float] = None
    volume: Optional[float] = None
    value: Optional[float] = None
    nav_issue: Optional[float] = None
    nav_redeem: Optional[float] = None
    nav_date: Optional[str] = None
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None
    source: str = "brs"
    captured_at: str = "<ISO-8601>"
    raw: dict = {}  # stripped from serialization
```

**Key design decisions:**
- Frozen dataclass — immutable once created
- `raw` field excluded from JSON serialization to keep payloads small
- Order book reduced to top-of-book only (best bid/ask) — lightweight
- Source defaults to `"brs"` — identifies data origin

### SyncBatch

```python
@dataclass(frozen=True)
class SyncBatch:
    batch_id: str          # SHA-256 hash, 16 chars
    source: str = "iran-gateway"
    target: str = "external-server"
    snapshots: tuple[FundSnapshot, ...]
    created_at: str        # ISO-8601
    checksum: str          # SHA-256 of all snapshot checksums
    compressed_size: int   # bytes after gzip
    status: str = "pending"  # pending | sent | acked | failed
```

**Key design decisions:**
- Batch ID is deterministic (hash of symbols + timestamp + count)
- Checksum is hash of all individual snapshot checksums — enables dedup on receiver side
- Status tracks delivery state

### SyncChunk

```python
@dataclass(frozen=True)
class SyncChunk:
    chunk_id: str          # SHA-256 hash, 12 chars
    batch_id: str
    chunk_index: int
    total_chunks: int
    data: bytes            # compressed payload slice
    checksum: str          # parent batch checksum
    size_bytes: int
    attempts: int = 0
    last_attempt_at: Optional[str]
    status: str = "pending"  # pending | sent | acked | failed
```

**Key design decisions:**
- Each chunk independently checksummed (SHA-256 of its data)
- `attempts` counter enables retry limits
- `last_attempt_at` timestamp enables stale-chunk detection
- Status tracks per-chunk delivery state

---

## 3. Failure Handling

### Failure Scenarios

| Scenario | Detection | Response |
|----------|-----------|----------|
| BRS provider returns error | Exception from `get_symbol()`/`get_nav()` | Skip symbol, log warning, continue with others |
| Empty snapshot list | `len(snapshots) == 0` | Raise `ValueError` in exporter |
| Compression failure | `gzip.compress()` exception | Log error, mark batch as failed |
| Chunk size mismatch | `len(chunk.data) > chunk_size` | Log error, reject chunk |
| Checksum mismatch | `SHA-256(data) != expected` | Mark chunk as failed, retry |
| Missing chunks on reassembly | `expected_indices - actual_indices` | Raise `ValueError`, request retransmission |
| Network failure during push | Connection error | Mark pending chunks, retry later |
| Duplicate batch received | Same `batch_id` in received batches | Return 200 OK with `duplicate: true` |

### Retry Strategy

1. **Per-chunk retry:** Each chunk tracks its own `attempts` count.
2. **Max retries:** Configurable (default 3). After max retries, chunk status → `"failed"`.
3. **Resume:** On restart, `get_pending_chunks()` returns only non-acked chunks.
4. **Backoff:** Exponential backoff between retries (1s, 2s, 4s).
5. **Batch-level retry:** If all chunks in a batch fail, the entire batch is retried.

### Idempotency

- Batch ID is deterministic → duplicate pushes are detected
- Receiver checks `batch_id` before processing
- Duplicate batches return `status: "duplicate"` without reprocessing

---

## 4. Retry Logic

### Chunker Retry/Resume Metadata

```python
# Each chunk carries its own retry state:
chunk.attempts      # Number of send attempts
chunk.last_attempt_at  # ISO-8601 timestamp of last attempt
chunk.status        # pending | sent | acked | failed
```

### Retry Flow

```
1. Collect pending chunks (status != "acked")
2. For each pending chunk:
   a. If attempts >= MAX_RETRIES → mark failed, skip
   b. Send chunk to receiver
   c. If success → mark acked
   d. If failure → increment attempts, update last_attempt_at
3. Re-check for pending chunks
4. If any pending → go to step 2
5. If all acked or all failed → batch complete
```

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SYNC_CHUNK_SIZE` | 5120 | Max chunk size in bytes (5KB) |
| `SYNC_BATCH_SIZE` | 100 | Max snapshots per batch |
| `SYNC_TARGET_URL` | `""` | Receiver URL (empty = disabled) |
| `SYNC_ENABLED` | `false` | Enable/disable sync collector |
| `SYNC_SNAPSHOT_TTL_HOURS` | 24 | Hours before local snapshots are cleaned up |

---

## 5. Database Schema (Deferred — V2)

> **Note:** This schema is documented for future reference but is NOT implemented in V1.
> V1 uses local JSON file storage only. No database tables are created.

### Planned Tables (V2)

```sql
-- Iran server: tracks records pending sync
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    batch_id TEXT,
    synced INTEGER NOT NULL DEFAULT 0,
    sync_attempts INTEGER NOT NULL DEFAULT 0,
    last_sync_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Iran server: batch metadata
CREATE TABLE IF NOT EXISTS sync_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL UNIQUE,
    table_name TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    compressed_size INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    checksum TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    synced_at TEXT,
    error_message TEXT
);

-- External server: deduplication
CREATE TABLE IF NOT EXISTS received_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL UNIQUE,
    source_server TEXT NOT NULL DEFAULT 'iran-gateway',
    record_count INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed INTEGER NOT NULL DEFAULT 0
);

-- External server: delivery tracking
CREATE TABLE IF NOT EXISTS sync_acknowledgements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    message TEXT,
    received_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Migration Strategy (V2)

- All new tables use `CREATE TABLE IF NOT EXISTS` — idempotent
- No existing tables are modified
- Migration runs automatically on application startup
- No data migration needed — new tables start empty
- Rollback: `DROP TABLE` the new tables (no data loss risk)

---

## 6. Local File Storage (V1)

### Snapshot Storage

- **Location:** `data/snapshots/` (configurable via `SNAPSHOT_DIR`)
- **Format:** JSON, one file per snapshot
- **Naming:** `{symbol}_{YYYYMMDD_HHMMSS}.json`
- **Cleanup:** Automatic removal of files older than `SYNC_SNAPSHOT_TTL_HOURS` (default 24h)

### Why File-Based in V1?

1. **No database migration** — zero risk to existing data
2. **No persistence layer changes** — no production DB impact
3. **Easy validation** — snapshots are human-readable JSON files
4. **No new dependencies** — uses standard library only
5. **Rollback is trivial** — delete the `services/sync/` directory

### File Layout

```
data/snapshots/
├── فندق_ملت_20260801_100000.json
├── فندق_توسع_20260801_100001.json
├── صندوق_پارس_20260801_100002.json
└── ...
```

---

## 7. Rollback Plan

### V1 Rollback (Trivial)

Since V1 adds only new files and modifies only `config.py` and `.env.example`:

```bash
# Delete the sync module
rm -rf services/sync/

# Revert config.py changes (git checkout)
git checkout config.py

# Revert .env.example changes
git checkout .env.example

# No database changes to revert
# No services to restart
# No data to clean up
```

### V2 Rollback (Full Architecture)

If the full V2 architecture is ever deployed and needs rollback:

```bash
# Delete the branch
git branch -D feature/architecture-v2-sync

# Revert to original branch
git checkout agent/v1.5-development

# Delete new services
rm -rf services/collector/ services/sync_worker/ services/receiver/

# Drop new database tables (if V2 tables were created)
sqlite3 data/database.db "DROP TABLE IF EXISTS sync_queue; DROP TABLE IF EXISTS sync_batches; DROP TABLE IF EXISTS received_batches; DROP TABLE IF EXISTS sync_acknowledgements;"

# No data loss — existing tables untouched
```

### Rollback Verification

After V1 rollback, confirm:
1. `git status` shows clean working tree on original branch
2. `python -c "from services.sync import FundCollector"` raises `ModuleNotFoundError`
3. Existing BRS provider still works: `python -c "from services.providers.brs_provider import BrsProvider"` succeeds
4. No snapshot files remain in `data/snapshots/`

---

## 8. Configuration

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_ENABLED` | `false` | Enable/disable the sync collector |
| `SYNC_CHUNK_SIZE` | `5120` | Maximum chunk size in bytes (5KB) |
| `SYNC_BATCH_SIZE` | `100` | Maximum snapshots per batch |
| `SYNC_TARGET_URL` | `""` | Receiver URL for push sync (empty = disabled) |
| `SYNC_SNAPSHOT_TTL_HOURS` | `24` | Hours before local snapshots are auto-cleaned |

### Config.py Additions

```python
# --- Sync V1 (incremental migration) ---
SYNC_CHUNK_SIZE: int = _env_int("SYNC_CHUNK_SIZE", 5120)
SYNC_BATCH_SIZE: int = _env_int("SYNC_BATCH_SIZE", 100)
SYNC_TARGET_URL: str = _env("SYNC_TARGET_URL", "")
SYNC_ENABLED: bool = _env("SYNC_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
SYNC_SNAPSHOT_TTL_HOURS: int = _env_int("SYNC_SNAPSHOT_TTL_HOURS", 24)
```

---

## 9. Testing Strategy

### Unit Tests (services/sync/)

| Test | Purpose |
|------|---------|
| `test_models.py` | Verify dataclass creation, JSON serialization, checksum |
| `test_collector.py` | Verify snapshot creation from mock provider data |
| `test_exporter.py` | Verify JSON serialization, gzip compression, checksum |
| `test_chunker.py` | Verify chunking, reassembly, retry metadata |

### Integration Tests (local only)

| Test | Purpose |
|------|---------|
| End-to-end pipeline | Collector → Exporter → Chunker → Reassemble → Verify |
| Compression ratio | Verify gzip reduces payload by >50% |
| Checksum validation | Verify checksum matches after round-trip |
| Chunk reassembly | Verify all chunks reassemble correctly |

### Test Data

Use mock `FundSnapshot` objects with realistic data:
- Symbol: `"صندوق ملت"`
- Ins Code: `"1234567890"`
- NAV: issue=10000, redeem=9950
- Price: last=10500, close=10400
- Volume: 1000000

---

## 10. Security Considerations

- **No secrets in code:** All configuration comes from environment variables
- **Checksums for integrity:** SHA-256 ensures data hasn't been tampered with in transit
- **No hardcoded URLs:** Target URL comes from environment
- **File permissions:** Snapshot files are readable only by the application user
- **No external exposure:** V1 has no HTTP server — data stays local until explicitly pushed

---

## 11. Monitoring and Observability (Future)

V1 does not include monitoring. V2 should add:
- Sync latency metrics (time from collection to delivery)
- Compression ratio tracking
- Chunk failure rate
- Batch success/failure rate
- Snapshot storage usage

---

*Design version: 1.0*  
*Status: Draft — pending implementation review*
