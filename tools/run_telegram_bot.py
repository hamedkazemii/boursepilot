#!/usr/bin/env python3
"""اجرای long-polling ربات دستوری صندوقچی."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.telegram_bot import SandoghchiBot


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = SandoghchiBot()
    bot.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
