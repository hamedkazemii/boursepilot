# Sync V1 — Receiver API Design Document
## External Server Component

**Date:** 2026-08-01  
**Status:** Draft  
**Scope:** Standalone receiver for sync chunks from Iran gateway

---

## 1. Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Iran Gateway   │────▶│  External       │────▶│  Local File     │
│  (Sender)       │     │  Receiver API   │     │  Storage        │
│                 │     │  (POST /sync/)  │     │  (data/receiver/)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
        1. POST manifest          2. Validate manifest
        3. Create pending batch    4. Create pending batch
        5. POST chunks            6. Validate each chunk
        7. Validate each chunk    8. Store chunk file
        9. Checksum per chunk     10. Detect duplicates
       11. Reassemble when        12. Verify final checksum
           complete                 
       13. Mark batch complete    14. Update batch status
```

### Step-by-Step

1. **Sender** POSTs manifest to `/sync/manifest` with batch metadata.
2. **Receiver** validates manifest fields and creates a pending batch.
3. **Sender** POSTs individual chunks to `/sync/chunk` with base64 payload.
4. **Receiver** validates each chunk's checksum (SHA-256 of payload).
5. **Receiver** detects duplicate chunks (same batch_id + chunk_number).
6. **Receiver** stores each chunk as a binary file in `data/receiver/chunks/`.
7. **Receiver** updates batch metadata after each chunk.
8. When all chunks are received, **Receiver** reassembles the batch.
9. **Receiver** validates the final checksum against the manifest.
10. **Receiver** marks batch as complete or failed.

---

## 2. API Endpoints

### POST /sync/manifest

Receive batch manifest metadata before chunks arrive.

**Request Body:**
```json
{
    "batch_id": "abc123",
    "total_chunks": 5,
    "chunk_size": 5120,
    "checksum": "sha256-hex-of-full-payload",
    "snapshot_count": 10,
    "created_at": "2026-08-01T10:00:00+00:00"
}
```

**Response (201):**
```json
{
    "status": "accepted",
    "batch_id": "abc123",
    "total_chunks": 5,
    "message": "Manifest accepted. Ready to receive chunks."
}
```

**Errors:**
- 400: Invalid manifest data
- 401: Invalid or missing X-Sync-Key header

### POST /sync/chunk

Receive a single sync chunk.

**Request Body:**
```json
{
    "batch_id": "abc123",
    "chunk_number": 0,
    "payload": "base64-encoded-bytes",
    "checksum": "sha256-hex-of-raw-payload"
}
```

**Response (201):**
```json
{
    "status": "accepted",
    "batch_id": "abc123",
    "chunk_number": 0,
    "message": "Chunk 0 accepted for batch abc123",
    "checksum_valid": true
}
```

**Response (200) for duplicate:**
```json
{
    "status": "duplicate",
    "batch_id": "abc123",
    "chunk_number": 0,
    "message": "Chunk 0 already received for batch abc123",
    "checksum_valid": false
}
```

**Response (400) for checksum mismatch:**
```json
{
    "status": "rejected",
    "batch_id": "abc123",
    "chunk_number": 0,
    "message": "Checksum mismatch for chunk 0",
    "checksum_valid": false
}
```

**Errors:**
- 400: Missing fields or invalid base64
- 401: Invalid or missing X-Sync-Key header

### GET /sync/status/{batch_id}

Check the status of a sync batch.

**Response (200):**
```json
{
    "batch_id": "abc123",
    "status": "complete",
    "total_chunks": 5,
    "received_chunks": 5,
    "missing_chunks": [],
    "is_complete": true,
    "completed_at": "2026-08-01T10:05:00+00:00",
    "error_message": null
}
```

**Errors:**
- 404: Batch not found
- 401: Invalid or missing X-Sync-Key header

### GET /health

Health check endpoint — no authentication required.

**Response (200):**
```json
{
    "status": "healthy",
    "service": "sync-receiver",
    "batch_count": 3,
    "storage_dir": "data/receiver/"
}
```

---

## 3. Security

### X-Sync-Key Header

All sync endpoints (`/sync/manifest`, `/sync/chunk`, `/sync/status/{batch_id}`) require the `X-Sync-Key` header.

**Validation:**
- Header value is compared against `SYNC_API_KEY` from environment
- If `SYNC_API_KEY` is not set, receiver is effectively disabled
- Default: `SYNC_RECEIVER_ENABLED=false`

**Example:**
```
X-Sync-Key: your-secret-api-key-here
```

### API Key Rotation

- `SYNC_API_KEY_VERSION` tracks the current key version
- Future versions can support multiple keys for rotation
- V1 uses a single static key

### No External Exposure

- V1 receiver is a standalone FastAPI app
- No authentication bypass
- No default API key
- All endpoints require valid X-Sync-Key header

---

## 4. Storage

### File-Based Storage (No Database)

```
data/receiver/
├── batches/
│   ├── abc123.json
│   ├── def456.json
│   └── ghi789.json
└── chunks/
    ├── abc123/
    │   ├── 0.bin
    │   ├── 1.bin
    │   ├── 2.bin
    │   ├── 3.bin
    └── def456/
        ├── 0.bin
        ├── 1.bin
        └── 2.bin
```

### Batch Metadata JSON

```json
{
    "batch_id": "abc123",
    "total_chunks": 5,
    "chunk_size": 5120,
    "expected_checksum": "sha256-hex",
    "snapshot_count": 10,
    "source": "iran-gateway",
    "target": "external-server",
    "created_at": "2026-08-01T10:00:00+00:00",
    "chunk_count": 3,
    "status": "pending",
    "completed_at": null,
    "error_message": null
}
```

### Chunk Files

- Binary files (`.bin`) containing the raw compressed payload
- Named by chunk number: `0.bin`, `1.bin`, etc.
- Stored in `data/receiver/chunks/{batch_id}/`

### Cleanup

- Old batches are automatically cleaned up after `SYNC_SNAPSHOT_TTL_HOURS` (default 24h)
- Cleanup removes both metadata JSON and chunk binary files
- No data loss risk — only temporary sync data is stored

---

## 5. Failure Handling

### Failure Scenarios

| Scenario | Detection | Response |
|----------|-----------|----------|
| Missing X-Sync-Key header | Header validation | 401 Unauthorized |
| Invalid API key | Key comparison | 401 Unauthorized |
| Invalid manifest data | Field validation | 400 Bad Request |
| Missing manifest fields | Required field check | 400 Bad Request |
| Invalid base64 payload | Decoding error | 400 Bad Request |
| Checksum mismatch | SHA-256 comparison | 400 Bad Request (rejected) |
| Duplicate chunk | Storage check | 200 OK (duplicate status) |
| Missing chunks on reassembly | Chunk count check | Batch stays incomplete |
| Final checksum mismatch | Manifest comparison | Batch marked as failed |
| Batch not found | Registry + storage lookup | 404 Not Found |

### Retry Strategy

1. **Sender retries failed chunks:** If a chunk POST fails (network error), sender retries the same chunk.
2. **Receiver detects duplicates:** Duplicate chunks return 200 OK with `status: "duplicate"`.
3. **Sender continues with remaining chunks:** Missing chunks are retried until all are received.
4. **Batch timeout:** If a batch is incomplete after a timeout, it stays in `pending` status.
5. **Cleanup:** Old pending batches are cleaned up automatically.

### Idempotency

- Chunk POSTs are idempotent — sending the same chunk twice is safe
- Receiver detects duplicates and returns `status: "duplicate"` without reprocessing
- No duplicate data is stored

---

## 6. Configuration

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_RECEIVER_ENABLED` | `false` | Enable/disable the receiver API |
| `SYNC_API_KEY` | `""` | API key for X-Sync-Key header validation |
| `SYNC_API_KEY_VERSION` | `1` | API key version for future rotation |

### Config.py Additions

```python
# --- Sync V1 Receiver (external server) ---
SYNC_RECEIVER_ENABLED: bool = _env("SYNC_RECEIVER_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SYNC_API_KEY: *** = _env("SYNC_API_KEY", "")
SYNC_API_KEY_VERSION: int = _env_int("SYNC_API_KEY_VERSION", 1)
```

---

## 7. Rollback Plan

### V1 Receiver Rollback (Trivial)

Since V1 adds only new files and modifies only `config.py` and `.env.example`:

```bash
# Delete the receiver module
rm -rf services/receiver/

# Revert config.py changes
git checkout config.py

# Revert .env.example changes
git checkout .env.example

# No database changes to revert
# No services to restart
# No data to clean up (receiver data is temporary)
```

### Rollback Verification

After rollback, confirm:
1. `git status` shows clean working tree on original branch
2. `python -c "from services.receiver import ReceiverAPI"` raises `ModuleNotFoundError`
3. Existing sync sender still works independently
4. No receiver data remains in `data/receiver/`

---

## 8. Testing Strategy

### Unit Tests (services/receiver/)

| Test | Purpose |
|------|---------|
| `test_models.py` | Verify dataclass creation, JSON serialization |
| `test_storage.py` | Verify file-based storage, cleanup |
| `test_validator.py` | Verify checksum validation, manifest validation, reassembly |
| `test_api.py` | Verify endpoint behavior, auth, error handling |

### Integration Tests (test_receiver_v1.py)

| Test | Purpose |
|------|---------|
| Receive single chunk | Verify chunk acceptance and storage |
| Receive duplicate chunk | Verify duplicate detection and rejection |
| Detect missing chunk | Verify missing chunk detection |
| Reassemble batch | Verify complete batch reassembly |
| Invalid checksum rejection | Verify checksum validation rejects bad data |
| Invalid API key rejection | Verify X-Sync-Key validation |
| Complete batch reassembly | End-to-end manifest → chunks → reassembly → verification |
| Full Iran→Receiver simulation | Simulate complete sync flow from Iran gateway |

---

## 9. Monitoring and Observability (Future)

V1 does not include monitoring. V2 should add:
- Chunk receive latency metrics
- Batch completion rate
- Duplicate chunk rate
- Checksum failure rate
- Storage usage tracking

---

*Design version: 1.0*  
*Status: Draft — pending implementation review*
