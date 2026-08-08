"""
Sync V1 Worker — file-based sync orchestration.

Reads local state, builds batches from collected snapshots,
pushes chunks to the external receiver, and tracks delivery status.

No database dependencies. No production config changes.
All state is file-based under the configured state directory.
"""

from __future__ import annotations

__version__ = "1.0.0"
