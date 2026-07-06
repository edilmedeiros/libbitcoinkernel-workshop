#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

required = [
    DATA / "blocks-prefix" / "001.hex",
    DATA / "blocks-prefix" / "101.hex",
    DATA / "blocks-main" / "102-fund-alice.hex",
    DATA / "blocks-main" / "103-alice-pays-bob.hex",
    DATA / "blocks-main" / "104-bob-pays-carol.hex",
    DATA / "blocks-invalid" / "102-bad-merkle.hex",
    DATA / "blocks-invalid" / "102-truncated.hex",
    DATA / "tx" / "103-alice-pays-bob.hex",
    DATA / "prevouts" / "103-input0-correct.json",
    DATA / "scenarios" / "missing-prev.json",
    DATA / "scenarios" / "reorg.json",
]

missing = [p for p in required if not p.exists()]
if missing:
    print("Missing files:")
    for p in missing:
        print(" ", p)
    raise SystemExit(1)

for p in DATA.rglob("*.hex"):
    s = p.read_text().strip()
    if len(s) % 2 != 0:
        raise SystemExit(f"Odd-length hex file: {p}")
    try:
        bytes.fromhex(s)
    except ValueError as e:
        raise SystemExit(f"Invalid hex in {p}: {e}") from e

print("Asset smoke test passed.")
