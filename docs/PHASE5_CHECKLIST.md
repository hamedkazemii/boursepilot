# Phase 5 Implementation Checklist — sync_worker (Updated)

**Date:** 2026-08-01
**Branch:** `feature/architecture-v2-sync`
**Status:** Approved with modifications — Phase 5A in progress

---

## Modifications from Original Plan

| # | Original | Modified | Reason |
|---|---|---|---|
| 1 | `services/sync_worker/` | `services/sync/worker/` | Namespace alignment with existing sync module |
| 2 | New `chunker.py` | Reuse `services/sync/chunker.py` | Avoid duplication; existing chunker is production-ready |
| 3 | Database tables + sync_queue | File-based local state only | Simpler; no DB migration needed for V1 worker |
| 4 | Config in `config.py` | Config in `services/sync/worker/config.py` | No production config changes |
| 5 | Modify existing files | Only add new worker files | Zero production code changes |
| 6 | Full implementation (Days 1-5) | Phase 5A only this turn | Incremental delivery |

---

## Phase 5A: sync_worker Core

| # | Task | File | Status |
|---|---|---|---|
| 1 | Create `services/sync/worker/__init__.py` | New | 🔲 |
| 2 | Create `services/sync/worker/config.py` — worker config (chunk size, retry max, batch size, schedule interval, state dir, target URL, API key) | New | 🔲 |
| 3 | Create `services/sync/worker/state.py` — file-based local state manager (pending batches, sent batches, failed batches, resume support) | New | 🔲 |
| 4 | Create `services/sync/worker/retry.py` — `RetryPolicy` class with exponential backoff (1s, 2s, 4s, 8s, 16s, max 60s), `should_retry()`, `next_delay()` | New | 🔲 |
| 5 | Create `services/sync/worker/sender.py` — `SyncSender` class using existing `SyncTransport` + retry state, manifest/chunk upload, resume from last unacked chunk | New | 🔲 |
| 6 | Create `services/sync/worker/worker.py` — `SyncWorker` class with `run_cycle()`, `get_pending_batches()`, `build_batch()`, `send_batch()`, `handle_response()`, `mark_synced()`, resume logic | New | 🔲 |
| 7 | Create `tests/test_sync_worker.py` — mock receiver, test chunking (reuse existing chunker), compression, checksum, retry, resume, duplicate detection | New | 🔲 |

---

## Phase 5B (Future)

| # | Task | File | Status |
|---|---|---|---|
| 8 | Integrate with collector output | New | 🔲 |
| 9 | Add logging and alerting | New | 🔲 |
| 10 | Performance test with 1000+ records | New | 🔲 |

---

## Phase 5C (Future — After Phase 5A Passes)

| # | Task | File | Status |
|---|---|---|---|
| 11 | Create `deploy/systemd/boursepilot-sync.service` | New | 🔲 |
| 12 | Create `deploy/systemd/boursepilot-sync.timer` | New | 🔲 |
| 13 | Create `deploy/systemd/install.sh` | New | 🔲 |

---

## Constraints

- ❌ Do NOT modify existing provider code
- ❌ Do NOT modify existing `DailyRankPipeline` scoring/ranking logic
- ❌ Do NOT modify existing Telegram bot logic
- ❌ Do NOT modify existing API endpoints
- ❌ Do NOT delete old provider code
- ❌ Do NOT modify `config.py`
- ❌ Do NOT create database tables
- ❌ Do NOT create a new chunker
- ✅ All new code in `services/sync/worker/` only
- ✅ Worker config lives in `services/sync/worker/config.py`
- ✅ File-based state only (no DB)
- ✅ Reuse existing `services/sync/chunker.py`
- ✅ Reuse existing `services/sync/transport.py`

---

## Deliverables Summary

```
New files: 7
Modified files: 0
No production code changes
```

---

**Phase 5A approved. Proceeding with implementation.**
