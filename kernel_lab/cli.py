"""Command line interface for the workshop solution."""

from __future__ import annotations

import argparse
import sys
import json
import shutil
from pathlib import Path

try:
    import pbk
except ModuleNotFoundError:  # pragma: no cover - exercised only in broken envs.
    raise RuntimeError(
        "py-bitcoinkernel is not installed. Run inside the project environment."
    )


def print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


# TODO 01: Load file data/tx/103-alice-pays-bob.hex into a Transaction object
def cmd_parse_tx(args: argparse.Namespace) -> int:
    ## 1. Read hex file
    fp = Path(args.path)
    hex = fp.read_text(encoding="utf-8")
    raw = bytes.fromhex(hex)

    ## 2. Create Transaction object
    tx = pbk.Transaction(raw)

    ## 3. Inspect object
    print(f"txid: {tx.txid}")
    print(f"locktime: {tx.locktime}")
    print(f"#inputs: {len(tx.inputs)}")
    for inp in tx.inputs:
        print(f"  txid : {inp.out_point.txid}")
        print(f"  index: {inp.out_point.index}")
    print(f"#outputs: {len(tx.outputs)}")
    for out in tx.outputs:
        print(f"  amount: {out.amount}")
        print(f"  scriptPubKey: {out.script_pubkey}")

    ## 4. Return success
    return 0


# TODO 02: load the file data/blocks-main/102-fund-alice.hex
# and create a Block object.
def cmd_parse_block(args: argparse.Namespace) -> int:
    ## 1. Read hex file
    fp = Path(args.path)
    hex = fp.read_text(encoding="utf-8")
    raw = bytes.fromhex(hex)

    ## 2. Create Block object
    block = pbk.Block(raw)

    ## 3. Inspect object
    print(f"block hash: {block.block_hash}")
    print(f"previous block: {block.block_header.prev_hash}")
    print(f"timestamp: {block.block_header.timestamp}")
    print("transactions:")
    for tx in block.transactions:
        print(f"  {tx.txid}")

    ## 4. Return success
    return 0


# TODO 03: load block and check it
def cmd_check_block(args: argparse.Namespace) -> int:
    ## 1. Read hex file
    fp = Path(args.path)
    hex = fp.read_text(encoding="utf-8")
    raw = bytes.fromhex(hex)

    ## 2. Create block object
    block = pbk.Block(raw)

    ## 3. Check block
    consensus_params = pbk.ChainParameters(pbk.ChainType.REGTEST).consensus_params
    flags = pbk.BlockCheckFlags.MERKLE | pbk.BlockCheckFlags.POW
    state = block.check(consensus_params, flags)

    ## 4. Inpect results
    valid = state.validation_mode == pbk.ValidationMode.VALID
    print(f"context free valid: {str(valid).lower()}")
    print(f"validation mode: {state.validation_mode.name}")
    print(f"validation result: {state.block_validation_result.name}")

    ## 5. Return success
    return 0


# TODO 04: verify script
def cmd_verify_script(args: argparse.Namespace) -> int:
    ## 1. Read json file with required data
    fp = Path(args.path)
    fixture = json.loads(fp.read_text(encoding="utf-8"))

    ## 2. Create transaction object to verify
    tx_path = Path(fixture["spending_tx_file"])
    tx_hex = tx_path.read_text(encoding="utf-8")
    tx_raw = bytes.fromhex(tx_hex)
    tx_loaded = pbk.Transaction(tx_raw)

    ## 3. Get previous output data
    prevout = fixture["prevout"]
    amount_sats = int(prevout["amount_sats"])
    input_index = int(fixture["input_index"])
    script_pubkey = bytes.fromhex(prevout["script_pubkey_hex"])
    spk = pbk.ScriptPubkey(script_pubkey)

    ## 4. Set what we want to verify
    svf = pbk.ScriptVerificationFlags
    flags = svf.P2SH | \
        svf.DERSIG | \
        svf.NULLDUMMY | \
        svf.CHECKLOCKTIMEVERIFY | \
        svf.CHECKSEQUENCEVERIFY | \
        svf.WITNESS

    result = spk.verify(amount_sats, tx_loaded, None, input_index, flags)
    
    ok = bool(result)
    detail = f"status={result}"

    lines = [
        f"source: {args.path}",
        f"spending_tx: {fixture['spending_tx_file']}",
        f"input_index: {input_index}",
        f"prevout_txid: {prevout['txid']}",
        f"prevout_vout: {prevout['vout']}",
        f"amount_sats: {amount_sats}",
        f"script_pubkey: {prevout['script_pubkey_hex']}",
        f"script_valid: {str(ok).lower()}",
        f"detail: {detail}",
    ]
    print_lines(lines)
    return 0 if ok else 2

# TODO 05: Load a series of blocks
def cmd_replay_main(args: argparse.Namespace) -> int:
    ## 1. Reset datadir if requested
    datadir = Path(args.datadir)
    if not args.no_reset:
        if datadir.exists():
            shutil.rmtree(datadir)
    datadir.mkdir(parents=True, exist_ok=True)

    ## 2. Enable logging
    pbk.set_log_level_category(pbk.LogCategory.ALL, pbk.LogLevel.INFO)
    pbk.enable_log_category(pbk.LogCategory.ALL)

    def log_callback(message):
        print(f"{message[:-1]}")

    _logger = pbk.LoggingConnection(log_callback)

    ## 3. Add callbacks
    def block_checked(self, block, state):
        print(f"--- Block checked: {block.block_hash}")

    def pow_valid_block(self, block, entry):
        print(f"--- Block has valid pow: {block.block_hash}")

    def block_connected(self, block, entry):
        print(f"--- Block connected: {block.block_hash}")

    def block_disconnected(self, block, entry):
        print(f"--- Block disconnected: {block.block_hash}")

    callbacks = pbk.ValidationInterfaceCallbacks(
        block_checked=block_checked,
        pow_valid_block=pow_valid_block,
        block_connected=block_connected,
        block_disconnected=block_disconnected)

    ## 4. Open chainstate datadir
    chainman = pbk.load_chainman(datadir, pbk.ChainType.REGTEST, callbacks)

    # 5. Process blocks
    for path in sorted(args.blocks.glob("*.hex")):
        fp = Path(path)
        print(f"--- Processing file {fp}")
        hex = fp.read_text(encoding="utf-8")
        raw = bytes.fromhex(hex)
        block = pbk.Block(raw)
        try:
            chainman.process_block(block)
        except Exception as e:
            print(e)
            return 1

    ## 6. Return success
    return 0

# TODO 06: Process single block
def cmd_process_block(args: argparse.Namespace) -> int:
    ## 1. Get datadir
    datadir = Path(args.datadir)
    datadir.mkdir(parents=True, exist_ok=True)

    ## 2. Enable logging
    pbk.set_log_level_category(pbk.LogCategory.ALL, pbk.LogLevel.INFO)
    pbk.enable_log_category(pbk.LogCategory.ALL)

    def log_callback(message):
        print(f"{message[:-1]}")

    _logger = pbk.LoggingConnection(log_callback)

    ## 3. Add callbacks
    def block_checked(self, block, state):
        print(f"--- Block checked: {block.block_hash}")

    def pow_valid_block(self, block, entry):
        print(f"--- Block has valid pow: {block.block_hash}")

    def block_connected(self, block, entry):
        print(f"--- Block connected: {block.block_hash}")

    def block_disconnected(self, block, entry):
        print(f"--- Block disconnected: {block.block_hash}")

    callbacks = pbk.ValidationInterfaceCallbacks(
        block_checked=block_checked,
        pow_valid_block=pow_valid_block,
        block_connected=block_connected,
        block_disconnected=block_disconnected)

    ## 4. Open chainstate datadir
    chainman = pbk.load_chainman(datadir, pbk.ChainType.REGTEST, callbacks)

    # 5. Process block
    fp = Path(args.block)
    print(f"--- Processing file {fp}")
    hex = fp.read_text(encoding="utf-8")
    raw = bytes.fromhex(hex)
    block = pbk.Block(raw)
    try:
        chainman.process_block(block)
    except Exception as e:
        print(e)
        return 1

    ## 6. Return success
    return 0


# Define command line commands
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kernel-lab",
        description=(
            "A libibtcoinkernel tutorial for exploring Bitcoin validation"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ## 1. Parse transaction
    p = sub.add_parser("parse-tx")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_parse_tx)

    # 2. Parse block
    p = sub.add_parser("parse-block")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_parse_block)

    # 3. Check block
    p = sub.add_parser("check-block")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_check_block)

    p = sub.add_parser("verify-script")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_verify_script)

    p = sub.add_parser("replay-blocks")
    p.add_argument("--datadir", type=Path, required=True)
    p.add_argument("--blocks", type=Path, required=True)
    p.add_argument("--no-reset", action="store_true")
    p.set_defaults(func=cmd_replay_main)

    p = sub.add_parser("process-block")
    p.add_argument("--datadir", type=Path, required=True)
    p.add_argument("--block", type=Path, required=True)
    p.set_defaults(func=cmd_process_block)

    return parser


# Main logic: process command line and finish
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as e:
        print(f"kernel api error: {e}", file=sys.stderr)
        return 3


# Entry point
if __name__ == "__main__":
    raise SystemExit(main())

