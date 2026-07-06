#!/usr/bin/env python3

import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

meta_tx = DATA / "meta" / "103-alice-pays-bob.tx.json"
out_dir = DATA / "prevouts"
out_dir.mkdir(parents=True, exist_ok=True)

tx = json.loads(meta_tx.read_text())

vin0 = tx["vin"][0]
prevout = vin0["prevout"]

amount_btc = Decimal(str(prevout["value"]))
amount_sats = int(amount_btc * Decimal("100000000"))

correct = {
    "spending_tx_file": "data/tx/103-alice-pays-bob.hex",
    "input_index": 0,
    "prevout": {
        "txid": vin0["txid"],
        "vout": vin0["vout"],
        "amount_btc": str(amount_btc),
        "amount_sats": amount_sats,
        "script_pubkey_hex": prevout["scriptPubKey"]["hex"],
    },
}

wrong_amount = json.loads(json.dumps(correct))
wrong_amount["prevout"]["amount_sats"] = amount_sats - 1
wrong_amount["note"] = "Same scriptPubKey, wrong amount by one satoshi."

wrong_script = json.loads(json.dumps(correct))
# OP_TRUE. This is intentionally not the real scriptPubKey.
wrong_script["prevout"]["script_pubkey_hex"] = "51"
wrong_script["note"] = "Wrong previous-output scriptPubKey."

(out_dir / "103-input0-correct.json").write_text(json.dumps(correct, indent=2) + "\n")
(out_dir / "103-input0-wrong-amount.json").write_text(json.dumps(wrong_amount, indent=2) + "\n")
(out_dir / "103-input0-wrong-script.json").write_text(json.dumps(wrong_script, indent=2) + "\n")

print("Wrote prevout fixtures.")
