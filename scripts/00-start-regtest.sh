#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_DATADIR="${ROOT}/.bitcoin-core-regtest"

mkdir -p "$CORE_DATADIR"

bitcoind \
  -regtest \
  -datadir="$CORE_DATADIR" \
  -fallbackfee=0.00001 \
  -txindex=1 \
  -daemon

echo "Waiting for bitcoind..."
until bitcoin-cli -regtest -datadir="$CORE_DATADIR" getblockchaininfo >/dev/null 2>&1; do
  sleep 0.2
done

echo "bitcoind ready at $CORE_DATADIR"
