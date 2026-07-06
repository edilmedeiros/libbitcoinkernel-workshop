"""Chainstate-backed block processing helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import pbk_compat as compat
from .callbacks import CallbackRecorder
from .io import block_hashes, prefix_hashes, resolve_repo_path, sorted_prefix_block_paths
from .objects import load_block


@dataclass
class ProcessedBlock:
    path: Path
    block_hash: str
    direct_result: str


@dataclass
class ScenarioResult:
    name: str
    tip: str | None
    processed: list[ProcessedBlock] = field(default_factory=list)
    callbacks: CallbackRecorder = field(default_factory=CallbackRecorder)
    notes: list[str] = field(default_factory=list)


def reset_kernel_datadir(path: str | Path) -> Path:
    datadir = resolve_repo_path(path)
    if datadir.exists():
        shutil.rmtree(datadir)
    datadir.mkdir(parents=True, exist_ok=True)
    return datadir


def open_chainstate(datadir: str | Path, recorder: CallbackRecorder | None = None):
    resolved = resolve_repo_path(datadir)
    resolved.mkdir(parents=True, exist_ok=True)
    return compat.make_chainman(resolved, recorder)


def process_paths(
    chainman: object,
    paths: Iterable[str | Path],
) -> list[ProcessedBlock]:
    processed: list[ProcessedBlock] = []
    for path in paths:
        loaded = load_block(path)
        try:
            result = compat.process_block(chainman, loaded.obj)
            direct_result = str(result)
        except Exception as exc:  # noqa: BLE001 - failed processing is demo data.
            direct_result = f"{type(exc).__name__}: {exc}"
        processed.append(
            ProcessedBlock(
                path=Path(path),
                block_hash=compat.block_hash(loaded.obj),
                direct_result=direct_result,
            )
        )
    return processed


def replay_prefix(chainman: object) -> list[ProcessedBlock]:
    return process_paths(chainman, sorted_prefix_block_paths())


def run_replay_main(datadir: str | Path, *, reset: bool = True) -> ScenarioResult:
    recorder = CallbackRecorder()
    if reset:
        reset_kernel_datadir(datadir)
    handle = open_chainstate(datadir, recorder)
    processed = replay_prefix(handle.chainman)
    processed.extend(
        process_paths(
            handle.chainman,
            [
                "data/blocks-main/102-fund-alice.hex",
                "data/blocks-main/103-alice-pays-bob.hex",
                "data/blocks-main/104-bob-pays-carol.hex",
            ],
        )
    )
    tip = compat.active_tip(handle.chainman)
    expected = block_hashes()["104"]
    notes = [f"expected_tip_104: {expected}"]
    return ScenarioResult("replay-main", tip, processed, recorder, notes)


def run_missing_prev(datadir: str | Path, *, reset: bool = True) -> ScenarioResult:
    recorder = CallbackRecorder()
    if reset:
        reset_kernel_datadir(datadir)
    handle = open_chainstate(datadir, recorder)
    processed = replay_prefix(handle.chainman)
    processed.extend(
        process_paths(
            handle.chainman,
            [
                "data/blocks-main/102-fund-alice.hex",
                "data/blocks-main/104-bob-pays-carol.hex",
            ],
        )
    )
    hashes = block_hashes()
    tip = compat.active_tip(handle.chainman)
    notes = [
        f"skipped_block_103: {hashes['103']}",
        f"attempted_block_104: {hashes['104']}",
        "lesson: parsing and context-free validity are not enough to connect a block",
    ]
    return ScenarioResult("missing-prev", tip, processed, recorder, notes)


def run_reorg(datadir: str | Path, *, reset: bool = True) -> ScenarioResult:
    recorder = CallbackRecorder()
    if reset:
        reset_kernel_datadir(datadir)
    handle = open_chainstate(datadir, recorder)
    processed = replay_prefix(handle.chainman)
    processed.extend(
        process_paths(
            handle.chainman,
            [
                "data/blocks-main/102-fund-alice.hex",
                "data/blocks-main/103-alice-pays-bob.hex",
                "data/blocks-main/104-bob-pays-carol.hex",
                "data/blocks-reorg/a/105a.hex",
                "data/blocks-reorg/a/106a.hex",
                "data/blocks-reorg/b/105b.hex",
                "data/blocks-reorg/b/106b.hex",
                "data/blocks-reorg/b/107b.hex",
            ],
        )
    )
    hashes = block_hashes()
    tip = compat.active_tip(handle.chainman)
    try:
        stale_height, stale_previous = compat.block_tree_entry(
            handle.chainman, hashes["106a"]
        )
        block_tree_note = (
            "stale_branch_a_entry: "
            f"height={stale_height} hash={hashes['106a']} previous={stale_previous}"
        )
    except Exception as exc:  # noqa: BLE001 - optional binding surface.
        block_tree_note = f"block_tree_inspection_unavailable: {type(exc).__name__}: {exc}"
    notes = [
        f"stale_branch_a_tip: {hashes['106a']}",
        f"expected_tip_107b: {hashes['107b']}",
        block_tree_note,
    ]
    return ScenarioResult("reorg", tip, processed, recorder, notes)


def scenario_lines(result: ScenarioResult) -> list[str]:
    lines = [f"scenario: {result.name}"]
    prefix = [item for item in result.processed if "blocks-prefix" in item.path.parts]
    scenario_blocks = [item for item in result.processed if item not in prefix]
    if prefix:
        lines.append(
            "processed_prefix: "
            f"count={len(prefix)} first={prefix[0].block_hash} last={prefix[-1].block_hash}"
        )
    lines.extend(
        f"processed: {item.path} hash={item.block_hash} result={item.direct_result}"
        for item in scenario_blocks
    )
    hidden_hashes = prefix_hashes()
    visible_events = [
        event
        for event in result.callbacks.events
        if event.block_hash not in hidden_hashes
    ]
    hidden_count = len(result.callbacks.events) - len(visible_events)
    if hidden_count:
        lines.append(f"callbacks_prefix_hidden: count={hidden_count}")
    for event in visible_events:
        line = f"callback: {event.kind} hash={event.block_hash}"
        if event.height is not None:
            line += f" height={event.height}"
        if event.detail:
            line += f" detail={event.detail}"
        lines.append(line)
    lines.extend(f"note: {note}" for note in result.notes)
    lines.append(f"active_tip: {result.tip or 'unavailable'}")
    return lines
