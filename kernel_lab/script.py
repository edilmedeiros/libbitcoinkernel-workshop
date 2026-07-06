"""Script verification demonstrations."""

from __future__ import annotations

from pathlib import Path

from . import pbk_compat as compat
from .io import load_json
from .objects import load_transaction


def verify_prevout_fixture(path: str | Path) -> tuple[bool, list[str]]:
    fixture = load_json(path)
    tx_loaded = load_transaction(fixture["spending_tx_file"])
    prevout = fixture["prevout"]
    script_pubkey = bytes.fromhex(prevout["script_pubkey_hex"])
    amount_sats = int(prevout["amount_sats"])
    input_index = int(fixture["input_index"])

    # Conceptual C API boundary:
    #   script verification requires the caller to supply the spending
    #   transaction, input index, previous output scriptPubKey, previous output
    #   amount, verification flags, and optionally precomputed transaction data.
    ok, detail = compat.verify_script(
        tx=tx_loaded.obj,
        input_index=input_index,
        script_pubkey=script_pubkey,
        amount_sats=amount_sats,
    )
    lines = [
        f"source: {path}",
        f"spending_tx: {fixture['spending_tx_file']}",
        f"input_index: {input_index}",
        f"prevout_txid: {prevout['txid']}",
        f"prevout_vout: {prevout['vout']}",
        f"amount_sats: {amount_sats}",
        f"script_pubkey: {prevout['script_pubkey_hex']}",
        f"script_valid: {str(ok).lower()}",
        f"detail: {detail}",
    ]
    return ok, lines

