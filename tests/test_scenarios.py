import pytest

from kernel_lab import pbk_compat as compat
from kernel_lab.chainstate import run_missing_prev, run_reorg, run_replay_main
from kernel_lab.io import block_hashes


pytestmark = pytest.mark.skipif(compat.pbk is None, reason="py-bitcoinkernel not installed")


def test_replay_main_reaches_expected_tip(tmp_path):
    result = run_replay_main(tmp_path / "main")
    assert result.tip == block_hashes()["104"]


def test_missing_prev_does_not_advance_through_104(tmp_path):
    result = run_missing_prev(tmp_path / "missing-prev")
    assert result.tip != block_hashes()["104"]


def test_reorg_ends_at_107b(tmp_path):
    result = run_reorg(tmp_path / "reorg")
    assert result.tip == block_hashes()["107b"]

