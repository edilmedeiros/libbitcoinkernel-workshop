import pytest

from kernel_lab import pbk_compat as compat
from kernel_lab.objects import load_block, load_transaction


pytestmark = pytest.mark.skipif(compat.pbk is None, reason="py-bitcoinkernel not installed")


def test_block_parsing():
    loaded = load_block("data/blocks-main/102-fund-alice.hex")
    assert len(loaded.raw) > 80
    assert compat.block_hash(loaded.obj)


def test_transaction_parsing():
    loaded = load_transaction("data/tx/103-alice-pays-bob.hex")
    assert len(loaded.raw) > 0
    assert compat.txid(loaded.obj)


def test_good_block_context_free_validation():
    loaded = load_block("data/blocks-main/102-fund-alice.hex")
    ok, _detail = compat.check_block(loaded.obj)
    assert ok


def test_bad_merkle_parses_but_fails_context_free_validation():
    loaded = load_block("data/blocks-invalid/102-bad-merkle.hex")
    ok, _detail = compat.check_block(loaded.obj)
    assert not ok


def test_truncated_block_fails_parsing():
    with pytest.raises(Exception):
        load_block("data/blocks-invalid/102-truncated.hex")

