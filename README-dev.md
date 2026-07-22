# NOTES

1. Parse file `data/tx/103-alice-pays-bob.hex`
2. Parse malleated tx: `data/tx/103.alice-pays-bob-malleaated.hex`



# Development Commands

This repository contains the complete solution code for the Python
libbitcoinkernel workshop. The tutorial consumes committed regtest fixtures under
`data/`; Bitcoin Core is not required while running the solution.

Use the Nix development shell if `uv` is not already available:

```bash
nix develop
```

Install and test:

```bash
uv run pytest
```

Run the required commands:

```bash
uv run kernel-lab parse-block data/blocks-main/102-fund-alice.hex
uv run kernel-lab parse-tx data/tx/103-alice-pays-bob.hex
uv run kernel-lab check-block data/blocks-main/102-fund-alice.hex
uv run kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex
uv run kernel-lab check-block data/blocks-invalid/102-truncated.hex
uv run kernel-lab verify-script data/prevouts/103-input0-correct.json
uv run kernel-lab verify-script data/prevouts/103-input0-wrong-amount.json
uv run kernel-lab verify-script data/prevouts/103-input0-wrong-script.json
uv run kernel-lab replay-main --kernel-datadir .kernel-lab/main
uv run kernel-lab missing-prev --kernel-datadir .kernel-lab/missing-prev
uv run kernel-lab reorg --kernel-datadir .kernel-lab/reorg
uv run kernel-lab walkthrough --kernel-datadir .kernel-lab/walkthrough
```

The `.kernel-lab/*` directories are disposable kernel datadirs. Scenario
commands reset their target datadir by default so reruns are deterministic.

Run the instructional tutorial:

```bash
uv run kernel-lab tutorial
uv run kernel-lab tutorial --plain
uv run kernel-lab tutorial overview
uv run kernel-lab tutorial overview --plain
uv run kernel-lab tutorial next
uv run kernel-lab tutorial previous
```

The tutorial command is explanatory only. It prints the current lesson and the
primitive command to run manually; it does not execute that command.

The `.kernel-lab.json` file stores only tutorial position. Use `--plain` for
deterministic text without colors or panels.

