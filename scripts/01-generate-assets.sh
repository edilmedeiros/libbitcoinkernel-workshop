#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_DATADIR="${ROOT}/.bitcoin-core-regtest"
DATA="${ROOT}/data"

CLI=(bitcoin-cli -regtest -datadir="$CORE_DATADIR")

mkdir -p \
  "$DATA/blocks-prefix" \
  "$DATA/blocks-main" \
  "$DATA/blocks-reorg/common" \
  "$DATA/blocks-reorg/a" \
  "$DATA/blocks-reorg/b" \
  "$DATA/tx" \
  "$DATA/meta" \
  "$DATA/scenarios"

# Fresh-ish wallets. Ignore errors if they already exist.
"${CLI[@]}" -named createwallet wallet_name=miner load_on_startup=true >/dev/null 2>&1 || true
"${CLI[@]}" -named createwallet wallet_name=alice load_on_startup=true >/dev/null 2>&1 || true
"${CLI[@]}" -named createwallet wallet_name=bob load_on_startup=true >/dev/null 2>&1 || true
"${CLI[@]}" -named createwallet wallet_name=carol load_on_startup=true >/dev/null 2>&1 || true

MINER_ADDR=$("${CLI[@]}" -rpcwallet=miner getnewaddress "" bech32)
ALICE_ADDR=$("${CLI[@]}" -rpcwallet=alice getnewaddress "" bech32)
BOB_ADDR=$("${CLI[@]}" -rpcwallet=bob getnewaddress "" bech32)
CAROL_ADDR=$("${CLI[@]}" -rpcwallet=carol getnewaddress "" bech32)

# Mine initial blockchain and save the raw blocks
echo "Mining 101 prefix blocks..."
PREFIX_HASHES=$("${CLI[@]}" generatetoaddress 101 "$MINER_ADDR")

echo "$PREFIX_HASHES" > "$DATA/meta/prefix-hashes.json"

i=1
echo "$PREFIX_HASHES" | jq -r '.[]' | while read -r H; do
  FILENAME=$(printf "%03d.hex" "$i")
  "${CLI[@]}" getblock "$H" 0 > "$DATA/blocks-prefix/$FILENAME"
  i=$((i + 1))
done

# Miner -> Alice
echo "Creating block 102: miner funds Alice..."
TX102=$("${CLI[@]}" -rpcwallet=miner sendtoaddress "$ALICE_ADDR" 1.0)
H102=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR" | jq -r '.[0]')
"${CLI[@]}" getblock "$H102" 0 > "$DATA/blocks-main/102-fund-alice.hex"
"${CLI[@]}" getblock "$H102" 3 > "$DATA/meta/102-fund-alice.block.json"
"${CLI[@]}" getrawtransaction "$TX102" 0 "$H102" > "$DATA/tx/102-fund-alice.hex"
"${CLI[@]}" getrawtransaction "$TX102" 2 "$H102" > "$DATA/meta/102-fund-alice.tx.json"

# Alice -> Bob
echo "Creating block 103: Alice pays Bob..."
TX103=$("${CLI[@]}" -rpcwallet=alice sendtoaddress "$BOB_ADDR" 0.4)
H103=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR" | jq -r '.[0]')
"${CLI[@]}" getblock "$H103" 0 > "$DATA/blocks-main/103-alice-pays-bob.hex"
"${CLI[@]}" getblock "$H103" 3 > "$DATA/meta/103-alice-pays-bob.block.json"
"${CLI[@]}" getrawtransaction "$TX103" 0 "$H103" > "$DATA/tx/103-alice-pays-bob.hex"
"${CLI[@]}" getrawtransaction "$TX103" 2 "$H103" > "$DATA/meta/103-alice-pays-bob.tx.json"

# Bob -> Carol
echo "Creating block 104: Bob pays Carol..."
TX104=$("${CLI[@]}" -rpcwallet=bob sendtoaddress "$CAROL_ADDR" 0.2)
H104=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR" | jq -r '.[0]')
"${CLI[@]}" getblock "$H104" 0 > "$DATA/blocks-main/104-bob-pays-carol.hex"
"${CLI[@]}" getblock "$H104" 3 > "$DATA/meta/104-bob-pays-carol.block.json"
"${CLI[@]}" getrawtransaction "$TX104" 0 "$H104" > "$DATA/tx/104-bob-pays-carol.hex"
"${CLI[@]}" getrawtransaction "$TX104" 2 "$H104" > "$DATA/meta/104-bob-pays-carol.tx.json"

cp "$DATA/blocks-main/102-fund-alice.hex" "$DATA/blocks-reorg/common/102-fund-alice.hex"
cp "$DATA/blocks-main/103-alice-pays-bob.hex" "$DATA/blocks-reorg/common/103-alice-pays-bob.hex"
cp "$DATA/blocks-main/104-bob-pays-carol.hex" "$DATA/blocks-reorg/common/104-bob-pays-carol.hex"

# We now extend the blockchain with blocks that will be reorganized
echo "Creating reorg A branch: 105a, 106a..."
MINER_ADDR_A=$("${CLI[@]}" -rpcwallet=miner getnewaddress "branch-a" bech32)
HA105=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR_A" | jq -r '.[0]')
HA106=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR_A" | jq -r '.[0]')
"${CLI[@]}" getblock "$HA105" 0 > "$DATA/blocks-reorg/a/105a.hex"
"${CLI[@]}" getblock "$HA106" 0 > "$DATA/blocks-reorg/a/106a.hex"

# Then the reorg blocks...
echo "Invalidating A branch to mine longer B branch from common tip..."
"${CLI[@]}" invalidateblock "$HA105"

echo "Creating reorg B branch: 105b, 106b, 107b..."
MINER_ADDR_B=$("${CLI[@]}" -rpcwallet=miner getnewaddress "branch-b" bech32)
HB105=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR_B" | jq -r '.[0]')
HB106=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR_B" | jq -r '.[0]')
HB107=$("${CLI[@]}" generatetoaddress 1 "$MINER_ADDR_B" | jq -r '.[0]')
"${CLI[@]}" getblock "$HB105" 0 > "$DATA/blocks-reorg/b/105b.hex"
"${CLI[@]}" getblock "$HB106" 0 > "$DATA/blocks-reorg/b/106b.hex"
"${CLI[@]}" getblock "$HB107" 0 > "$DATA/blocks-reorg/b/107b.hex"

# Create metadate for the generated assets
cat > "$DATA/meta/block-hashes.json" <<EOF
{
  "102": "$H102",
  "103": "$H103",
  "104": "$H104",
  "105a": "$HA105",
  "106a": "$HA106",
  "105b": "$HB105",
  "106b": "$HB106",
  "107b": "$HB107"
}
EOF

cat > "$DATA/meta/txids.json" <<EOF
{
  "102_fund_alice": "$TX102",
  "103_alice_pays_bob": "$TX103",
  "104_bob_pays_carol": "$TX104"
}
EOF

cat > "$DATA/scenarios/missing-prev.json" <<EOF
{
  "description": "Replay prefix, then process 102 and 104 while skipping 103.",
  "process": [
    "data/blocks-main/102-fund-alice.hex",
    "data/blocks-main/104-bob-pays-carol.hex"
  ],
  "expected_lesson": "The block can parse and pass context-free checks while failing to connect to chainstate."
}
EOF

cat > "$DATA/scenarios/reorg.json" <<EOF
{
  "description": "Replay common chain, then A branch, then longer B branch.",
  "common": [
    "data/blocks-main/102-fund-alice.hex",
    "data/blocks-main/103-alice-pays-bob.hex",
    "data/blocks-main/104-bob-pays-carol.hex"
  ],
  "branch_a": [
    "data/blocks-reorg/a/105a.hex",
    "data/blocks-reorg/a/106a.hex"
  ],
  "branch_b": [
    "data/blocks-reorg/b/105b.hex",
    "data/blocks-reorg/b/106b.hex",
    "data/blocks-reorg/b/107b.hex"
  ],
  "expected_lesson": "The active chain can change while stale branch blocks remain addressable through the block tree."
}
EOF

echo "Assets generated."
