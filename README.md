# libbitcoinkernel-workshop

This is a hands-on workshop about `libbitcoinkernel`, the extracted Bitcoin
Core validation and chainstate library.

The goal is not to build a Bitcoin node. The exercises focus on the validation
boundaries exposed by the kernel: parsing serialized Bitcoin data, inspecting
opaque block and transaction objects, running context-free block checks,
verifying transaction inputs with explicit previous-output context, processing
blocks through chainstate, observing validation callbacks, and seeing
missing-parent and reorg behavior.

All tutorial data is pre-generated regtest fixture data committed under
`data/`. You do not need Bitcoin Core, `bitcoin-cli`, RPC, P2P, or a live node
while doing the workshop.

## Install

You need `uv` installed on your system.

From the repository root:

```bash
uv sync
source .venv/bin/activate
```

If you are using Nix, enter the development shell first:

```bash
nix develop
uv sync
source .venv/bin/activate
```

After activation, the `kernel-lab` command should be available directly:

```bash
kernel-lab --help
```

## Start

Start the guided workshop with:

```bash
kernel-lab tutorial
```

The tutorial command explains the current lesson, lists the fixture files being
used, identifies the concept to focus on, and shows the primitive command you
should run manually. It does not run the exercise for you.

Navigate with:

```bash
kernel-lab tutorial next
kernel-lab tutorial previous
kernel-lab tutorial overview
```

Use `--plain` if you want deterministic text without colors or panels:

```bash
kernel-lab tutorial --plain
```

## Exercises

The source code contains TODO annotations tied to the tutorial lessons. Those
TODOs mark the places where students should implement or complete something as
they move through the workshop.

