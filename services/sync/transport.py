from __future__ import annotations

import base64
import requests
import logging

from services.sync.models import SyncBatch

logger = logging.getLogger(__name__)


class SyncTransport:
    """
    HTTP transport from Iran sender to external receiver.
    """

    def __init__(
        self,
        target_url: str,
        api_key: str,
        timeout: int = 120,
    ):
        self.target_url = target_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self):
        return {
            "X-Sync-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def send_manifest(self, batch: SyncBatch):

        manifest = batch._manifest

        payload = {
            "batch_id": manifest.batch_id,
            "total_chunks": manifest.total_chunks,
            "chunk_size": manifest.chunk_size,
            "checksum": manifest.checksum,
            "snapshot_count": manifest.snapshot_count,
            "created_at": manifest.created_at,
            "source": manifest.source,
            "target": manifest.target,
        }

        r = requests.post(
            f"{self.target_url}/sync/manifest",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

        r.raise_for_status()

        return r.json()


    def send_chunks(self, batch: SyncBatch):

        results = []

        for chunk in batch._chunks:

            payload = {
                "batch_id": chunk.batch_id,
                "chunk_number": chunk.chunk_index,
                "payload": base64.b64encode(
                    chunk.data
                ).decode(),
                "checksum": chunk.checksum,
            }

            r = requests.post(
                f"{self.target_url}/sync/chunk",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )

            r.raise_for_status()

            results.append(r.json())

        return results


    def send_batch(self, batch: SyncBatch):

        manifest = self.send_manifest(batch)

        chunks = self.send_chunks(batch)

        return {
            "manifest": manifest,
            "chunks": chunks,
        }
