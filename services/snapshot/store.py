"""ذخیره اسنپ‌شات روزانه کشف و رنکینگ."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)


class SnapshotStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        default = Path(getattr(settings, "SNAPSHOT_DIR", "") or "data/snapshots")
        self.base_dir = Path(base_dir) if base_dir else default
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _day(self, when: Optional[datetime] = None) -> str:
        dt = when or datetime.now().astimezone()
        return dt.strftime("%Y-%m-%d")

    def path_for(self, kind: str, day: Optional[str] = None) -> Path:
        d = day or self._day()
        folder = self.base_dir / d
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{kind}.json"

    def save_json(self, kind: str, payload: Any, day: Optional[str] = None) -> Path:
        path = self.path_for(kind, day=day)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info("snapshot saved %s", path)
        return path

    def load_json(self, kind: str, day: Optional[str] = None) -> Any:
        path = self.path_for(kind, day=day)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def save_latest(self, kind: str, payload: Any) -> Path:
        """کپی latest برای دسترسی سریع."""
        latest_dir = self.base_dir / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        path = latest_dir / f"{kind}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
