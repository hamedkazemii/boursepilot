from __future__ import annotations

import json
import gzip
import hashlib
from pathlib import Path
from datetime import datetime, timezone


OUTPUT = Path("data/sync/live/funds_latest.json")
GZIP_OUTPUT = Path("data/sync/live/funds_latest.json.gz")


class FundSnapshotExporter:

    def __init__(self):
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)


    def checksum(self, data: bytes):
        return hashlib.sha256(data).hexdigest()


    def export(self):

        from services.providers.factory import get_market_data_provider

        provider = get_market_data_provider()

        funds = provider.get_fund_symbols()

        print("FUNDS:", len(funds))


        clean = []

        for f in funds:

            clean.append({
                "symbol": f.symbol,
                "name": f.name,
                "last_price": f.last_price,
                "close_price": f.close_price,
                "change_last": f.change_last,
                "change_last_pct": f.change_last_pct,
                "change_close": f.change_close,
                "change_close_pct": f.change_close_pct,
                "volume": f.volume,
                "value": f.value,
                "trade_count": f.trade_count,
                "market_value": f.market_value,
                "shares": f.shares,
                "time": f.time,
            })


        payload = {
            "type": "fund_market_snapshot",
            "source": "iran-server",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "count": len(clean),
            "checksum": "",
            "funds": clean,
        }


        raw = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":")
        ).encode()


        payload["checksum"] = self.checksum(raw)


        raw = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":")
        ).encode()


        OUTPUT.write_bytes(raw)


        with gzip.open(
            GZIP_OUTPUT,
            "wb",
            compresslevel=9
        ) as f:
            f.write(raw)


        print("JSON:", OUTPUT)
        print("JSON SIZE:", OUTPUT.stat().st_size)
        print("GZIP:", GZIP_OUTPUT)
        print("GZIP SIZE:", GZIP_OUTPUT.stat().st_size)
        print("CHECKSUM:", payload["checksum"])

        return OUTPUT



if __name__ == "__main__":
    FundSnapshotExporter().export()
