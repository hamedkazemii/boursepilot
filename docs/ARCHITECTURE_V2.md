# BoursePilot Architecture V2 — Async Sync Design

**Date:** 2026-08-01  
**Branch:** `feature/architecture-v2-sync`  
**Status:** Design Document — Not Yet Implemented  
**Replaces:** V1 Synchronous Pull Architecture

---

## 1. Design Principles

1. **No large GET requests between servers** — All data transfer is push-based, chunked, and compressed.
2. **External server never depends on live Iran API** — External server operates entirely from its local database.
3. **Resilient sync** — Retry, resume, acknowledgement, duplicate protection built into every transfer.
4. **Iran collector is self-sufficient** — Iran server collects and normalizes data independently.
5. **Ranking and Telegram work from external database only** — No live Iran API calls needed for these services.

---

## 2. Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IRAN SERVER (89.44.241.230)                      │
│                                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ BRS API     │───▶│ Collector    │───▶│ Local SQLite │                  │
│  │ (external)  │    │ Service      │    │ (local DB)   │                  │
│  └─────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                  │                          │
│                                         ┌────────▼────────┐                │
│                                         │ Sync Worker     │                │
│                                         │ (reads unsynced │                │
│                                         │  records,       │                │
│                                         │  gzip, chunks,  │                │
│                                         │  pushes to      │                │
│                                         │  External)      │                │
│                                         └────────┬────────┘                │
│                                                  │                          │
│                                         ┌────────▼────────┐                │
│                                         │ Compressed      │                │
│                                         │ Small Chunks    │                │
│                                         │ (push to Ext.)  │                │
│                                         └────────┬────────┘                │
└─────────────────────────────────────────────────┼──────────────────────────┘
                                                  │
                              PUSH (POST /sync/batch)
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVER (82.115.8.100)                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Receiver API (FastAPI)                         │   │
│  │                                                                     │   │
│  │  POST /sync/batch    ← Receive compressed chunks from Iran         │   │
│  │  GET  /sync/status    ← Query sync progress                        │   │
│  │  POST /sync/ack       ← Acknowledge received batch                 │   │
│  │                                                                     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                    ┌────────────▼────────────┐                             │
│                    │   External Database     │                             │
│                    │   (SQLite, same schema  │                             │
│                    │    + sync tracking)     │                             │
│                    └────────────┬────────────┘                             │
│                                 │                                          │
│          ┌──────────────────────┼──────────────────────┐                   │
│          │                      │                      │                   │
│          ▼                      ▼                      ▼                   │
│  ┌───────────────┐    ┌────────────────┐    ┌────────────────┐            │
│  │ Ranking       │    │ Telegram Bot   │    │ API Services   │            │
│  │ Engine        │    │                │    │ (FastAPI 8000) │            │
│  │ (reads local  │    │ (reads local   │    │                │            │
│  │  DB only)     │    │  DB only)      │    │                │            │
│  └───────────────┘    └────────────────┘    └────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Services

### 3.1 Collector Service (Iran Server)

**Responsibilities:**
- Fetch data from BRS API (`AllSymbols.php`, `Symbol.php`, `Nav.php`, `Shareholder.php`)
- Normalize raw BRS responses to standard DTOs (`SymbolQuote`, `NavData`, etc.)
- Save normalized records to local SQLite database with `synced=false` flag
- Run on a schedule (e.g., every 5 minutes during market hours)

**Key Characteristics:**
- Completely independent — no external server communication
- Operates even if External server is down
- Stores raw + normalized data locally for audit trail

**New Files:**
- `services/collector/collector_service.py` — Main collector logic
- `services/collector/config.py` — Collector-specific configuration
- `services/collector/__init__.py` — Package init

### 3.2 Sync Worker (Iran Server)

**Responsibilities:**
- Read unsynced records from local database
- Compress data using gzip
- Split into small chunks (configurable size, default ~50KB per chunk)
- Push each chunk to External server's Receiver API
- Handle retry with exponential backoff
- Track sync status per batch
- Handle acknowledgement from External server
- Mark records as synced only after successful acknowledgement

**Key Characteristics:**
- Push-based (no polling from External server)
- Chunked transfer (no single large request)
- Resumable (tracks which chunks were sent)
- Duplicate-protected (each chunk has unique ID + checksum)
- Fault-tolerant (retries on failure, resumes on interruption)

**New Files:**
- `services/sync_worker/sync_worker.py` — Main sync logic
- `services/sync_worker/chunker.py` — Chunking and compression logic
- `services/sync_worker/retry.py` — Retry logic with exponential backoff
- `services/sync_worker/__init__.py` — Package init

### 3.3 Receiver API (External Server)

**Responsibilities:**
- Receive compressed batches from Iran Sync Worker
- Decompress and validate (checksum verification)
- Deduplicate (ignore already-received chunks)
- Store data in External database
- Send acknowledgement back to Sync Worker
- Provide status endpoint for monitoring

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sync/batch` | Receive a compressed batch chunk |
| `GET` | `/sync/status` | Query sync progress and last received batch |
| `POST` | `/sync/ack` | Acknowledge successful receipt of a batch |
| `GET` | `/sync/health` | Health check endpoint |

**New Files:**
- `services/receiver/receiver_api.py` — FastAPI application
- `services/receiver/models.py` — Request/response models
- `services/receiver/__init__.py` — Package init

### 3.4 Ranking Service (External Server)

**Responsibilities:**
- Read market data from local External database only
- Run scoring and ranking pipelines
- Generate reports
- No dependency on Iran server or live BRS API

**Changes:**
- Update `DailyRankPipeline` to use local External DB instead of calling Iran gateway
- No changes to scoring/ranking logic itself

### 3.5 Telegram Service (External Server)

**Responsibilities:**
- Read data from local External database only
- Send reports and alerts
- No dependency on Iran server or live BRS API

**Changes:**
- No code changes needed — already reads from local database

---

## 4. Database Changes

### 4.1 Iran Server Database (Local SQLite)

**New tables:**

```sql
-- Track sync status for each data record
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,          -- e.g., 'symbols', 'nav_history'
    record_id TEXT NOT NULL,           -- Business key (e.g., symbol name)
    payload_json TEXT NOT NULL,        -- Normalized record data
    batch_id TEXT,                     -- ID of the batch this record belongs to
    synced INTEGER NOT NULL DEFAULT 0, -- 0 = pending, 1 = synced, 2 = failed
    sync_attempts INTEGER NOT NULL DEFAULT 0,
    last_sync_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_unsynced ON sync_queue(synced, table_name);
CREATE INDEX IF NOT EXISTS idx_sync_queue_batch ON sync_queue(batch_id);

-- Track sync batches
CREATE TABLE IF NOT EXISTS sync_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL UNIQUE,     -- UUID for this batch
    table_name TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    compressed_size INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, sending, sent, acked, failed
    checksum TEXT,                     -- SHA256 of full batch payload
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    synced_at TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_batches_status ON sync_batches(status);
```

### 4.2 External Server Database (Local SQLite)

**New tables:**

```sql
-- Track received batches for deduplication
CREATE TABLE IF NOT EXISTS received_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL UNIQUE,     -- Same batch_id as sent from Iran
    source_server TEXT NOT NULL,       -- 'iran-gateway'
    record_count INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_received_batches_batch ON received_batches(batch_id);

-- Track sync acknowledgements
CREATE TABLE IF NOT EXISTS sync_acknowledgements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    status TEXT NOT NULL,              -- 'received', 'processed', 'error'
    message TEXT,
    received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sync_ack_batch ON sync_acknowledgements(batch_id);
```

**Schema additions to existing tables:**
- No changes to existing tables — they are populated by the receiver from incoming batches

### 4.3 Database Migration Strategy

- New tables are created via `CREATE TABLE IF NOT EXISTS` (idempotent)
- Existing tables remain unchanged
- Migration is applied on application startup
- No data migration needed — new tables start empty

---

## 5. API Contracts

### 5.1 Batch Format (Push from Iran → External)

```json
{
  "id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-08-01T10:30:00Z",
  "sequence": 42,
  "table_name": "symbols",
  "records": [
    { "symbol": "عیار", "ins_code": "123456", "last_price": 12600, ... },
    { "symbol": "یاقوت", "ins_code": "123457", "last_price": 3450, ... }
  ],
  "record_count": 2,
  "checksum": "sha256:abc123...",
  "gzip_compressed": true,
  "original_size": 515878,
  "compressed_size": 125432
}
```

### 5.2 Receiver API — POST /sync/batch

**Request Headers:**
- `Content-Type: application/json`
- `X-Batch-ID: <batch_id>`
- `X-Sequence: <sequence_number>`
- `X-Checksum: <sha256_checksum>`
- `X-Gzip: true`
- `Authorization: Bearer <SYNC_TOKEN>` (optional, for authentication)

**Request Body:** Compressed batch JSON (gzip-compressed, base64-encoded or raw binary)

**Response (200 OK):**
```json
{
  "status": "accepted",
  "batch_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "received_records": 2,
  "duplicate": false,
  "processed_at": "2026-08-01T10:30:01Z"
}
```

**Response (200 OK, duplicate):**
```json
{
  "status": "duplicate",
  "batch_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "duplicate": true,
  "message": "Batch already received and processed"
}
```

**Response (400 Bad Request):**
```json
{
  "status": "error",
  "batch_id": null,
  "error": "Checksum mismatch",
  "detail": "Expected sha256:abc123, got sha256:def456"
}
```

### 5.3 Receiver API — GET /sync/status

**Response (200 OK):**
```json
{
  "status": "healthy",
  "last_batch_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "last_received_at": "2026-08-01T10:30:01Z",
  "total_batches_received": 156,
  "total_records_received": 4500,
  "pending_batches": 0,
  "duplicate_batches": 3,
  "error_batches": 0
}
```

### 5.4 Sync Worker — Retry/Resume Protocol

1. Sync Worker sends batch to `/sync/batch`
2. Waits for response (timeout: 30 seconds)
3. On success (200 OK): mark batch as `sent`, increment sequence
4. On timeout or 5xx: retry with exponential backoff (1s, 2s, 4s, 8s, 16s, max 60s)
5. On max retries exceeded: mark batch as `failed`, save error message
6. On next run: resume from first `failed` or `pending` batch
7. On duplicate detection (200 OK with `duplicate: true`): mark as `acked` and continue

---

## 6. Failure Scenarios

### 6.1 Iran Server Goes Down

- **Impact:** No new data is collected or synced
- **External server:** Continues to operate from last synced data in local database
- **Recovery:** When Iran server comes back, Sync Worker resumes from last unsynced batch
- **Ranking/Telegram:** Continue working from local External DB (may be stale)

### 6.2 External Server Goes Down

- **Impact:** Sync Worker cannot push batches
- **Iran server:** Continues collecting and storing data locally (unsynced)
- **Recovery:** When External server comes back, Sync Worker resumes pushing unsynced batches
- **Data loss risk:** None — data is persisted locally on Iran server

### 6.3 Network Interruption During Transfer

- **Impact:** Partial batch transfer
- **Sync Worker:** Retries with exponential backoff
- **Receiver API:** Idempotent — duplicate batches are detected and ignored
- **Recovery:** Sync Worker resumes from last unacknowledged batch

### 6.4 Batch Corruption (Checksum Mismatch)

- **Impact:** Receiver rejects the batch
- **Sync Worker:** Retries the batch (up to max retries)
- **If persistent:** Mark batch as `failed`, log error, alert operator
- **Recovery:** Sync Worker re-fetches data from local DB and re-sends

### 6.5 Duplicate Batch (Already Processed)

- **Impact:** None — Receiver detects duplicate and returns `duplicate: true`
- **Sync Worker:** Marks batch as `acked` and continues
- **No data duplication** in External database

### 6.6 Large Batch Timeout

- **Impact:** Single large batch fails to transfer
- **Mitigation:** Chunks are limited to ~50KB, so this should not occur
- **If it does:** Sync Worker retries; if persistent, batch is split into smaller chunks

---

## 7. Configuration

### Iran Server (Collector + Sync Worker)

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_TARGET_URL` | `http://82.115.8.100:8000` | External server Receiver API URL |
| `SYNC_TOKEN` | *(empty)* | Bearer token for Receiver API auth |
| `SYNC_CHUNK_SIZE` | `51200` | Max bytes per chunk (~50KB) |
| `SYNC_BATCH_SIZE` | `100` | Records per batch |
| `SYNC_RETRY_MAX` | `5` | Max retry attempts per batch |
| `SYNC_RETRY_BASE_DELAY` | `1` | Base delay in seconds for exponential backoff |
| `SYNC_RETRY_MAX_DELAY` | `60` | Max delay in seconds between retries |
| `SYNC_SCHEDULE_SECONDS` | `300` | How often to run sync (5 minutes) |
| `COLLECTOR_SCHEDULE_SECONDS` | `300` | How often to collect from BRS (5 minutes) |

### External Server (Receiver API)

| Variable | Default | Description |
|----------|---------|-------------|
| `RECEIVER_PORT` | `8001` | Port for Receiver API |
| `RECEIVER_TOKEN` | *(empty)* | Bearer token for auth (must match SYNC_TOKEN) |
| `RECEIVER_DB_PATH` | `data/receiver.db` | Path to receiver database |
| `RECEIVER_MAX_BATCH_SIZE` | `1048576` | Max batch size in bytes (1MB) |
| `RECEIVER_DUP_WINDOW_HOURS` | `24` | How long to keep received batch IDs for dedup |

---

## 8. Security Considerations

1. **Authentication:** Optional Bearer token for Receiver API (configurable, disabled by default for internal network)
2. **Checksum verification:** SHA256 checksum on every batch prevents silent corruption
3. **Idempotency:** Duplicate batches are detected and ignored — no data duplication
4. **No external exposure:** Receiver API binds to internal network only (not 0.0.0.0)
5. **Rate limiting:** Sync Worker respects configurable delay between batches
6. **No secrets in code:** All configuration via environment variables

---

## 9. Monitoring and Observability

### Iran Server Metrics
- Records collected per cycle
- Sync batches sent / failed / retried
- Sync latency (time from collection to acknowledgement)
- Batch sizes (original vs compressed)
- Error rate per batch

### External Server Metrics
- Batches received per cycle
- Duplicate detection rate
- Processing latency
- Database size growth
- API response times

### Logging
- All sync operations logged with batch IDs for traceability
- Error logs include full batch context for debugging
- Structured JSON logging for machine parsing
