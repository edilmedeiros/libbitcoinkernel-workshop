import json
from pathlib import Path

import pytest

from kernel_lab.cli import build_parser
from kernel_lab import tutorial


def test_overview_plain_lists_all_lessons():
    text = tutorial.render_overview_plain()
    assert tutorial.TUTORIAL_TITLE in text
    for lesson in tutorial.TUTORIAL_LESSONS:
        assert f"{lesson.lesson_id}  {lesson.title}" in text


def test_bare_tutorial_initializes_state_and_prints_lesson_01(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"
    assert tutorial.run_tutorial("show", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 01: Raw bytes -> block object" in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 0}}


def test_bare_tutorial_with_existing_state_does_not_advance(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"
    state_path.write_text('{"tutorial": {"lesson_index": 3}}\n')

    assert tutorial.run_tutorial("show", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 04: Context-free validation: mutated block" in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 3}}


def test_next_from_missing_state_starts_at_lesson_01(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"

    assert tutorial.run_tutorial("next", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 01: Raw bytes -> block object" in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 0}}


def test_next_moves_from_lesson_01_to_lesson_02(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"
    tutorial.run_tutorial("show", plain=True, state_path=state_path)
    capsys.readouterr()

    assert tutorial.run_tutorial("next", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 02: Raw bytes -> transaction object" in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 1}}


def test_previous_moves_from_lesson_02_to_lesson_01(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"
    state_path.write_text('{"tutorial": {"lesson_index": 1}}\n')

    assert tutorial.run_tutorial("previous", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 01: Raw bytes -> block object" in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 0}}


def test_previous_at_first_lesson_stays_there(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"
    state_path.write_text('{"tutorial": {"lesson_index": 0}}\n')

    assert tutorial.run_tutorial("previous", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 01: Raw bytes -> block object" in out
    assert "This is the first lesson." in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 0}}


def test_next_at_last_lesson_stays_there(tmp_path, capsys):
    state_path = tmp_path / ".kernel-lab.json"
    state_path.write_text('{"tutorial": {"lesson_index": 10}}\n')

    assert tutorial.run_tutorial("next", plain=True, state_path=state_path) == 0

    out = capsys.readouterr().out
    assert "Lesson 11: Reorg: active chain vs block tree" in out
    assert "This is the last lesson." in out
    assert json.loads(state_path.read_text()) == {"tutorial": {"lesson_index": 10}}


def test_lesson_plain_output_has_required_sections():
    text = tutorial.render_lesson_plain(tutorial.TUTORIAL_LESSONS[0])
    for section in [
        "What we are doing",
        "Files used",
        "Concept to focus on",
        "Primitive command",
        "What to look for",
    ]:
        assert section in text


def test_failure_lessons_explain_expected_failure():
    for index in [3, 4, 6, 7]:
        lesson = tutorial.TUTORIAL_LESSONS[index]
        text = tutorial.render_lesson_plain(lesson).lower()
        assert "expected failure" in text


def test_tutorial_does_not_create_chainstate_datadir(tmp_path):
    state_path = tmp_path / ".kernel-lab.json"
    before = set(Path(".").glob(".kernel-lab/*"))

    tutorial.run_tutorial("next", plain=True, state_path=state_path)
    tutorial.run_tutorial("previous", plain=True, state_path=state_path)

    after = set(Path(".").glob(".kernel-lab/*"))
    assert after == before


def test_plain_option_is_scoped_to_tutorial_command():
    parser = build_parser()

    tutorial_args = parser.parse_args(["tutorial", "overview", "--plain"])
    assert tutorial_args.command == "tutorial"
    assert tutorial_args.action == "overview"
    assert tutorial_args.plain

    with pytest.raises(SystemExit):
        parser.parse_args(["parse-block", "--plain", "data/blocks-main/102-fund-alice.hex"])
