#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

src = DATA / "blocks-main" / "102-fund-alice.hex"
out_dir = DATA / "blocks-invalid"
out_dir.mkdir(parents=True, exist_ok=True)

raw = bytearray(bytes.fromhex(src.read_text().strip()))

# 1. Bad merkle fixture.
#
# Flip the last byte of the serialized block. This keeps the block length unchanged
# and normally leaves the serialization parseable, but changes transaction data,
# so the header merkle root no longer commits to the mutated tx set.
bad_merkle = bytearray(raw)
bad_merkle[-1] ^= 0x01
(out_dir / "102-bad-merkle.hex").write_text(bad_merkle.hex() + "\n")

# 2. Truncated fixture.
#
# This should fail earlier: object construction / parsing, not validation.
truncated = raw[:-1]
(out_dir / "102-truncated.hex").write_text(truncated.hex() + "\n")

print("Wrote:")
print(out_dir / "102-bad-merkle.hex")
print(out_dir / "102-truncated.hex")
