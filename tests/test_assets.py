from pathlib import Path


REQUIRED_ASSETS = [
    "data/blocks-main/102-fund-alice.hex",
    "data/blocks-main/103-alice-pays-bob.hex",
    "data/blocks-main/104-bob-pays-carol.hex",
    "data/blocks-invalid/102-bad-merkle.hex",
    "data/blocks-invalid/102-truncated.hex",
    "data/tx/103-alice-pays-bob.hex",
    "data/prevouts/103-input0-correct.json",
    "data/prevouts/103-input0-wrong-amount.json",
    "data/prevouts/103-input0-wrong-script.json",
    "data/meta/block-hashes.json",
]


def test_required_assets_exist():
    for path in REQUIRED_ASSETS:
        assert Path(path).is_file(), path


def test_prefix_assets_are_complete():
    paths = sorted(Path("data/blocks-prefix").glob("*.hex"))
    assert len(paths) == 101
    assert paths[0].name == "001.hex"
    assert paths[-1].name == "101.hex"

