# Tutorial Command Plan

Add a purely instructional `kernel-lab tutorial` command that walks students
through the workshop lessons one at a time. The command should explain the
current lesson and show the primitive command the student should run manually.
It must not run primitive commands on the student's behalf.

## Goals

- Keep this feature instructional only.
- Do not call or execute the existing primitive commands.
- Show the primitive command line the student should run next.
- Pretty-print tutorial pages by default using terminal formatting.
- Add `--plain` for plain tutorial text output.
- Store tutorial explainer text and tutorial state helpers in
  `kernel_lab/tutorial.py`.
- Persist tutorial position in `.kernel-lab.json`.
- Support the bare tutorial command:

```bash
kernel-lab tutorial
```

  This initializes tutorial state if needed and shows the current lesson.
- Support moving forward and backward with:

```bash
kernel-lab tutorial next
kernel-lab tutorial previous
```

- Support a bird's-eye view with:

```bash
kernel-lab tutorial overview
```

## Lessons

Tutorial title:

```text
Bitcoin Validation Without a Node
```

Lessons:

1. `01 Raw bytes -> block object`
2. `02 Raw bytes -> transaction object`
3. `03 Context-free validation: valid block`
4. `04 Context-free validation: mutated block`
5. `05 Parsing failure: truncated block`
6. `06 Explicit-context input verification: correct prevout`
7. `07 Explicit-context input verification: wrong amount`
8. `08 Explicit-context input verification: wrong script`
9. `09 Chainstate-backed validation: replay main chain`
10. `10 Missing previous block: structurally fine, unconnectable`
11. `11 Reorg: active chain vs block tree`

## Lesson Output Shape

Each lesson should print these sections, in this order:

1. What we are doing
2. What files are used
3. What concept to focus on
4. Which primitive command is being exercised
5. What to look for after the student runs it

Example shape:

```text
Bitcoin Validation Without a Node
Lesson 01: Raw bytes -> block object

What we are doing
...

Files used
...

Concept to focus on
...

Primitive command
kernel-lab parse-block data/blocks-main/102-fund-alice.hex

What to look for
...
```

The tutorial command should print only explanation and expected observations. It
should not run the primitive command, should not capture stdout, and should not
print live command output.

## Tutorial Formatting

Pretty-print only the workshop explainers. The existing primitive commands
should stay plain and boring:

- `parse-block`
- `parse-tx`
- `check-block`
- `verify-script`
- `replay-main`
- `missing-prev`
- `reorg`
- `walkthrough`

Use a terminal formatting library for tutorial pages. Prefer `rich` because it
provides panels, section headings, code blocks, and color while still degrading
well in normal terminals.

Add dependency:

```toml
dependencies = [
    "py-bitcoinkernel",
    "pytest>=8",
    "rich>=13",
]
```

Default tutorial rendering should feel like a structured manual page:

- Title panel for `Bitcoin Validation Without a Node`.
- Lesson number and title as a strong heading.
- Section headings for:
  - What we are doing
  - Files used
  - Concept to focus on
  - Primitive command
  - What to look for
- File paths and commands rendered in monospace.
- Minimal color only to aid scanning. Avoid decorative output that makes copying
  commands harder.

Add `--plain` to the tutorial command only:

```bash
kernel-lab tutorial --plain
kernel-lab tutorial overview --plain
kernel-lab tutorial next --plain
kernel-lab tutorial previous --plain
```

Plain mode should print deterministic text with no ANSI color, no box drawing,
and no dependency on terminal width. This is useful for tests, logs, and people
who prefer simple output.

Implementation suggestion:

- Keep lesson data as structured strings and lists.
- Add two renderers:
  - `render_lesson_rich(...)`
  - `render_lesson_plain(...)`
  - `render_overview_rich(...)`
  - `render_overview_plain(...)`
- CLI selects renderer based on `args.plain`.
- Tests should primarily assert against plain rendering.

## State File

Persist tutorial state in:

```text
.kernel-lab.json
```

Suggested schema:

```json
{
  "tutorial": {
    "lesson_index": 0
  }
}
```

Rules:

- If the state file is missing, `tutorial` initializes state to lesson 1 and
  shows lesson 1.
- If the state file is missing, `tutorial next` also initializes state to lesson
  1 and shows lesson 1. There is no previous current lesson to advance from.
- Once state exists, `tutorial` shows the current lesson without changing the
  lesson index.
- `tutorial next` increments the lesson until lesson 11, then stays at lesson 11
  and prints it again with a short note that this is the last lesson.
- `tutorial previous` decrements the lesson until lesson 1, then stays at lesson
  1 and prints it again with a short note that this is the first lesson.
- Invalid or malformed state should not crash the command. Fall back to the
  initial state and overwrite with valid state after a successful command.

## Module Structure

Add:

- `kernel_lab/tutorial.py`

Update:

- `kernel_lab/cli.py`
- tests
- `README-dev.md`

Remove or stop using:

- `kernel_lab/strings.py`

## `kernel_lab/tutorial.py`

Move the existing explainer text from `kernel_lab/strings.py` into this module.
This module should own both the static lesson text and the lightweight tutorial
state helpers.

Suggested structures:

```python
TUTORIAL_TITLE = "Bitcoin Validation Without a Node"

TUTORIAL_OVERVIEW = """
...
"""

TUTORIAL_LESSONS = [
    {
        "id": "01",
        "title": "Raw bytes -> block object",
        "what": "...",
        "files": ["data/blocks-main/102-fund-alice.hex"],
        "focus": "...",
        "command": "kernel-lab parse-block data/blocks-main/102-fund-alice.hex",
        "look_for": "...",
    },
    ...
]
```

Keep the text plain, stable, and workshop-oriented. The strings should explain
libbitcoinkernel boundaries rather than Python abstractions.

## Primitive Command Mapping

Each lesson maps to one existing primitive command:

1. `kernel-lab parse-block data/blocks-main/102-fund-alice.hex`
2. `kernel-lab parse-tx data/tx/103-alice-pays-bob.hex`
3. `kernel-lab check-block data/blocks-main/102-fund-alice.hex`
4. `kernel-lab check-block data/blocks-invalid/102-bad-merkle.hex`
5. `kernel-lab check-block data/blocks-invalid/102-truncated.hex`
6. `kernel-lab verify-script data/prevouts/103-input0-correct.json`
7. `kernel-lab verify-script data/prevouts/103-input0-wrong-amount.json`
8. `kernel-lab verify-script data/prevouts/103-input0-wrong-script.json`
9. `kernel-lab replay-main --kernel-datadir .kernel-lab/main`
10. `kernel-lab missing-prev --kernel-datadir .kernel-lab/missing-prev`
11. `kernel-lab reorg --kernel-datadir .kernel-lab/reorg`

For lesson commands that intentionally return nonzero status when used as raw
primitive commands, such as invalid block or failed script checks, the tutorial
text should prepare the student for that result. The tutorial command itself
should still return `0` because it is only printing instructions.

## No Primitive Command Execution

Do not invoke existing command functions and do not spawn subprocesses from the
tutorial command.

The tutorial command should only render static lesson text from
`kernel_lab/tutorial.py` plus state-derived lesson position. The student runs the
shown primitive command separately.

This matters pedagogically: the tutorial page tells the student what concept to
focus on, then the student explicitly executes the kernel-facing primitive
command and inspects the output.

## CLI Shape

Add a `tutorial` subcommand with an optional action argument:

```bash
kernel-lab tutorial
kernel-lab tutorial --plain
kernel-lab tutorial overview
kernel-lab tutorial overview --plain
kernel-lab tutorial next
kernel-lab tutorial next --plain
kernel-lab tutorial previous
kernel-lab tutorial previous --plain
```

Optional future-compatible arguments:

```bash
kernel-lab tutorial show
kernel-lab tutorial reset
kernel-lab tutorial lesson 07
```

Do not implement optional actions unless needed during coding. The required
forms are bare `tutorial`, `overview`, `next`, and `previous`.

## Determinism

For lessons 9-11, the displayed primitive commands should use deterministic
datadirs:

- `.kernel-lab/main`
- `.kernel-lab/missing-prev`
- `.kernel-lab/reorg`

The tutorial command itself should not create, reset, or inspect these datadirs.

The tutorial state file `.kernel-lab.json` should not affect chainstate output.
It only controls which lesson is shown.

## Tests

Add tests for:

- `overview` prints the tutorial title and all 11 lesson titles.
- `overview --plain` prints the same lesson list without ANSI color or panel
  characters.
- Bare `tutorial` initializes missing state to lesson 01 and prints lesson 01.
- Bare `tutorial --plain` initializes missing state to lesson 01 and prints a
  deterministic plain lesson page.
- Bare `tutorial` with existing state prints the current lesson without changing
  state.
- Missing state file plus `next` shows lesson 01 and writes state.
- `next` moves from lesson 01 to lesson 02.
- `previous` moves from lesson 02 back to lesson 01.
- `previous` at lesson 01 stays on lesson 01.
- `next` at lesson 11 stays on lesson 11.
- A lesson output includes all required sections:
  - What we are doing
  - Files used
  - Concept to focus on
  - Primitive command
  - What to look for
- Lesson 04, 05, 07, and 08 explain that the primitive command demonstrates an
  expected failure, but the tutorial page itself exits successfully.
- `tutorial next` and `tutorial previous` do not create `.kernel-lab/*`
  chainstate datadirs and do not invoke primitive command functions.
- `--plain` is accepted only for the `tutorial` command family, not for the
  primitive commands.

Use temporary directories for state-file tests. The implementation can accept an
internal state path argument in helper functions to make testing easy, while the
CLI uses `.kernel-lab.json`.

## README-dev.md Updates

Add commands:

```bash
uv run kernel-lab tutorial
uv run kernel-lab tutorial --plain
uv run kernel-lab tutorial overview
uv run kernel-lab tutorial overview --plain
uv run kernel-lab tutorial next
uv run kernel-lab tutorial previous
```

Explain:

- `.kernel-lab.json` stores only tutorial position.
- `.kernel-lab/*` stores disposable chainstate datadirs.
- The tutorial command prints explanations and the primitive command to run
  manually. It does not run that command.
- Tutorial output is pretty-printed by default. Use `--plain` for deterministic
  plain text.

## Verification

Run:

```bash
uv run pytest
uv run kernel-lab tutorial overview
uv run kernel-lab tutorial overview --plain
uv run kernel-lab tutorial
uv run kernel-lab tutorial --plain
uv run kernel-lab tutorial next
uv run kernel-lab tutorial next
uv run kernel-lab tutorial previous
```

Also spot-check that lesson 11 prints:

- the reorg primitive command
- guidance to look for block disconnect/connect callbacks
- guidance to look for active tip ending at `107b`
- guidance to look for the stale branch block-tree entry for branch A
