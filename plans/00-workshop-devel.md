# Python libbitcoinkernel Workshop Solution Plan

This plan covers the complete solution version of the workshop code. The goal is
conceptual clarity and deterministic demo execution, not a production Bitcoin
application.

The tutorial code must consume only committed fixtures under `data/`, create a
fresh py-bitcoinkernel datadir for each scenario by default, and must not require
Bitcoin Core, RPC, P2P, `bitcoin-cli`, or a live node during the workshop.

## 1. Inspect the py-bitcoinkernel API

Before implementing behavior, inspect the installed `py-bitcoinkernel` package
and adapt to the API that is actually present.

Confirm:

- Object construction for blocks and transactions, such as `pbk.Block(raw)` and
  `pbk.Transaction(raw)`.
- Block and transaction inspection methods for hashes, headers, transaction
  counts, inputs, and outputs.
- Context-free block validation API.
- Script verification API, including SegWit v0 flags and
  `precomputed_txdata=None` behavior.
- Chainstate construction APIs:
  - `Context`
  - `ContextOptions`
  - `ChainstateManagerOptions`
  - `ChainstateManager`
  - fallback `pbk.load_chainman`, if needed
- Callback registration names and callback signatures for:
  - `block_checked`
  - `block_connected`
  - `block_disconnected`
- Whether block-tree entry inspection is exposed by the binding.

Keep API compatibility code isolated so the rest of the tutorial reads like a
clear walkthrough of kernel concepts.

## 2. Create the Project Skeleton

Add:

- `pyproject.toml`
- `kernel_lab/__init__.py`
- `kernel_lab/cli.py`
- `kernel_lab/io.py`
- `kernel_lab/objects.py`
- `kernel_lab/script.py`
- `kernel_lab/chainstate.py`
- `kernel_lab/callbacks.py`
- `kernel_lab/scenarios.py`
- `tests/`
- `README-dev.md`

Expose the CLI with:

```toml
[project.scripts]
kernel-lab = "kernel_lab.cli:main"
```

Use `argparse` unless an existing project convention appears during
implementation.

## 3. Add Shared Helpers

Implement small, explicit helpers:

- `read_hex_bytes(path)`
- `load_json(path)`
- `load_block(path)`
- `load_transaction(path)`
- `reset_kernel_datadir(path)`
- `format_hash(...)`
- `describe_block(...)`
- `describe_transaction(...)`

The solution should keep the conceptual C API boundary visible through comments
and naming. For example:

```python
# Conceptual C API boundary:
#   pbk.Block(raw) corresponds to creating a btck_Block from serialized bytes.
block = pbk.Block(raw)
```

The comments should teach what the Python binding is wrapping without pretending
the workshop is about a high-level Python Bitcoin object model.

## 4. Implement Parsing Commands

Required commands:

```bash
kernel-lab parse-block data/blocks-main/102-fund-alice.hex
kernel-lab parse-tx data/tx/103-alice-pays-bob.hex
```

Output should be human-readable and stable:

- source path
- byte length
- object type
- block hash or txid, if exposed
- transaction count for blocks, if exposed
- input and output counts for transactions, if exposed

Wording should make clear that these are opaque kernel objects created from raw
serialized bytes.

## 5. Implement Context-Free Block Validation

Required commands:

```bash
kernel-lab check-block data/blocks-main/102-fund-alice.hex
kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex
kernel-lab check-block data/blocks-invalid/102-truncated.hex
```

Expected behavior:

- `data/blocks-main/102-fund-alice.hex` parses and passes context-free checks.
- `data/blocks-invalid/102-bad-merkle.hex` parses but fails context-free
  validation.
- `data/blocks-invalid/102-truncated.hex` fails parsing before validation.

Output should distinguish:

- parse failure
- parsed successfully but context-free invalid
- parsed successfully and context-free valid

## 6. Implement Script Verification

Required commands:

```bash
kernel-lab verify-script data/prevouts/103-input0-correct.json
kernel-lab verify-script data/prevouts/103-input0-wrong-amount.json
kernel-lab verify-script data/prevouts/103-input0-wrong-script.json
```

Use the prevout JSON fixtures:

- spending transaction file
- input index
- previous output txid and vout
- previous output amount
- previous output scriptPubKey

The lesson should be explicit:

- The kernel does not look up the prevout for this call.
- The caller supplies the spending transaction, previous output script, amount,
  input index, and flags.
- Use the SegWit v0 path with `precomputed_txdata=None` unless the binding
  requires a different shape.

Expected demonstrations:

- Correct prevout verifies successfully.
- Wrong amount fails.
- Wrong scriptPubKey fails.

## 7. Implement Deterministic Chainstate Setup

Add a chainstate helper that:

- Resets `--kernel-datadir` by default.
- Replays `data/blocks-prefix/001.hex` through `data/blocks-prefix/101.hex`
  before scenario blocks.
- Constructs explicit context and chainstate manager options when exposed by the
  binding.
- Falls back to `pbk.load_chainman` only through a compatibility helper when
  necessary.

The datadirs under `.kernel-lab/` are disposable and should be safe to recreate
for each run.

## 8. Implement CallbackRecorder

Add `CallbackRecorder` for:

- `block_checked`
- `block_connected`
- `block_disconnected`

It should store structured events and print stable summaries containing fields
when exposed:

- event type
- block hash
- height
- validation result or validation state

Important teaching point:

`process_block(...)` may return only a direct processing status. The detailed
validation verdict should be observed through validation callbacks.

## 9. Implement Scenario Commands

Required commands:

```bash
kernel-lab replay-main --kernel-datadir .kernel-lab/main
kernel-lab missing-prev --kernel-datadir .kernel-lab/missing-prev
kernel-lab reorg --kernel-datadir .kernel-lab/reorg
kernel-lab walkthrough --kernel-datadir .kernel-lab/walkthrough
```

### `replay-main`

Flow:

1. Reset the kernel datadir.
2. Replay prefix blocks `001` through `101`.
3. Process:
   - `data/blocks-main/102-fund-alice.hex`
   - `data/blocks-main/103-alice-pays-bob.hex`
   - `data/blocks-main/104-bob-pays-carol.hex`
4. Print callback summaries and final active-chain tip.

Expected final tip:

```text
65302772c19d3b0b6a66da690a8cac192e40f5d557c1ab9d3314b19fd372a5df
```

This is block `104` from `data/meta/block-hashes.json`.

### `missing-prev`

Flow:

1. Reset the kernel datadir.
2. Replay prefix blocks `001` through `101`.
3. Process `data/blocks-main/102-fund-alice.hex`.
4. Skip `data/blocks-main/103-alice-pays-bob.hex`.
5. Attempt to process `data/blocks-main/104-bob-pays-carol.hex`.

Lesson:

`104` can parse and pass context-free checks, but it cannot connect to
chainstate because required context is missing. The active chain should not
advance through block `104`.

## `reorg`

Flow:

1. Reset the kernel datadir.
2. Replay prefix blocks `001` through `101`.
3. Process common chain:
   - `data/blocks-main/102-fund-alice.hex`
   - `data/blocks-main/103-alice-pays-bob.hex`
   - `data/blocks-main/104-bob-pays-carol.hex`
4. Process branch A:
   - `data/blocks-reorg/a/105a.hex`
   - `data/blocks-reorg/a/106a.hex`
5. Process longer branch B:
   - `data/blocks-reorg/b/105b.hex`
   - `data/blocks-reorg/b/106b.hex`
   - `data/blocks-reorg/b/107b.hex`
6. Print callback summaries showing disconnect/connect behavior during the
   active-chain transition.
7. If the binding exposes block-tree APIs, inspect stale branch A entries.
   Otherwise, print a clear note that block-tree inspection is unavailable in
   the installed binding.

Expected final tip:

```text
1f9a335bf09b9f4ef30cfa22e12534fa67fbb28ab16bbab72d11ac5ac6e435bc
```

This is block `107b` from `data/meta/block-hashes.json`.

### `walkthrough`

Run the complete conceptual sequence:

1. Parse block.
2. Parse transaction.
3. Run context-free check on a valid block.
4. Run context-free check on invalid block fixtures.
5. Verify correct, wrong-amount, and wrong-script prevout fixtures.
6. Replay the main chain.
7. Demonstrate missing-parent or missing-context behavior.
8. Demonstrate reorg behavior.

Use concise section headings and stable output.

## 10. Add Tests

Add pytest coverage for:

- Required fixture assets exist.
- Block parsing succeeds for
  `data/blocks-main/102-fund-alice.hex`.
- Transaction parsing succeeds for
  `data/tx/103-alice-pays-bob.hex`.
- Valid block passes context-free validation.
- Bad-merkle block parses but fails context-free validation.
- Truncated block fails parsing.
- `replay-main` reaches expected block `104` tip:

```text
65302772c19d3b0b6a66da690a8cac192e40f5d557c1ab9d3314b19fd372a5df
```

- `missing-prev` does not advance through block `104`.
- `reorg` ends at expected block `107b` tip:

```text
1f9a335bf09b9f4ef30cfa22e12534fa67fbb28ab16bbab72d11ac5ac6e435bc
```

Prefer testing library functions directly. Add CLI smoke tests only where they
provide meaningful coverage.

## 11. Add README-dev.md

Document:

- How to install or run with `uv`.
- How to run tests:

```bash
uv run pytest
```

- Every required CLI command.
- That Bitcoin Core is not needed during the tutorial.
- That committed fixtures under `data/` are the only data source.
- That `.kernel-lab/*` datadirs are disposable.

## 12. Verify the Complete Solution

Final verification should run:

```bash
uv run pytest
```

Then run every required CLI command:

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

Inspect output for deterministic wording, stable hashes, and clear separation of
kernel concepts:

- serialized bytes
- opaque block and transaction objects
- context-free validation
- explicitly supplied script context
- chainstate-backed block processing
- validation callbacks
- active-chain updates
- missing-parent or missing-context failures
- reorg behavior

