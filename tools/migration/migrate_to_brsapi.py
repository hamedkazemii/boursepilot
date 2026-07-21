#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPLACE = {
    "services.brsapi.all_symbols": "services.brsapi.all_symbols",
    "BRSClient": "BRSClient",
    "Sandoghchi": "Sandoghchi",
    "sandoghchi": "sandoghchi",
}

SKIP = {
    ".git",
    ".venv",
    "__pycache__",
}


count = 0

for path in ROOT.rglob("*.py"):

    if any(x in path.parts for x in SKIP):
        continue

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    original = text

    for old, new in REPLACE.items():
        text = text.replace(old, new)

    if text != original:
        path.write_text(
            text,
            encoding="utf-8",
        )
        count += 1
        print(path)

print()
print("Updated:", count, "files")
