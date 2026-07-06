"""Fixture loading helpers for the workshop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def resolve_repo_path(path: str | Path) -> Path:
    """Return an absolute path, resolving relative paths from the repo root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def read_hex_bytes(path: str | Path) -> bytes:
    """Read a hex fixture file and return the serialized bytes it represents."""
    resolved = resolve_repo_path(path)
    text = resolved.read_text(encoding="utf-8")
    compact = "".join(text.split())
    return bytes.fromhex(compact)


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON fixture file as a dictionary."""
    resolved = resolve_repo_path(path)
    return json.loads(resolved.read_text(encoding="utf-8"))


def sorted_prefix_block_paths() -> list[Path]:
    """Return prefix block fixture paths in deterministic chain order."""
    return sorted((DATA_DIR / "blocks-prefix").glob("*.hex"))


def block_hashes() -> dict[str, str]:
    """Load named scenario block hashes from fixture metadata."""
    return load_json(DATA_DIR / "meta" / "block-hashes.json")


def prefix_hashes() -> set[str]:
    """Load the set of prefix block hashes from fixture metadata."""
    return set(load_json(DATA_DIR / "meta" / "prefix-hashes.json"))
