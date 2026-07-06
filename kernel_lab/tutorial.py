"""Instructional lesson text and state handling for `kernel-lab tutorial`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .io import REPO_ROOT
from .strings import (
    TutorialLesson,
    TUTORIAL_TITLE,
    TUTORIAL_OVERVIEW,
    TUTORIAL_HOWTO,
    TUTORIAL_LESSONS,
)

STATE_PATH = REPO_ROOT / ".kernel-lab.json"

def load_state(state_path: Path = STATE_PATH) -> dict[str, Any]:
    """Load tutorial state, returning an empty state for missing or bad JSON."""
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, Any], state_path: Path = STATE_PATH) -> None:
    """Persist tutorial state as deterministic JSON."""
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def current_lesson_index(state: dict[str, Any]) -> int | None:
    """Return the saved zero-based lesson index, or None if unavailable."""
    try:
        index = int(state["tutorial"]["lesson_index"])
    except (KeyError, TypeError, ValueError):
        return None
    if 0 <= index < len(TUTORIAL_LESSONS):
        return index
    return None


def update_lesson_index(action: str, state_path: Path = STATE_PATH) -> tuple[int, str | None]:
    """Apply a tutorial navigation action and persist the resulting lesson."""
    state = load_state(state_path)
    current = current_lesson_index(state)
    note = None

    if current is None:
        index = 0
    elif action == "next":
        if current == len(TUTORIAL_LESSONS) - 1:
            index = current
            note = "This is the last lesson."
        else:
            index = current + 1
    elif action == "previous":
        if current == 0:
            index = current
            note = "This is the first lesson."
        else:
            index = current - 1
    else:
        index = current

    state["tutorial"] = {"lesson_index": index}
    save_state(state, state_path)
    return index, note


def render_overview_plain() -> str:
    """Render the tutorial overview without colors or terminal styling."""
    lines = [TUTORIAL_TITLE, "", "Overview", TUTORIAL_OVERVIEW.strip(), "", "Lessons"]
    lines.extend(f"{lesson.lesson_id}  {lesson.title}" for lesson in TUTORIAL_LESSONS)
    return "\n".join(lines) + "\n"


def render_lesson_plain(lesson: TutorialLesson, note: str | None = None) -> str:
    """Render a tutorial lesson without colors or terminal styling."""
    lines = [
        TUTORIAL_TITLE,
        f"Lesson {lesson.lesson_id}: {lesson.title}",
    ]
    if note:
        lines.extend(["", f"Note: {note}"])
    lines.extend(
        [
            "",
            "What we are doing",
            lesson.what,
            "",
            "Files used",
            *lesson.files,
            "",
            "Concept to focus on",
            lesson.focus,
            "",
            "Primitive command",
            lesson.command,
            "",
            "What to look for",
            lesson.look_for,
        ]
    )
    return "\n".join(lines) + "\n"


def print_overview_rich(console: Console) -> None:
    """Pretty-print the tutorial overview using rich."""
    console.print()
    console.print(Rule(f"[bold cyan]{TUTORIAL_TITLE}[/bold cyan]", style="dim"))
    console.print()
    console.print(Markdown(TUTORIAL_OVERVIEW.strip()))
    console.print()
    console.print(Rule("[bold cyan]How to use this tutorial[/bold cyan]", style="dim"))
    console.print()
    console.print(Markdown(f"{TUTORIAL_HOWTO}"))
    console.print()
    table = Table(title="Lessons", show_header=True, header_style="bold")
    table.add_column("Lesson", style="cyan", no_wrap=True)
    table.add_column("Title")
    for lesson in TUTORIAL_LESSONS:
        table.add_row(lesson.lesson_id, lesson.title)
    console.print(table)


def print_lesson_rich(
    lesson: TutorialLesson,
    console: Console,
    note: str | None = None,
) -> None:
    """Pretty-print a tutorial lesson using rich."""
    title = f"Lesson {lesson.lesson_id}: {lesson.title}"
    console.print(Panel(title, style="bold cyan"))
    if note:
        console.print(f"[yellow]{note}[/yellow]")
    console.print()
    _print_section(console, "What we are doing", lesson.what)
    _print_section(console, "Files used", "".join(f"`{path}`\n\n" for path in lesson.files))
    _print_section(console, "Concept to focus on", lesson.focus)
    _print_section(console, "Primitive command", lesson.command)
    _print_section(console, "What to look for", lesson.look_for)
    _print_section(console, "Discussion questions", lesson.discussion)


def _print_section(console: Console, title: str, body: str) -> None:
    """Print one rich tutorial section."""
    console.print(Rule(f"[bold cyan]{title}[/bold cyan]", align="left"))
    console.print()
    console.print(Markdown(body))
    console.print()


def print_overview(*, plain: bool, console: Console | None = None) -> None:
    """Print the tutorial overview in rich or plain form."""
    if plain:
        print(render_overview_plain(), end="")
        return
    print_overview_rich(console or Console())


def print_lesson(
    lesson: TutorialLesson,
    *,
    plain: bool,
    note: str | None = None,
    console: Console | None = None,
) -> None:
    """Print one tutorial lesson in rich or plain form."""
    if plain:
        print(render_lesson_plain(lesson, note), end="")
        return
    print_lesson_rich(lesson, console or Console(), note)


def run_tutorial(
    action: str,
    *,
    plain: bool = False,
    state_path: Path = STATE_PATH,
) -> int:
    """Run the instructional tutorial command without executing primitives."""
    if action == "overview":
        print_overview(plain=plain)
        return 0

    index, note = update_lesson_index(action, state_path)
    print_lesson(TUTORIAL_LESSONS[index], plain=plain, note=note)
    return 0
