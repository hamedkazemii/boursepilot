# BoursePilot V2 Migration — Implementation Plan

**Date:** 2026-08-01  
**Branch:** `feature/architecture-v2-sync`  
**Status:** Plan — Awaiting Approval  
**Estimated Duration:** 5 days

---

## Pre-Implementation Checklist

- [x] Phase 0: Full audit completed (`reports/MIGRATION_AUDIT.md`)
- [x] Phase 1: Migration branch created (`feature/architecture-v2-sync`)
- [x] Phase 2: Architecture design completed (`docs/ARCHITECTURE_V2.md`)
- [ ] Phase 3: Implementation plan approved
- [ ] Phase 4: Implementation (not started)

---

## Day 1: Infrastructure & Database Foundation

### Morning: Database Schema Migration

**Tasks:**
1. Add `sync_queue` table to Iran server database schema (`core/database/schema.py`)
2. Add `sync_batches` table to Iran server database schema
3. Add `received_batches` table to External server database schema
4. Add `sync_acknowledgements` table to External server database schema
5. Run schema migration on both servers
6. Verify new tables are created correctly

**Files to modify:**
- `core/database/schema.py` — Add new tables to `SCHEMA_SQL`
- `core/database/connection.py` — No changes needed (auto-migration on startup)

**Verification:**
- Run `python -c "from core.database import get_database; db = get_database(); print(db.fetchall('SELECT name FROM sqlite_master WHERE type=\"table\" AND name LIKE \"sync_%\"'))"`
- Confirm all 4 new tables exist

### Afternoon: Configuration & Environment

**Tasks:**
1. Add sync configuration variables to `.env` on both servers
2. Update `.env.example` with new sync variables
3. Update `config.py` to read new sync settings
4. Add `SYNC_TARGET_URL`, `SYNC_TOKEN`, `SYNC_CHUNK_SIZE`, etc. to `Settings` dataclass

**Files to modify:**
- `config.py` — Add sync configuration fields to `Settings`
- `.env.example` — Add new sync variables
- `.env` — Add actual values (Iran server: target URL; External server: receiver token)

**Verification:**
- Run `python -c "from config import settings; print(settings.SYNC_TARGET_URL)"`
- Confirm all new settings are accessible

---

## Day 2: Collector Service (Iran Server)

### Morning: Collector Service Implementation

**Tasks:**
1. Create `services/collector/__init__.py`
2. Create `services/collector/collector_service.py` with:
   - `CollectorService` class
   - `collect_all_symbols()` method — fetches from BRS, normalizes, saves to local DB
   - `collect_symbol(symbol)` method — fetches single symbol data
   - `collect_nav(symbol)` method — fetches NAV data
   - `collect_shareholders(symbol)` method — fetches shareholder data
   - `run_cycle()` method — runs full collection cycle
   - Records saved with `synced=0` flag in `sync_queue` table
3. Create `services/collector/config.py` — Collector-specific configuration
4. Write unit tests for CollectorService (mock BRS client, verify DB writes)

**Files to create:**
- `services/collector/__init__.py`
- `services/collector/collector_service.py`
- `services/collector/config.py`
- `tests/test_collector.py`

**Constraints:**
- Do NOT modify existing `BrsProvider`, `BrsClient`, or `brs_provider.py`
- Do NOT modify existing `MarketDataProvider` protocol
- Collector uses existing provider chain internally
- New code only — no changes to existing business logic

### Afternoon: Collector Integration

**Tasks:**
1. Integrate CollectorService with existing `DailyRankPipeline` (optional — collector runs independently)
2. Test collector runs without External server (offline mode)
3. Verify data is saved to local SQLite with `synced=0`
4. Test collection cycle produces correct `sync_queue` entries

**Verification:**
- Run collector in offline mode: `python -c "from services.collector.collector_service import CollectorService; c = CollectorService(); c.run_cycle()"`
- Verify `sync_queue` table has entries with `synced=0`
- Verify existing `DailyRankPipeline` still works unchanged

---

## Day 3: Sync Worker (Iran Server)

### Morning: Sync Worker Core

**Tasks:**
1. Create `services/sync_worker/__init__.py`
2. Create `services/sync_worker/chunker.py`:
   - `Chunker` class — splits records into configurable-size chunks
   - `compress_chunk(data)` — gzip compression
   - `decompress_chunk(data)` — decompression
   - `calculate_checksum(data)` — SHA256 checksum
3. Create `services/sync_worker/retry.py`:
   - `RetryPolicy` class — exponential backoff with configurable max retries
   - `should_retry(exception)` — decides if retry is appropriate
   - `next_delay(attempt)` — calculates exponential backoff delay
4. Create `services/sync_worker/sync_worker.py`:
   - `SyncWorker` class
   - `get_unsynced_batches()` — reads pending records from `sync_queue`
   - `build_batch(records)` — groups records into batch
   - `send_batch(batch)` — pushes batch to External Receiver API
   - `handle_response(response)` — processes acknowledgement
   - `mark_synced(batch_id)` — updates `sync_queue` and `sync_batches`
   - `run_cycle()` — full sync cycle
   - Resume logic — starts from first `failed` or `pending` batch

**Files to create:**
- `services/sync_worker/__init__.py`
- `services/sync_worker/chunker.py`
- `services/sync_worker/retry.py`
- `services/sync_worker/sync_worker.py`
- `tests/test_sync_worker.py`

**Constraints:**
- Do NOT modify existing provider code
- Do NOT modify existing API endpoints
- Sync Worker is a new standalone service

### Afternoon: Sync Worker Integration & Testing

**Tasks:**
1. Test sync worker with mock receiver (no External server needed)
2. Test chunking — verify records are split into ~50KB chunks
3. Test compression — verify gzip round-trip works
4. Test checksum — verify SHA256 verification
5. Test retry logic — simulate failures and verify exponential backoff
6. Test resume — simulate interrupted transfer and verify resume from last batch
7. Test duplicate protection — send same batch twice, verify second is ignored

**Verification:**
- Run sync worker in dry-run mode: `python -c "from services.sync_worker.sync_worker import SyncWorker; w = SyncWorker(dry_run=True); w.run_cycle()"`
- Verify batches are created in `sync_batches` table
- Verify chunks are compressed and checksums are correct

---

## Day 4: Receiver API (External Server)

### Morning: Receiver API Implementation

**Tasks:**
1. Create `services/receiver/__init__.py`
2. Create `services/receiver/models.py`:
   - `BatchRequest` model — request body validation
   - `BatchResponse` model — response body
   - `SyncStatus` model — status endpoint response
3. Create `services/receiver/receiver_api.py`:
   - FastAPI application with endpoints:
     - `POST /sync/batch` — receive compressed batch
     - `GET /sync/status` — query sync progress
     - `POST /sync/ack` — acknowledge batch
     - `GET /sync/health` — health check
   - Decompression logic (gzip)
   - Checksum verification
   - Duplicate detection (check `received_batches` table)
   - Store records in External database
   - Send acknowledgement response
4. Create `services/receiver/config.py` — Receiver-specific configuration
5. Write unit tests for Receiver API

**Files to create:**
- `services/receiver/__init__.py`
- `services/receiver/models.py`
- `services/receiver/receiver_api.py`
- `services/receiver/config.py`
- `tests/test_receiver.py`

**Constraints:**
- Do NOT modify existing External server business logic
- Do NOT change existing API endpoints on External server
- Receiver API is a new standalone FastAPI app on port 8001

### Afternoon: Receiver API Integration

**Tasks:**
1. Test Receiver API endpoints with curl/httpx
2. Test batch decompression and validation
3. Test duplicate detection — send same batch twice, verify second is rejected
4. Test checksum mismatch — send corrupted batch, verify rejection
5. Test status endpoint — verify it reports correct counts
6. Test health endpoint
7. Verify External server ranking engine still works from local DB

**Verification:**
- Start Receiver API: `uvicorn services.receiver.receiver_api:app --host 0.0.0.0 --port 8001`
- Send test batch: `curl -X POST http://localhost:8001/sync/batch -H "Content-Type: application/json" -d @test_batch.json`
- Verify response is 200 OK with `status: "accepted"`
- Verify records are in External database

---

## Day 5: End-to-End Testing & Verification

### Morning: Integration Testing

**Tasks:**
1. **Test 1: Iran collector works without External server**
   - Disable network access to External server
   - Run collector cycle — verify data is collected and saved locally
   - Verify `sync_queue` has entries with `synced=0`
   - Restore network — verify sync worker can push later

2. **Test 2: External server works without Iran live requests**
   - Disable Iran server network access
   - Run ranking pipeline on External server — verify it works from local DB
   - Run Telegram bot on External server — verify it works from local DB
   - Restore Iran network — verify sync resumes

3. **Test 3: Interrupted transfer resumes**
   - Start sync worker
   - Kill sync worker mid-transfer (simulate network interruption)
   - Restart sync worker
   - Verify it resumes from last unacknowledged batch
   - Verify no duplicate records in External DB

4. **Test 4: Duplicate packets ignored**
   - Send same batch twice
   - Verify second send returns `duplicate: true`
   - Verify no duplicate records in External DB

5. **Test 5: 1000+ records sync successfully**
   - Generate 1000+ test records in `sync_queue`
   - Run sync worker
   - Verify all records are transferred to External DB
   - Verify checksums match
   - Verify `synced=1` for all records

### Afternoon: Full System Test

**Tasks:**
1. Run full pipeline: Collector → Sync Worker → Receiver → Ranking → Telegram
2. Verify end-to-end data flow works
3. Verify all failure scenarios are handled gracefully
4. Run existing test suite — verify no regressions
5. Performance test — measure sync latency for 1000 records
6. Document any issues found

### Rollback Strategy

If any phase fails or causes issues:

1. **Database rollback:** New tables are `IF NOT EXISTS` — no rollback needed, just drop them if needed
2. **Code rollback:** All new code is on `feature/architecture-v2-sync` branch — merge to `develop` only after full validation
3. **Service rollback:** New services (collector, sync_worker, receiver) are independent — can be disabled without affecting existing services
4. **Config rollback:** `.env` changes are additive — remove new variables to disable V2 features
5. **Full rollback:** Delete `feature/architecture-v2-sync` branch, stay on `agent/v1.5-development`

**Rollback commands:**
```bash
# On Iran server
cd /home/bourse/projects/boursepilot
git checkout develop
git branch -D feature/architecture-v2-sync
systemctl restart bourse-market-gateway

# On External server
cd /root/projects/boursepilot
git checkout agent/v1.5-development
git branch -D feature/architecture-v2-sync
systemctl restart boursepilot
```

---

## Implementation Constraints (Reiterated)

### DO NOT:
- ❌ Rewrite existing business logic
- ❌ Remove current API endpoints
- ❌ Delete old provider code (archive only, after migration is validated)
- ❌ Change production services blindly
- ❌ Kill services without approval
- ❌ Modify existing `BrsProvider`, `BrsClient`, `MarketGatewayProvider`, `MarketGatewayClient`
- ❌ Modify existing `DailyRankPipeline` scoring/ranking logic
- ❌ Modify existing Telegram bot logic

### DO:
- ✅ Create new services in new directories
- ✅ Add new database tables (idempotent)
- ✅ Add new configuration variables
- ✅ Write tests for all new code
- ✅ Keep old code working until V2 is fully validated
- ✅ Archive legacy code only after migration is proven stable

---

## Success Criteria

| # | Criterion | Verification Method |
|---|-----------|-------------------|
| 1 | Iran collector works without External server | Run collector offline, verify DB entries |
| 2 | External server works without Iran live requests | Run ranking/Telegram offline, verify results |
| 3 | Interrupted transfer resumes | Kill sync mid-transfer, restart, verify resume |
| 4 | Duplicate packets ignored | Send same batch twice, verify no duplicates |
| 5 | 1000+ records sync successfully | Generate 1000 records, sync, verify all received |
| 6 | No regressions in existing functionality | Run full test suite, verify all pass |
| 7 | Sync latency < 5 seconds for 1000 records | Measure end-to-end sync time |
| 8 | Compression reduces payload by >50% | Compare original vs compressed size |

---

## Post-Implementation: Cleanup (Future)

Once V2 is stable and validated:
1. Archive legacy TSETMC files (`services/tsetmc_client.py`, etc.)
2. Archive `services/providers/tsetmc_provider.py`
3. Remove `.env.example` conflicting defaults
4. Update `MARKET_GATEWAY_URL` on Iran server (remove self-reference)
5. Update `BRS_API_KEY` in `.env` (if BRS key is renewed)
6. Document V1 → V2 migration in `CHANGELOG.md`
