#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_DATADIR="${ROOT}/.bitcoin-core-regtest"
DATA="${ROOT}/data"

bitcoin-cli -regtest -datadir="$CORE_DATADIR" stop >/dev/null 2>&1 || true
rm -rf "$CORE_DATADIR"
echo "Removed $CORE_DATADIR"

rm -rf ${DATA}
echo "Removed $DATA"
