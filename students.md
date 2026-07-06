# Bitcoin Validation Without a Node

A guided workshop on `libbitcoinkernel`, using Python bindings to explore Bitcoin Core’s validation engine without building a full Bitcoin node.

The goal of this workshop is not to implement P2P networking, RPC, wallet logic, mempool policy, or a block explorer. The goal is to understand what `libbitcoinkernel` can know at each layer:

```text
raw bytes
  -> parsed opaque Bitcoin objects
  -> context-free validation
  -> script validation with explicitly supplied context
  -> chainstate-backed block processing
  -> validation callbacks
  -> active-chain updates and reorgs
```

You will build a small command-line tool called `kernel-lab` that consumes pre-generated regtest fixtures under `data/`.

Bitcoin Core was used to generate these fixtures, but Bitcoin Core does **not** need to be running during the workshop.

---

## Prerequisites

You should have:

- Python 3.11+
- Git
- A working installation of the workshop dependencies
- Basic familiarity with Bitcoin blocks, transactions, and the UTXO model

You do **not** need:

- A running Bitcoin Core node
- A synced blockchain
- P2P networking
- RPC access
- Wallet setup

The workshop uses pre-generated regtest blocks and transactions committed to the repository.

---

## What you are building

You will implement a small CLI with commands like:

```bash
kernel-lab parse-block data/blocks-main/102-fund-alice.hex
kernel-lab parse-tx data/tx/103-alice-pays-bob.hex
kernel-lab check-block data/blocks-main/102-fund-alice.hex
kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex
kernel-lab verify-script data/prevouts/103-input0-correct.json
kernel-lab replay-main --kernel-datadir .kernel-lab/main
kernel-lab missing-prev --kernel-datadir .kernel-lab/missing-prev
kernel-lab reorg --kernel-datadir .kernel-lab/reorg
```

The code is written in Python using `py-bitcoinkernel`, imported as:

```python
import pbk
```

Even though we are using Python, the workshop is about `libbitcoinkernel`, not about hiding the kernel behind a high-level abstraction. When possible, pay attention to the conceptual C API operation behind each Python call.

For example:

```python
block = pbk.Block(raw)
```

Conceptually corresponds to creating a kernel block object from serialized bytes, similar to the C API’s `btck_block_create(...)`.

---

## Fixture overview

The repository contains pre-generated regtest data.

```text
data/
  blocks-prefix/
    001.hex
    ...
    101.hex

  blocks-main/
    102-fund-alice.hex
    103-alice-pays-bob.hex
    104-bob-pays-carol.hex

  blocks-invalid/
    102-bad-merkle.hex
    102-truncated.hex

  blocks-reorg/
    common/
      102-fund-alice.hex
      103-alice-pays-bob.hex
      104-bob-pays-carol.hex
    a/
      105a.hex
      106a.hex
    b/
      105b.hex
      106b.hex
      107b.hex

  tx/
    102-fund-alice.hex
    103-alice-pays-bob.hex
    104-bob-pays-carol.hex

  prevouts/
    103-input0-correct.json
    103-input0-wrong-amount.json
    103-input0-wrong-script.json

  scenarios/
    missing-prev.json
    reorg.json

  meta/
    block-hashes.json
    txids.json
    *.block.json
    *.tx.json
```

The `blocks-prefix/` files are intentionally boring. They exist to create mature coinbase outputs. On regtest, coinbase outputs still require maturity before they can be spent, so the interesting tutorial blocks begin only after the 101-block prefix.

---

# Workshop sequence

## Step 1 — Read raw bytes

### Files to use

```text
data/blocks-main/102-fund-alice.hex
data/tx/103-alice-pays-bob.hex
```

### What to build

Implement helper functions to read hex files into raw bytes:

```python
def read_hex(path: Path) -> bytes:
    ...
```

### What to focus on

At this point, the data is just bytes.

Do not treat the block as “valid” yet. Do not even treat it as a parsed Bitcoin block yet. It is only serialized consensus data.

The first distinction is:

```text
raw bytes are not parsed objects
parsed objects are not necessarily valid objects
valid objects are not necessarily connectable to chainstate
```

---

## Step 2 — Parse a block into an opaque kernel object

### Files to use

```text
data/blocks-main/102-fund-alice.hex
```

### What to build

Implement:

```bash
kernel-lab parse-block data/blocks-main/102-fund-alice.hex
```

The command should:

1. Read the hex file.
2. Construct a `pbk.Block`.
3. Print basic information:
   - block hash
   - previous block hash
   - number of transactions
   - coinbase transaction id
   - first non-coinbase transaction id, if present

### Conceptual C API mapping

```python
block = pbk.Block(raw)
```

Conceptually maps to:

```text
btck_block_create(raw, raw_len)
```

### What to focus on

The block object is an opaque kernel object.

You are not manually decoding every field. You are asking the kernel library to parse serialized consensus bytes and give you a handle to a Bitcoin block.

Pay attention to object ownership and views:

- A block object owns or references kernel-managed data.
- Transactions obtained from a block may be views into that block.
- A view is not necessarily an independent copy.

Python makes this safer, but the underlying C API still has explicit ownership and lifetime rules.

---

## Step 3 — Parse a transaction

### Files to use

```text
data/tx/103-alice-pays-bob.hex
```

### What to build

Implement:

```bash
kernel-lab parse-tx data/tx/103-alice-pays-bob.hex
```

The command should:

1. Read the transaction hex.
2. Construct a `pbk.Transaction`.
3. Print:
   - txid
   - number of inputs
   - number of outputs
   - each output amount
   - each output scriptPubKey, if exposed by the binding

### Conceptual C API mapping

```python
tx = pbk.Transaction(raw)
```

Conceptually maps to creating a kernel transaction object from serialized bytes.

### What to focus on

A transaction can be parsed without knowing whether it is spendable, confirmed, final, standard, or valid in the current chain.

Parsing is only the first layer.

---

## Step 4 — Context-free block validation

### Files to use

```text
data/blocks-main/102-fund-alice.hex
data/blocks-invalid/102-bad-merkle.hex
data/blocks-invalid/102-truncated.hex
```

### What to build

Implement:

```bash
kernel-lab check-block data/blocks-main/102-fund-alice.hex
kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex
kernel-lab check-block data/blocks-invalid/102-truncated.hex
```

The command should:

1. Try to parse the block.
2. If parsing succeeds, run context-free block validation.
3. Print the validation mode/result.

Suggested behavior:

```text
102-fund-alice.hex:
  parses
  context-free validation succeeds

102-bad-merkle.hex:
  parses
  context-free validation fails

102-truncated.hex:
  fails before validation because it cannot be parsed as a block
```

### Conceptual C API mapping

```python
state = block.check(consensus_params, pbk.BlockCheckFlags.ALL)
```

Conceptually maps to:

```text
btck_block_check(...)
```

### What to focus on

Context-free block validation does **not** require the active chain or the UTXO set.

It can answer questions like:

```text
Is this structurally a block?
Does it have a valid merkle root?
Does it satisfy context-free block rules?
```

It cannot answer questions like:

```text
Does this block connect to my current tip?
Are the spent outputs available?
Are coinbase spends mature?
Does this block become part of the active chain?
```

That requires chainstate.

---

## Step 5 — Script validation with explicit context

### Files to use

```text
data/tx/103-alice-pays-bob.hex

data/prevouts/103-input0-correct.json
data/prevouts/103-input0-wrong-amount.json
data/prevouts/103-input0-wrong-script.json
```

### What to build

Implement:

```bash
kernel-lab verify-script data/prevouts/103-input0-correct.json
kernel-lab verify-script data/prevouts/103-input0-wrong-amount.json
kernel-lab verify-script data/prevouts/103-input0-wrong-script.json
```

Each JSON file describes the context needed to verify input `0` of the spending transaction:

```json
{
  "spending_tx_file": "data/tx/103-alice-pays-bob.hex",
  "input_index": 0,
  "prevout": {
    "txid": "...",
    "vout": 1,
    "amount_sats": 99999141,
    "script_pubkey_hex": "0014..."
  }
}
```

The command should:

1. Load the spending transaction.
2. Load the previous output scriptPubKey and amount from the JSON fixture.
3. Verify the selected input using the given context.
4. Report success or failure.

Expected behavior:

```text
103-input0-correct.json:
  succeeds

103-input0-wrong-amount.json:
  fails

103-input0-wrong-script.json:
  fails
```

### Conceptual C API mapping

This corresponds to script verification against an explicitly supplied previous output contract.

The key data is:

```text
spending transaction
input index
previous output scriptPubKey
previous output amount
script verification flags
```

### What to focus on

This is not full transaction validation.

You are verifying that one input satisfies one explicitly supplied previous-output contract.

Chainstate-backed validation asks more:

```text
Does this previous output actually exist?
Is it unspent?
Is it mature, if it came from a coinbase?
Does it belong to the active chain?
```

Script verification shows why transaction validity is contextual.

A transaction is not simply “valid by itself.”

---

## Step 6 — Create a fresh chainstate

### Files to use

```text
data/blocks-prefix/001.hex
...
data/blocks-prefix/101.hex
```

### What to build

Create a helper that initializes a fresh regtest chainstate manager.

Suggested CLI usage:

```bash
kernel-lab replay-main --kernel-datadir .kernel-lab/main
```

The command should reset the kernel datadir by default.

The chainstate datadir used by `libbitcoinkernel` should be separate from any Bitcoin Core datadir.

Suggested convention:

```text
.bitcoin-core-regtest/
  used only to generate fixtures
  not used during the tutorial
  not committed

.kernel-lab/
  used by py-bitcoinkernel during the tutorial
  created fresh for each scenario
  not committed
```

### What to focus on

The kernel chainstate is stateful.

Once you begin processing blocks, the library maintains data such as:

```text
block index
active chain
UTXO set
block data
undo data, if available
```

This is a different layer from context-free validation.

---

## Step 7 — Replay the prefix

### Files to use

```text
data/blocks-prefix/001.hex
...
data/blocks-prefix/101.hex
```

### What to build

Implement a function:

```python
def replay_prefix(chainman) -> None:
    ...
```

It should process all prefix blocks in sorted order.

Do not print one line per prefix block unless debugging. For the workshop, summarize:

```text
Replayed 101 prefix blocks.
```

### What to focus on

These blocks are boring on purpose.

Their job is to create a mature UTXO set so that later transactions can spend coinbase-derived funds.

This is a useful lesson: some validation context is historical. The validity of a block at height 103 depends on state built from previous blocks.

---

## Step 8 — Process the main chain

### Files to use

```text
data/blocks-main/102-fund-alice.hex
data/blocks-main/103-alice-pays-bob.hex
data/blocks-main/104-bob-pays-carol.hex
```

### What to build

Complete:

```bash
kernel-lab replay-main --kernel-datadir .kernel-lab/main
```

The command should:

1. Reset the kernel datadir.
2. Create a chainstate manager.
3. Replay the 101-block prefix.
4. Process blocks 102, 103, and 104.
5. Print validation events.
6. Print the active chain tip.

### Conceptual C API mapping

```python
chainman.process_block(block)
```

Conceptually maps to:

```text
btck_chainstate_manager_process_block(...)
```

### What to focus on

Processing a block is not the same as checking a block.

Context-free checking asks:

```text
Is this block structurally valid?
```

Chainstate-backed processing asks:

```text
Can this block connect to the known chainstate?
Does it update the UTXO set?
Does it extend or reorganize the active chain?
```

Also pay attention to this important distinction:

```text
The direct return value of process_block is not the full validation verdict.
Detailed validation information is observed through validation callbacks.
```

---

## Step 9 — Add validation callbacks

### Files to use

Same as Step 8.

```text
data/blocks-prefix/*.hex
data/blocks-main/*.hex
```

### What to build

Implement a callback recorder for:

```text
block_checked
block_connected
block_disconnected
```

Your recorder should collect events and print them in a readable format.

Example output:

```text
[callback:block_checked]
hash: ...
result: valid

[callback:block_connected]
height: 102
hash: ...

[callback:block_connected]
height: 103
hash: ...
```

### What to focus on

Callbacks are how you observe validation and chain updates.

This is especially important for:

```text
invalid blocks
missing parents
reorgs
block connection
block disconnection
```

Do not confuse “the function returned” with “the block is valid and connected.”

---

## Step 10 — Missing previous block scenario

### Files to use

```text
data/scenarios/missing-prev.json

data/blocks-prefix/*.hex
data/blocks-main/102-fund-alice.hex
data/blocks-main/104-bob-pays-carol.hex
```

### What to build

Implement:

```bash
kernel-lab missing-prev --kernel-datadir .kernel-lab/missing-prev
```

The scenario should:

1. Reset the kernel datadir.
2. Replay the prefix.
3. Process block 102.
4. Skip block 103.
5. Try to process block 104.
6. Print the callback events and active tip.

### Expected lesson

Block 104 is not malformed bytes.

Block 104 may even pass context-free validation.

But block 104 points to block 103 as its previous block. If block 103 is missing from the chainstate, block 104 cannot connect.

This demonstrates the difference between:

```text
context-free validity
```

and:

```text
chainstate-backed validity
```

---

## Step 11 — Reorg scenario

### Files to use

```text
data/scenarios/reorg.json

data/blocks-prefix/*.hex

data/blocks-reorg/common/
  102-fund-alice.hex
  103-alice-pays-bob.hex
  104-bob-pays-carol.hex

data/blocks-reorg/a/
  105a.hex
  106a.hex

data/blocks-reorg/b/
  105b.hex
  106b.hex
  107b.hex

data/meta/block-hashes.json
```

### What to build

Implement:

```bash
kernel-lab reorg --kernel-datadir .kernel-lab/reorg
```

The command should:

1. Reset the kernel datadir.
2. Replay the prefix.
3. Process the common chain: 102, 103, 104.
4. Process branch A: 105a, 106a.
5. Print the active tip.
6. Process branch B: 105b, 106b, 107b.
7. Print callback events.
8. Print the final active tip.
9. If supported by the binding, look up stale branch block `106a` by hash and inspect its `BlockTreeEntry`.

### Expected lesson

The block tree can contain more blocks than the active chain.

A block can be valid and still not be part of the active chain.

When a heavier branch appears, the active chain can reorganize:

```text
old active branch blocks are disconnected
new branch blocks are connected
stale blocks may remain known in the block tree
```

This is where callbacks become especially important.

---

## Step 12 — Optional walkthrough command

### Files to use

All files from the previous steps.

### What to build

Implement:

```bash
kernel-lab walkthrough --kernel-datadir .kernel-lab/walkthrough
```

This command should run a concise version of the entire tutorial:

```text
1. Parse block 102.
2. Parse transaction 103.
3. Context-free check good block.
4. Context-free check bad-merkle block.
5. Verify script with correct prevout.
6. Verify script with wrong amount.
7. Replay prefix and main chain.
8. Demonstrate missing-prev.
9. Demonstrate reorg.
```

### What to focus on

The walkthrough command is useful for testing and demo rehearsal.

It should not hide the individual steps. It should simply run them in a convenient order.

---

# Suggested implementation modules

You may organize the code however you like, but this layout is recommended:

```text
kernel_lab/
  __init__.py
  cli.py
  io.py
  pretty.py
  kernel.py
  callbacks.py
  script_verify.py
  scenarios.py
```

## `io.py`

Use this for:

```text
read_hex
read_json
sorted_hex_files
reset_dir
data_path
```

## `kernel.py`

Use this for direct interaction with `py-bitcoinkernel`:

```text
make_block
make_tx
consensus_params
check_block_context_free
make_chainman
process_block_file
process_block_files
```

## `callbacks.py`

Use this for:

```text
CallbackRecorder
make_validation_callbacks
```

## `script_verify.py`

Use this for:

```text
verify_prevout_fixture
```

## `scenarios.py`

Use this for:

```text
replay_prefix
replay_main
missing_prev
reorg
walkthrough
```

## `pretty.py`

Use this for stable human-readable output.

## `cli.py`

Use this for command-line parsing and dispatch.

---

# Things to avoid

Do not build a node.

Do not use P2P.

Do not call `bitcoin-cli` from the tutorial code.

Do not require Bitcoin Core to be running.

Do not regenerate fixtures during the workshop.

Do not use a live Bitcoin Core datadir as the kernel datadir.

Do not hide every kernel concept behind a high-level “Node” or “Explorer” abstraction.

The point is to see the kernel boundary clearly.

---

# Suggested final checklist

By the end, these commands should work:

```bash
kernel-lab parse-block data/blocks-main/102-fund-alice.hex
kernel-lab parse-tx data/tx/103-alice-pays-bob.hex

kernel-lab check-block data/blocks-main/102-fund-alice.hex
kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex
kernel-lab check-block data/blocks-invalid/102-truncated.hex

kernel-lab verify-script data/prevouts/103-input0-correct.json
kernel-lab verify-script data/prevouts/103-input0-wrong-amount.json
kernel-lab verify-script data/prevouts/103-input0-wrong-script.json

kernel-lab replay-main --kernel-datadir .kernel-lab/main
kernel-lab missing-prev --kernel-datadir .kernel-lab/missing-prev
kernel-lab reorg --kernel-datadir .kernel-lab/reorg
kernel-lab walkthrough --kernel-datadir .kernel-lab/walkthrough
```

When those commands work, you have a complete solution version of the workshop.

The student starter version can then be created by removing selected implementation pieces and replacing them with TODOs.

