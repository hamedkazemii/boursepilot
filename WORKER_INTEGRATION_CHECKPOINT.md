# Worker Integration Checkpoint

## Date: 2026-08-02 15:25 UTC
## Branch: feature/architecture-v2-sync
## Version: 0.7.0

## Overview

This checkpoint documents the integration points between various worker components in BoursePilot, focusing on how they relate to the Sync V1 implementation. It covers the receiver service (Iran gateway), sync collector/exporter/chunker, and the core data pipelines.

## Worker Components Summary

### 1. Iran Gateway Receiver (`services/receiver/`)
- **Purpose**: Receives sync chunks from Iran gateway and reassembles them
- **Key Files**:
  - `api.py`: FastAPI endpoints for receiving manifests and chunks
  - `models.py`: Data models (ReceivedBatch, ReceivedChunk, SyncAck)
  - `storage.py`: File-based storage for batches and chunks
  - `validator.py`: Manifest and chunk validation

### 2. Sync V1 Pipeline (`services/sync/`)
- **Collector** (`collector.py`): 
  - Collects fund snapshots from providers (BRS, TSETMC, etc.)
  - Stores them as local JSON files in SNAPSHOT_DIR
  - Uses existing provider interfaces without modification
  
- **Exporter** (`exporter.py`):
  - Converts FundSnapshot lists to compressed, checksummed batches
  - Pipeline: FundSnapshots → JSON → gzip → checksum → chunks
  
- **Chunker** (`chunker.py`):
  - Splits compressed payloads into configurable chunks (default 5KB)
  - Provides retry/resume metadata for interrupted transfers
  
- **Sender** (`sender/engine.py`):
  - Legacy sender implementation (appears to be simplified/custom)
  - Chunks files and sends them with manifest to receiver URL

### 3. Core Data Pipelines (`core/pipeline/`)
- **Daily Rank Pipeline** (`daily_rank.py`):
  - Discovers funds → (optional NAV) → Scores → Ranks → Persists/Reports
  - Uses HistoryEngine for incremental storage
  - Generates JSON ranking files and text reports
  
- **Daily Analysis Pipeline** (`daily_analysis.py`):
  - Full pipeline: live/snapshot → history → indicators → smart rank → persist
  - More comprehensive than daily_rank, includes technical indicators
  - Uses IndicatorEngine and SmartRanker for enhanced analysis

### 4. Collection Layer (`services/collectors/`)
- **Fund Collector** (`fund_collector.py`):
  - Appears to be the main collection interface used by pipelines
  - Wraps provider calls and stores results

## Integration Flow Analysis

### Normal Data Flow (Without Sync V1)
```
Market Data Provider (BRS/TSETMC)
        ↓
services/collectors/fund_collector.py
        ↓
core/pipeline/daily_analysis.py or daily_rank.py
        ↓
services/snapshot/store.py (JSON files)
        ↓
core/history/engine.py (SQLite)
        ↓
Telegram bot / reports / API
```

### Sync V1 Enhanced Data Flow
```
Market Data Provider (BRS/TSETMC)
        ↓
services/collectors/fund_collector.py
        ↓
services/sync/collector.py (FundCollector)  ← NEW: Local JSON snapshots
        ↓
services/sync/exporter.py (SyncExporter)   ← NEW: Batching, compression, checksum
        ↓
services/sync/chunker.py (SyncChunker)     ← NEW: Chunking for transfer
        ↓
[NETWORK TRANSFER: Iran Gateway → External Server]
        ↓
services/receiver/api.py (ReceiverAPI)     ← NEW: Chunk reception
        ↓
services/receiver/storage.py (ReceiverStorage) ← NEW: File storage
        ↓
services/receiver/validator.py (ChunkValidator) ← NEW: Validation
        ↓
services/sync/chunker.py (SyncChunker)     ← NEW: Reassembly
        ↓
services/sync/exporter.py (SyncExporter)   ← NEW: Decompression, validation
        ↓
core/pipeline/daily_analysis.py or daily_rank.py
        ↓
services/snapshot/store.py (JSON files)
        ↓
core/history/engine.py (SQLite)
        ↓
Telegram bot / reports / API
```

### Alternative Flow (Direct Provider to Pipeline)
```
Market Data Provider (BRS/TSETMC)
        ↓
services/collectors/fund_collector.py
        ↓
core/pipeline/daily_analysis.py or daily_rank.py
        ↓
[IF ENABLED: services/sync/collector.py → exporter → chunker → network → receiver → ...]
        ↓
services/snapshot/store.py (JSON files)
        ↓
core/history/engine.py (SQLite)
        ↓
Telegram bot / reports / API
```

## Key Integration Points for Sync V1

### 1. Collector Integration
- **Location**: `services/sync/collector.py`
- **Integration Point**: Sits between provider and storage layer
- **Function**: 
  - Collects snapshots from providers (same as existing fund_collector)
  - Stores them as local JSON files in SNAPSHOT_DIR
  - This is the NEW storage layer that Sync V1 adds before transmission
- **Interface**: 
  - Accepts MarketSnapshotProvider (same interface as existing collectors)
  - Returns FundSnapshot objects (same as existing)
  - Backward compatible with existing code

### 2. Exporter/Chunker Integration
- **Location**: `services/sync/exporter.py` and `chunker.py`
- **Integration Point**: After local storage, before network transmission
- **Function**:
  - Takes list of FundSnapshot objects
  - Serializes to JSON, compresses with gzip, generates SHA-256 checksum
  - Splits into chunks for reliable transfer
  - Generates manifest for validation
- **Interface**:
  - Input: List[FundSnapshot], batch_id, chunk_size
  - Output: SyncBatch object with chunks and manifest
  - Designed to be called periodically or on demand

### 3. Receiver Integration
- **Location**: `services/receiver/`
- **Integration Point**: Network endpoint receiving chunks from external server
- **Function**:
  - Receives manifest (batch metadata) first
  - Receives chunks individually with validation
  - Reassembles chunks when all received
  - Validates final checksum against manifest
  - Stores completed batch for retrieval
- **Interface**:
  - HTTP endpoints: POST /sync/manifest, POST /sync/chunk, GET /sync/status/{batch_id}
  - Requires X-Sync-Key authentication
  - Returns JSON responses with status information

### 4. Pipeline Integration Points
- **History Engine** (`core/history/engine.py`):
  - Already used by pipelines for incremental storage
  - Sync V1 doesn't change this directly, but provides additional data source
  
- **Snapshot Store** (`services/snapshot/store.py`):
  - Used by pipelines for caching JSON data
  - Sync V1's collector writes to SNAPSHOT_DIR which may be the same or different from snapshot store's directory
  - Need to verify if these are separate or overlapping storage locations

### 5. Provider Reliability Integration
- **Location**: `services/providers/reliability.py` and related files
- **Integration Point**: Wraps provider calls to add retry, circuit breaker, etc.
- **Function**:
  - All collector and pipeline code uses `get_market_data_provider()` factory
  - This factory should return reliability-wrapped providers when configured
  - Transparent to calling code (collector, pipelines, telegram bot)

## Data Flow Verification Points

### For Sync V1 Implementation Verification:
1. **Collector to Storage**:
   - Verify that `services/sync/collector.py` correctly stores JSON snapshots
   - Check that files are written to `settings.SNAPSHOT_DIR`
   - Ensure filename format: `{safe_symbol}_{timestamp}.json`

2. **Exporter Operation**:
   - Verify that `SyncExporter.export_batch()` correctly:
     - Serializes FundSnapshot list to JSON
     - Compresses with gzip
     - Generates SHA-256 checksum of compressed data
     - Creates chunks of appropriate size
     - Generates manifest with correct metadata

3. **Receiver Operation**:
   - Verify that `ReceiverAPI` correctly:
     - Validates X-Sync-Key header
     - Accepts manifest and creates pending batch
     - Accepts chunks, validates checksums, stores them
     - Tracks received chunks per batch
     - (Currently skips automatic validation/reassembly on chunk receipt - intentional for performance)

4. **Reassembly and Validation**:
   - Verify that when all chunks are received:
     - Chunks can be reassembled in correct order
     - Reassembled data decompresses correctly
     - Decompressed JSON matches original snapshot count
     - Final checksum matches manifest

### Integration with Existing Pipelines:
1. **Backward Compatibility**:
   - Existing code using `services/collectors/fund_collector.py` should continue to work
   - Existing code using providers directly should continue to work
   - Sync V1 components are additive, not replacement

2. **Optional Usage**:
   - Sync V1 components can be used independently:
     - Run collector to populate SNAPSHOT_DIR
     - Run exporter/chunker to create transfer batches
     - Send batches via network
     - Run receiver to collect batches
     - Use reassembled data in pipelines

3. **Potential Enhancement Points**:
   - Pipelines could be modified to use Sync V1's storage as primary source
   - Could add a mode where pipelines first check for recently synced data before fetching live
   - Could implement fallback logic: if provider fails, use most recent synced batch

## Risk Assessment

### High Risk Areas:
1. **Storage Directory Conflicts**:
   - Need to verify if `SNAPSHOT_DIR` (used by sync collector) and `SnapshotStore.base_dir` are intended to be separate
   - If they overlap, need to ensure no file naming conflicts or deletion issues

2. **Receiver Validation Logic**:
   - Current receiver code skips automatic validation/reassembly on chunk receipt (line with `if False and updated_batch.is_complete:`)
   - This means batches are not automatically validated when completed via chunk reception
   - Need to verify if this is intentional (for performance) and if there's a separate validation process

3. **Checksum Propagation**:
   - Need to verify that checksums are correctly generated, transmitted, and validated at each stage
   - Any mismatch should be detected and handled appropriately

### Medium Risk Areas:
1. **Chunk Size Configuration**:
   - Default chunk size is 5KB in SynChunker but 1024 bytes in SyncSender (legacy)
   - Need to ensure consistency if both are used in same deployment

2. **Retry Logic Alignment**:
   - Sync Chunker has retry/resume metadata
   - Telegram bot already has rate limiting
   - Provider reliability layer has retry/circuit breaker
   - Need to ensure these complement rather than conflict

3. **Timestamp Handling**:
   - Multiple components generate timestamps (captured_at, created_at, etc.)
   - Need to ensure consistency in timezone handling (all appear to use UTC)

### Low Risk Areas:
1. **Data Model Compatibility**:
   - All components use FundSnapshot or compatible DTOs
   - No changes to core data structures indicated

2. **Interface Stability**:
   - Sync V1 components use existing provider interfaces (MarketSnapshotProvider)
   - No changes required to provider implementations

## Recommendations for Sync V1 Worker Integration

1. **Clarify Storage Architecture**:
   - Document whether SNAPSHOT_DIR and SnapshotStore.base_dir should be separate or unified
   - If separate, consider naming convention to avoid confusion (e.g., sync_snapshots vs cache_snapshots)

2. **Implement Receiver Validation Strategy**:
   - Decide whether to:
     - Enable automatic validation on chunk receipt (may impact performance)
     - Implement a separate validation worker/process
     - Rely on consumer-triggered validation (when pipelines request data)
   - Document the chosen approach and ensure it meets reliability requirements

3. **Add Observability**:
   - Consider adding metrics/prometheus endpoints to track:
     - Chunk reception rates
     - Reassembly success/failure rates
     - Checksum validation results
     - Batch processing latency
   - This would help monitor Sync V1 health in production

4. **Test Failure Scenarios**:
   - Test network interruptions during chunk transfer
   - Test chunk corruption detection
   - Test receiver restart recovery
   - Test validation failure handling

5. **Document Operational Procedures**:
   - How to monitor Sync V1 health
   - How to troubleshoot common issues
   - Backup and recovery procedures for sync data
   - Scaling considerations (multiple receivers, load balancing)

## Conclusion

The worker components in BoursePilot show good separation of concerns, with Sync V1 components designed to be layered on top of existing functionality rather than replacing it. 

**Integration Readiness: YELLOW** (Ready with caveats)

The Sync V1 worker components are well-designed and follow the existing architectural patterns. The primary risks are around storage directory clarity and receiver validation strategy, which should be clarified before full deployment. The components are designed to be opt-in/additive, allowing for gradual rollout and testing.

Key integration points are clearly defined:
- Collector ↔ Provider (unchanged interface)
- Collector ↔ Storage (new local JSON storage)
- Exchanger/Chunker ↔ Collector (FundSnapshot list in/out)
- Receiver ↔ Chunker/Exporter (chunk reassembly and validation)
- Pipelines ↔ Storage/History (existing interfaces unchanged)

With proper clarification of the storage architecture and validation approach, the Sync V1 workers should integrate smoothly with the existing BoursePilot workforce.