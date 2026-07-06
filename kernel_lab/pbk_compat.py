"""Compatibility helpers around the py-bitcoinkernel binding.

The workshop intentionally exposes the kernel boundary, but the Python binding
API is still young enough that keeping name/signature differences here makes the
lesson code easier to read.

Most functions in this module are thin adapters over `pbk`. They deliberately
keep libbitcoinkernel concepts visible: serialized bytes become opaque kernel
objects, validation receives explicit context, and chainstate work goes through
a chainstate manager plus callbacks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


try:
    import pbk
except ModuleNotFoundError:  # pragma: no cover - exercised only in broken envs.
    pbk = None  # type: ignore[assignment]


class KernelApiError(RuntimeError):
    """Raised when the installed binding does not expose an expected feature."""


def require_pbk() -> Any:
    """Return the imported `pbk` module or raise a clear environment error."""
    if pbk is None:
        raise KernelApiError(
            "py-bitcoinkernel is not installed. Run inside the project environment."
        )
    return pbk


def public_names() -> list[str]:
    """Return public names exposed by the installed `pbk` module."""
    module = require_pbk()
    return [name for name in dir(module) if not name.startswith("_")]


def call_first(candidates: list[Callable[[], Any]], feature: str) -> Any:
    """Try candidate binding calls and return the first one that succeeds."""
    errors: list[str] = []
    for candidate in candidates:
        try:
            return candidate()
        except Exception as exc:  # noqa: BLE001 - compatibility probing.
            errors.append(f"{type(exc).__name__}: {exc}")
    raise KernelApiError(f"Could not use py-bitcoinkernel feature {feature}: {errors}")


def attr_first(obj: Any, names: list[str]) -> Any:
    """Read the first available attribute or zero-argument method from `obj`."""
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            return value() if callable(value) else value
    raise KernelApiError(f"{type(obj).__name__} does not expose any of {names}")


def maybe_attr(obj: Any, names: list[str]) -> Any | None:
    """Read the first available attribute or method, returning `None` if absent."""
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            return value() if callable(value) else value
    return None


def as_hex(value: Any) -> str:
    """Convert binding hash-like values into stable display text."""
    if value is None:
        return "unavailable"
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if hasattr(value, "hex"):
        try:
            return value.hex()
        except TypeError:
            pass
    return str(value)


def create_block(raw: bytes) -> Any:
    """Create an opaque kernel block object from serialized block bytes.

    Conceptual C API mapping:
    - Python: `pbk.Block(raw)`
    - C API idea: create a `btck_Block` handle from serialized bytes

    The returned value is intentionally treated as opaque workshop data. We ask
    the binding for specific views such as hash or transactions, but we do not
    reinterpret it as a general Python-native Bitcoin block.
    """
    module = require_pbk()
    # Conceptual C API boundary:
    #   pbk.Block(raw) corresponds to creating a btck_Block from serialized bytes.
    return module.Block(raw)


def create_transaction(raw: bytes) -> Any:
    """Create an opaque kernel transaction object from serialized tx bytes.

    Conceptual C API mapping:
    - Python: `pbk.Transaction(raw)`
    - C API idea: create a `btck_Transaction` handle from serialized bytes

    The object is useful for kernel calls such as txid inspection and script
    verification, while the serialized fixture bytes remain the source of truth.
    """
    module = require_pbk()
    # Conceptual C API boundary:
    #   pbk.Transaction(raw) corresponds to creating a btck_Transaction from
    #   serialized bytes.
    return module.Transaction(raw)


def block_hash(block: Any) -> str:
    """Return the display hash for an opaque block object."""
    return as_hex(attr_first(block, ["block_hash", "hash", "get_hash", "GetHash"]))


def txid(tx: Any) -> str:
    """Return the display txid for an opaque transaction object."""
    return as_hex(attr_first(tx, ["txid", "hash", "get_hash", "GetHash"]))


def count_txs(block: Any) -> int | None:
    """Return the number of transactions in a block, if exposed by the binding."""
    txs = maybe_attr(block, ["transactions", "txs", "vtx"])
    if txs is not None:
        try:
            return len(txs)
        except TypeError:
            return None
    count = maybe_attr(block, ["transaction_count", "tx_count", "n_tx"])
    return int(count) if count is not None else None


def count_inputs(tx: Any) -> int | None:
    """Return the number of transaction inputs, if exposed by the binding."""
    vin = maybe_attr(tx, ["inputs", "vin"])
    if vin is not None:
        try:
            return len(vin)
        except TypeError:
            return None
    count = maybe_attr(tx, ["input_count", "n_inputs"])
    return int(count) if count is not None else None


def count_outputs(tx: Any) -> int | None:
    """Return the number of transaction outputs, if exposed by the binding."""
    vout = maybe_attr(tx, ["outputs", "vout"])
    if vout is not None:
        try:
            return len(vout)
        except TypeError:
            return None
    count = maybe_attr(tx, ["output_count", "n_outputs"])
    return int(count) if count is not None else None


def check_block(block: Any) -> tuple[bool, str]:
    """Run context-free block validation with explicit regtest parameters.

    Conceptual C API mapping:
    - Python: `block.check(consensus_params, flags)`
    - C API idea: run the kernel's block sanity checks against a `btck_Block`
      using caller-supplied consensus parameters and check flags

    This is "context-free" in the chainstate sense: it checks properties such as
    proof of work and merkle-root consistency without connecting the block to an
    active chain. The caller still supplies chain parameters because the validity
    rules depend on the selected network.
    """
    module = require_pbk()
    consensus_params = module.ChainParameters(module.ChainType.REGTEST).consensus_params
    flags = module.BlockCheckFlags.MERKLE | module.BlockCheckFlags.POW
    # Conceptual C API boundary:
    #   this is the context-free block check path. The caller still supplies
    #   regtest consensus params and explicit check flags.
    state = block.check(consensus_params, flags)
    valid = state.validation_mode == module.ValidationMode.VALID
    detail = (
        f"validation_mode={state.validation_mode.name} "
        f"block_validation_result={state.block_validation_result.name}"
    )
    return valid, detail


def script_flags() -> Any:
    """Build the script verification flags used for the SegWit v0 fixtures.

    Conceptual C API mapping:
    - Python: combine `pbk.ScriptVerificationFlags` values
    - C API idea: pass an explicit script verification flags bitset to the
      kernel script verifier
    """
    module = require_pbk()
    flags = module.ScriptVerificationFlags
    return (
        flags.P2SH
        | flags.DERSIG
        | flags.NULLDUMMY
        | flags.CHECKLOCKTIMEVERIFY
        | flags.CHECKSEQUENCEVERIFY
        | flags.WITNESS
    )


def verify_script(
    *,
    tx: Any,
    input_index: int,
    script_pubkey: bytes,
    amount_sats: int,
) -> tuple[bool, str]:
    """Verify one transaction input against an explicitly supplied prevout.

    Conceptual C API mapping:
    - Python: `pbk.ScriptPubkey(script_pubkey).verify(...)`
    - C API idea: create a scriptPubKey handle from prevout bytes, then verify
      a spending transaction input with caller-supplied amount, input index,
      flags, and optional precomputed transaction data

    This demonstrates a key libbitcoinkernel boundary: the script verifier does
    not look up the previous output. The caller provides the previous output
    script and amount. Supplying the wrong amount or script causes verification
    to fail even when the spending transaction bytes are unchanged.
    """
    module = require_pbk()
    flags = script_flags()
    # Conceptual C API boundary:
    #   the scriptPubKey is an explicit kernel object created from the previous
    #   output script bytes; the amount and spending input index are caller data.
    spk = module.ScriptPubkey(script_pubkey)
    result = spk.verify(amount_sats, tx, None, input_index, flags)
    return bool(result), f"status={result}"


@dataclass
class ChainmanHandle:
    """Bundle a chainstate manager with context and callback objects.

    In the C API these lifetimes are explicit: options, context, callback
    handles, and chainstate manager handles must stay alive for as long as the
    kernel uses them. `pbk.load_chainman` hides part of that setup, but this
    wrapper keeps the ownership relationship visible for the workshop.
    """

    chainman: Any
    context: Any | None = None
    callbacks: Any | None = None


def make_chainman(datadir: Path, recorder: Any | None = None) -> ChainmanHandle:
    """Create a regtest chainstate manager rooted at `datadir`.

    Conceptual C API mapping:
    - Python: `pbk.load_chainman(datadir, ChainType.REGTEST, callbacks)`
    - C API idea: configure context options, validation callbacks, and
      chainstate manager options, then create/load a chainstate manager handle

    The binding helper performs the lower-level option construction for this
    py-bitcoinkernel release. The wrapper keeps callback ownership visible and
    gives the rest of the workshop one stable object to use.
    """
    module = require_pbk()
    datadir = Path(datadir)
    callbacks = None
    if recorder is not None:
        callbacks = module.ValidationInterfaceCallbacks(
            block_checked=recorder.block_checked,
            block_connected=recorder.block_connected,
            block_disconnected=recorder.block_disconnected,
        )
    # Prefer the binding helper because it builds ContextOptions,
    # ChainstateManagerOptions, and ChainstateManager with the expected datadir
    # and regtest chain parameters for this py-bitcoinkernel release.
    chainman = module.load_chainman(datadir, module.ChainType.REGTEST, callbacks)
    return ChainmanHandle(chainman, None, callbacks)


def process_block(chainman: Any, block: Any) -> Any:
    """Submit a block to chainstate-backed processing.

    Conceptual C API mapping:
    - Python: `chainman.process_block(block)`
    - C API idea: process a `btck_Block` through a chainstate manager handle

    The direct return value is not the complete validation story. Detailed
    verdicts, including `MISSING_PREV` and reorg connect/disconnect events, are
    observed through validation callbacks recorded elsewhere in the workshop.
    """
    for name in ["process_block", "ProcessBlock", "processBlock"]:
        if hasattr(chainman, name):
            fn = getattr(chainman, name)
            return fn(block)
    module = require_pbk()
    for name in ["process_block", "ProcessBlock"]:
        if hasattr(module, name):
            fn = getattr(module, name)
            return call_first(
                [
                    lambda: fn(chainman, block),
                    lambda: fn(block, chainman),
                ],
                "process_block",
            )
    raise KernelApiError("Installed py-bitcoinkernel does not expose process_block")


def active_tip(chainman: Any) -> str | None:
    """Return the current active-chain tip hash, if exposed by the binding."""
    if hasattr(chainman, "best_entry"):
        entry = chainman.best_entry
        if entry is not None and hasattr(entry, "block_hash"):
            return as_hex(entry.block_hash)
    for name in ["active_tip", "tip", "get_tip", "get_best_block", "best_block_hash"]:
        value = maybe_attr(chainman, [name])
        if value is not None:
            return as_hex(value)
    return None


def block_tree_entry(chainman: Any, block_hash_hex: str) -> tuple[int, str | None]:
    """Look up a block-tree entry by hash and return its height and parent hash.

    Conceptual C API mapping:
    - Python: `chainman.block_tree_entries[pbk.BlockHash(...)]`
    - C API idea: query the block tree/index for metadata about a known block

    This is how the reorg demo can show that stale branch blocks remain known to
    chainstate even after they are no longer on the active chain.
    """
    module = require_pbk()
    if not hasattr(chainman, "block_tree_entries"):
        raise KernelApiError("block_tree_entries is not exposed")
    # pbk.BlockHash takes internal hash byte order; user-facing fixture hashes
    # are displayed in the conventional reversed hex form.
    block_hash_obj = module.BlockHash(bytes.fromhex(block_hash_hex)[::-1])
    entry = chainman.block_tree_entries[block_hash_obj]
    previous = as_hex(entry.previous.block_hash) if entry.previous is not None else None
    return int(entry.height), previous
