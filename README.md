# Terminal Kanban

A modernized terminal Kanban board with three columns: **To Do**, **In-Progress**, and **Done**. Manage tasks quickly using shorthand commands, colorized output, automatic cleanup of old completed tasks, and sequential IDs.

Naming decision: internal storage & commands use the key `todo` (no hyphen) for backward compatibility and simplicity, while the UI header is rendered as `TO DO` for readability.

## Current Features

- Global sequential task IDs (auto-assigned). IDs are renumbered compactly after cleanup of stale done tasks (> 1 week old).
- Columns: To Do, In-Progress (renamed from legacy Doing), Done.
- Add tasks:
  - Interactive: `add` (prompts for title)
  - Shorthand: `add <title words>`
- Move tasks by ID: `mv <id> <status>` where status aliases: `t` (todo), `ip` (in-progress), `d` (done)
- Remove tasks: `rm <id>` or `remove <id>` (or interactive `remove`)
- Multi-line word wrapping: long titles wrap; IDs remain aligned; no truncation.
- Colored, truecolor (24-bit) palette:
  - Primary / headers / IDs: #476EAE
  - To Do: #48B3AF
  - In-Progress: #F6FF99
  - Done: #A7E399 (plus completion marker ✓ YYYY-MM-DD)
- Automatic cleanup: done tasks older than one week are purged on each command cycle; remaining tasks are renumbered.
- Graceful exit on Ctrl-C or Ctrl-D (tasks saved, message printed).
- ANSI color auto-disables when stdout is not a TTY or if `NO_COLOR` env var is set.
- Dynamic layout: column widths automatically adapt to your current terminal width each time the board is redrawn (whenever you run a command or simply press Enter on an empty line after resizing the window).
- Full clear: the screen and scrollback buffer are wiped each redraw so prior board states are not retained in scroll history (uses ESC 3J / 2J).

## Planned / Optional Enhancements

These are ideas tracked but not yet implemented:

- Configurable column widths or max width.
- Theme/palette overrides & runtime toggling; force monochrome setting.
- Additional shorthand (e.g., `d <id>` to mark done directly).
- Export/archive of completed tasks prior to cleanup.
- Sorting customization (pinning / priority).
- Config file & data versioning for future migrations.
- Unit tests & mypy enforcement.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/terminal-kanban.git
   cd terminal-kanban
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

(Requires Python 3.11+ recommended; tested on Python 3.12.)

## Usage

Run the board:

```
python src/main.py
```

You will see the three columns side-by-side. Enter commands at the prompt.

### Command Reference

```
add                 # interactive add (prompts for title)
add <title...>      # shorthand add inline
move                # interactive move (prompts for id & status)
mv <id> <status>    # shorthand move; status aliases: t / ip / d
rm <id>             # remove task by id (shorthand)
remove <id>         # same as rm; or `remove` for interactive prompt
help                # show help (does not clear screen afterward)
exit                # save and exit
```

Status aliases: `t` -> todo, `ip` -> in-progress, `d` -> done.

### Colors / NO_COLOR

Set environment variable `NO_COLOR=1` to disable colors:

```
NO_COLOR=1 python src/main.py
```

Automatic detection disables colors if output is redirected (non-TTY).

## Data & Cleanup

Tasks are stored in `data/tasks.json`. Each task entry fields:

```
{
  "id": <int>,
  "title": <str>,
  "status": "todo" | "in-progress" | "done",
  "completion_date": <ISO timestamp or null>,
  "created_at": <ISO timestamp>
}
```

On each command cycle completed tasks older than 7 days are removed; remaining tasks are renumbered starting from 1 in creation order.

## File Structure

- `src/main.py` – entry point
- `src/cli.py` – command loop & parsing
- `src/board.py` – board model, display, ID management, wrapping
- `src/models.py` – dataclass `Task`
- `src/storage.py` – load/save & cleanup/renumber integration
- `src/theme.py` – color & style helpers (truecolor palette)
- `data/tasks.json` – persisted tasks
- `requirements.txt` – dependencies
- `pyproject.toml` – project configuration

## Contributing

Issues & PRs welcome. Please discuss major changes first.

## License

MIT License. See `LICENSE` (or add one if missing).
