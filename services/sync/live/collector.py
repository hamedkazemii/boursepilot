from __future__ import annotations

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


BASE = Path("data/sync/live")
BASE.mkdir(parents=True, exist_ok=True)


def checksum(data: str) -> str:
    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


def collect_market_snapshot():

    from services.providers.factory import get_market_data_provider

    provider = get_market_data_provider()

    symbols = provider.get_all_symbols()

    payload = {
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "provider": getattr(
            provider,
            "name",
            provider.__class__.__name__
        ),

        "count": len(symbols),

        "symbols": [
            s.raw
            if hasattr(s, "raw")
            else s.__dict__
            for s in symbols
        ]
    }


    raw = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",",":")
    )


    payload["checksum"] = checksum(raw)


    output = BASE / "latest.json"

    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print(
        "SNAPSHOT CREATED",
        output,
        "symbols=",
        len(symbols),
        "checksum=",
        payload["checksum"]
    )


    return output



if __name__ == "__main__":
    collect_market_snapshot()
