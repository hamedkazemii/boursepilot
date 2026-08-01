"""
Sync V1 — ReceiverAPI

FastAPI-based receiver for sync chunks from the Iran gateway.

Endpoints:
    POST /sync/manifest  — Receive batch manifest metadata
    POST /sync/chunk     — Receive a single chunk
    GET  /sync/status/{batch_id} — Check batch status
    GET  /health         — Health check

Security:
    All sync endpoints require X-Sync-Key header validation.
    API key is read from SYNC_API_KEY environment variable.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from services.receiver.models import ReceivedBatch, ReceivedChunk, SyncAck
from services.receiver.storage import ReceiverStorage
from services.receiver.validator import ChunkValidator
from services.sync.models import SyncManifest

logger = logging.getLogger(__name__)

app = FastAPI(title="Sync V1 Receiver", version="1.0")


def _get_api_key() -> str:
    """Read the API key from environment via config."""
    from config import settings

    return settings.SYNC_API_KEY


def _validate_api_key(x_sync_key: Optional[str] = None) -> bool:
    """Validate the X-Sync-Key header against the configured API key."""
    api_key = _get_api_key()
    if not api_key:
        # No API key configured — receiver is effectively disabled
        return False
    if not x_sync_key:
        return False
    return x_sync_key == api_key


def _require_auth(x_sync_key: Optional[str] = None) -> None:
    """Raise HTTPException if API key is invalid."""
    if not _validate_api_key(x_sync_key):
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid or missing X-Sync-Key header"},
        )


# ---------------------------------------------------------------------------
# In-memory batch registry (complements file-based storage)
# ---------------------------------------------------------------------------

# Maps batch_id -> ReceivedBatch
_batch_registry: dict[str, ReceivedBatch] = {}

# Maps batch_id -> SyncManifest
_manifest_registry: dict[str, SyncManifest] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/sync/manifest")
async def receive_manifest(
    request: Request,
    x_sync_key: Optional[str] = Header(None, alias="X-Sync-Key"),
):
    """
    Receive batch manifest metadata before chunks arrive.

    Creates a pending batch record that chunks will be associated with.

    Required JSON body:
        {
            "batch_id": str,
            "total_chunks": int,
            "chunk_size": int,
            "checksum": str,
            "snapshot_count": int,
            "created_at": str (optional)
        }
    """
    _require_auth(x_sync_key)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}")

    # Validate manifest
    validator = ChunkValidator()
    manifest = validator.validate_manifest(body)
    if manifest is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid manifest data",
        )

    # Create pending batch
    batch = ReceivedBatch(
        batch_id=manifest.batch_id,
        total_chunks=manifest.total_chunks,
        chunk_size=manifest.chunk_size,
        expected_checksum=manifest.checksum,
        snapshot_count=manifest.snapshot_count,
    )

    # Store in registry and file system
    _batch_registry[batch.batch_id] = batch
    _manifest_registry[batch.batch_id] = manifest

    storage = ReceiverStorage()
    storage.save_batch(batch)

    logger.info(
        "Manifest received for batch %s: %d chunks, %d snapshots",
        batch.batch_id,
        batch.total_chunks,
        batch.snapshot_count,
    )

    return JSONResponse(
        status_code=201,
        content={
            "status": "accepted",
            "batch_id": batch.batch_id,
            "total_chunks": batch.total_chunks,
            "message": "Manifest accepted. Ready to receive chunks.",
        },
    )


@app.post("/sync/chunk")
async def receive_chunk(
    request: Request,
    x_sync_key: Optional[str] = Header(None, alias="X-Sync-Key"),
):
    """
    Receive a single sync chunk.

    Required JSON body:
        {
            "batch_id": str,
            "chunk_number": int,
            "payload": str (base64-encoded bytes),
            "checksum": str (SHA-256 hex of raw payload)
        }
    """
    _require_auth(x_sync_key)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}")

    # Validate required fields
    required = ["batch_id", "chunk_number", "payload", "checksum"]
    for field in required:
        if field not in body:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}",
            )

    batch_id = body["batch_id"]
    chunk_number = int(body["chunk_number"])
    payload_b64 = body["payload"]
    checksum = body["checksum"]

    # Decode base64 payload
    import base64

    try:
        payload = base64.b64decode(payload_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid base64 payload: {exc}",
        )

    # Check for duplicate
    storage = ReceiverStorage()
    if storage.chunk_exists(batch_id, chunk_number):
        ack = SyncAck(
            batch_id=batch_id,
            chunk_number=chunk_number,
            status="duplicate",
            message=f"Chunk {chunk_number} already received for batch {batch_id}",
            checksum_valid=False,
        )
        return JSONResponse(
            status_code=200,
            content=ack.to_dict(),
        )

    # Validate chunk checksum
    actual_checksum = __import__("hashlib").sha256(payload).hexdigest()
    if actual_checksum != checksum:
        ack = SyncAck(
            batch_id=batch_id,
            chunk_number=chunk_number,
            status="rejected",
            message=f"Checksum mismatch for chunk {chunk_number}",
            checksum_valid=False,
        )
        return JSONResponse(
            status_code=400,
            content=ack.to_dict(),
        )

    # Create chunk record
    chunk = ReceivedChunk(
        batch_id=batch_id,
        chunk_number=chunk_number,
        payload=payload,
        checksum=checksum,
    )

    # Store chunk file
    storage.save_chunk(chunk)

    # Update batch registry
    if batch_id in _batch_registry:
        batch = _batch_registry[batch_id]
        # Create updated batch with new chunk
        updated_chunks = dict(batch.chunks)
        updated_chunks[chunk_number] = chunk
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
            status="pending",
        )
        _batch_registry[batch_id] = updated_batch
        storage.save_batch(updated_batch)

        # Check if batch is now complete
        if updated_batch.is_complete:
            # Validate and reassemble
            validator = ChunkValidator(storage)
            manifest = _manifest_registry.get(batch_id)
            if manifest:
                validation = validator.validate_complete_batch(
                    updated_batch,
                    manifest,
                )
                if validation.get("final_checksum_valid") is True:
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
                        status="complete",
                        completed_at=__import__("datetime").datetime.now(
                            tz=__import__("datetime").timezone.utc
                        ).isoformat(),
                    )
                    _batch_registry[batch_id] = updated_batch
                    storage.save_batch(updated_batch)

                    logger.info(
                        "Batch %s complete and validated",
                        batch_id,
                    )
                else:
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
                        status="failed",
                        error_message="Final checksum validation failed",
                    )
                    _batch_registry[batch_id] = updated_batch
                    storage.save_batch(updated_batch)

    ack = SyncAck(
        batch_id=batch_id,
        chunk_number=chunk_number,
        status="accepted",
        message=f"Chunk {chunk_number} accepted for batch {batch_id}",
        checksum_valid=True,
    )

    return JSONResponse(
        status_code=201,
        content=ack.to_dict(),
    )


@app.get("/sync/status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    x_sync_key: Optional[str] = Header(None, alias="X-Sync-Key"),
):
    """
    Get the status of a sync batch.

    Returns the current state of the batch including
    which chunks have been received and whether the batch
    is complete.
    """
    _require_auth(x_sync_key)

    # Check in-memory registry first
    if batch_id in _batch_registry:
        batch = _batch_registry[batch_id]
        return JSONResponse(
            status_code=200,
            content={
                "batch_id": batch.batch_id,
                "status": batch.status,
                "total_chunks": batch.total_chunks,
                "received_chunks": len(batch.chunks),
                "missing_chunks": batch.missing_chunks,
                "is_complete": batch.is_complete,
                "completed_at": batch.completed_at,
                "error_message": batch.error_message,
            },
        )

    # Fall back to file storage
    storage = ReceiverStorage()
    batch = storage.load_batch(batch_id)
    if batch is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batch {batch_id} not found",
        )

    return JSONResponse(
        status_code=200,
        content={
            "batch_id": batch.batch_id,
            "status": batch.status,
            "total_chunks": batch.total_chunks,
            "received_chunks": len(batch.chunks),
            "missing_chunks": batch.missing_chunks,
            "is_complete": batch.is_complete,
            "completed_at": batch.completed_at,
            "error_message": batch.error_message,
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint — no authentication required."""
    storage = ReceiverStorage()
    batch_count = len(_batch_registry)

    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "sync-receiver",
            "batch_count": batch_count,
            "storage_dir": str(storage.base_dir),
        },
    )
