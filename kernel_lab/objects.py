"""Opaque block and transaction object helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import pbk_compat as compat
from .io import read_hex_bytes


@dataclass(frozen=True)
class LoadedObject:
    """Serialized fixture bytes paired with the opaque kernel object they create."""

    path: Path
    raw: bytes
    obj: object


def load_block(path: str | Path) -> LoadedObject:
    """Read a block fixture and construct the corresponding opaque pbk.Block."""
    resolved = Path(path)
    raw = read_hex_bytes(resolved)
    block = compat.create_block(raw)
    return LoadedObject(path=resolved, raw=raw, obj=block)


def load_transaction(path: str | Path) -> LoadedObject:
    """Read a transaction fixture and construct the corresponding opaque pbk.Transaction."""
    resolved = Path(path)
    raw = read_hex_bytes(resolved)
    tx = compat.create_transaction(raw)
    return LoadedObject(path=resolved, raw=raw, obj=tx)


def describe_block(loaded: LoadedObject) -> list[str]:
    """Return stable, human-readable lines describing a loaded block object."""
    tx_count = compat.count_txs(loaded.obj)
    lines = [
        f"source: {loaded.path}",
        f"bytes: {len(loaded.raw)}",
        "object: opaque libbitcoinkernel block",
        f"hash: {compat.block_hash(loaded.obj)}",
    ]
    if tx_count is not None:
        lines.append(f"transactions: {tx_count}")
    return lines


def describe_transaction(loaded: LoadedObject) -> list[str]:
    """Return stable, human-readable lines describing a loaded transaction object."""
    input_count = compat.count_inputs(loaded.obj)
    output_count = compat.count_outputs(loaded.obj)
    lines = [
        f"source: {loaded.path}",
        f"bytes: {len(loaded.raw)}",
        "object: opaque libbitcoinkernel transaction",
        f"txid: {compat.txid(loaded.obj)}",
    ]
    if input_count is not None:
        lines.append(f"inputs: {input_count}")
    if output_count is not None:
        lines.append(f"outputs: {output_count}")
    return lines
