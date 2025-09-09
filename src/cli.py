"""Command-line interface loop for the Kanban board.

Internal status key is "todo" (no hyphen) while user-facing header reads
"TO DO" for clarity. This preserves storage compatibility.
"""
import os
from typing import Optional  # Added for Python <3.10 Optional typing
from models import Task
from storage import Storage
from board import Board

# --- terminal control helpers ---
# We aggressively clear: ESC[3J (scrollback), ESC[H (home), ESC[2J (screen), ESC[H (home))
# Order (3J first) improves reliability in some terminals.
try:  # pragma: no cover
    import click  # type: ignore  # noqa: F401
    def _clear_screen() -> None:  # pragma: no cover
        print("\033[3J\033[H\033[2J\033[H", end="", flush=True)
except Exception:  # pragma: no cover
    def _clear_screen() -> None:  # fallback identical
        print("\033[3J\033[H\033[2J\033[H", end="", flush=True)


def _truthy_env(value: Optional[str], default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


def _enter_alt_screen() -> None:
    # Switch to alternate screen buffer
    print("\033[?1049h", end="", flush=True)


def _leave_alt_screen() -> None:
    # Return to normal screen buffer
    print("\033[?1049l", end="", flush=True)


STATUS_ALIASES = {
    't': 'todo',
    'todo': 'todo',
    'ip': 'in-progress',
    'in-progress': 'in-progress',
    'd': 'done',
    'done': 'done'
}


class CLI:
    def __init__(self, board: Board):
        self.board: Board = board
        # Alt screen default ON; disable with KANBAN_ALT_SCREEN=0 (or false/no/off)
        self.alt_screen: bool = _truthy_env(os.getenv("KANBAN_ALT_SCREEN"), True)

    def run(self) -> None:
        """Main REPL loop; board is always cleared/redrawn each cycle.

        Uses the terminal's alternate screen (if enabled) so prior board
        renders do not remain in scrollback history. Scrollback is also
        cleared each redraw (ESC[3J) for terminals lacking alt screen.
        """
        exit_message: Optional[str] = None
        if self.alt_screen:
            _enter_alt_screen()
        try:
            while True:
                _clear_screen()
                print("Kanban Board:")
                self.board.display()
                line = input("\n: ").strip()
                if not line:
                    continue
                lower = line.lower()
                if lower == 'help':
                    _clear_screen()
                    self._help()
                    input("\nPress Enter to return to the board...")
                    continue
                if lower == 'exit':
                    # Persist and break; message printed after leaving alt screen
                    tasks_dict = self.board.get_tasks()
                    tasks_dict = Storage.clean_done_tasks(tasks_dict)
                    Storage.save_tasks(tasks_dict)
                    exit_message = "Goodbye."
                    break
                self._handle_command(line)
                # persist after each command
                tasks_dict = self.board.get_tasks()
                tasks_dict = Storage.clean_done_tasks(tasks_dict)
                Storage.save_tasks(tasks_dict)
        except (KeyboardInterrupt, EOFError):
            tasks_dict = self.board.get_tasks()
            tasks_dict = Storage.clean_done_tasks(tasks_dict)
            Storage.save_tasks(tasks_dict)
            exit_message = "Interrupted. Goodbye."
        finally:
            if self.alt_screen:
                _leave_alt_screen()
            if exit_message:
                print(exit_message)

    # -------------------- command dispatch --------------------
    def _handle_command(self, line: str) -> None:
        tokens = line.split()
        if not tokens:
            return
        cmd = tokens[0].lower()
        if cmd == 'mv':
            self._cmd_mv(tokens)
        elif cmd == 'add':
            self._cmd_add(tokens)
        elif cmd == 'rm':
            self._cmd_rm(tokens)
        elif cmd == 'remove':
            if len(tokens) == 2 and tokens[1].isdigit():
                result = self.board.remove_task_by_id(int(tokens[1]))
                print(result)
            else:
                self._remove()
        elif cmd == 'move':
            self._move()
        else:
            # Refresh board immediately, then show warning
            _clear_screen()
            print("Kanban Board:")
            self.board.display()
            print("\nUnknown command. Type 'help' for instructions.")

    # ---- individual command helpers ----
    def _cmd_mv(self, tokens: list[str]) -> None:
        if len(tokens) != 3:
            print("Usage: mv <id> <status>; statuses: t/ip/d")
            return
        id_part, status_part = tokens[1], tokens[2].lower()
        if not id_part.isdigit():
            print("Invalid id.")
            return
        new_status = STATUS_ALIASES.get(status_part)
        if not new_status:
            print("Invalid status.")
            return
        result = self.board.move_task_by_id(int(id_part), new_status)
        # Suppress success messages; only show errors or no-op
        if not (result.startswith('Task') and 'moved' in result):
            print(result)

    def _cmd_add(self, tokens: list[str]) -> None:
        if len(tokens) > 1:  # inline shorthand
            title = ' '.join(tokens[1:]).strip()
            if not title:
                print("Title required.")
                return
            self.board.add_task(Task(id=0, title=title))
        else:
            self._add()

    def _cmd_rm(self, tokens: list[str]) -> None:
        if len(tokens) != 2:
            print("Usage: rm <id>")
            return
        raw_id = tokens[1].rstrip('.')
        if not raw_id.isdigit():
            print("Invalid id.")
            return
        result = self.board.remove_task_by_id(int(raw_id))
        print(result)

    # -------------------- user-interactive flows --------------------
    def _help(self) -> None:
        print("Commands:")
        print("  add                 Add a new task (prompts for title)")
        print("  add <title...>      Shorthand add with inline title (e.g., add write report)")
        print("  move                Move a task (interactive prompts)")
        print("  mv <id> <status>    Shorthand move; status aliases: t (todo), ip (in-progress), d (done)")
        print("  rm <id>             Shorthand remove by id (e.g., rm 2)")
        print("  remove              Remove a task by id (prompts or 'remove <id>')")
        print("  help                Show this help (press Enter to return)")
        print("  exit                Save and exit")

    def _add(self) -> None:
        title = input("Enter task title: ").strip()
        if not title:
            print("Title required.")
            return
        self.board.add_task(Task(id=0, title=title))

    def _move(self) -> None:
        tid_raw = input("Enter task id: ").strip()
        if not tid_raw.isdigit():
            print("Invalid id.")
            return
        tid = int(tid_raw)
        target = input("Enter new status (todo/in-progress/done or t/ip/d): ").strip().lower()
        new_status = STATUS_ALIASES.get(target)
        if not new_status:
            print("Invalid status.")
            return
        result = self.board.move_task_by_id(tid, new_status)
        if not (result.startswith('Task') and 'moved' in result):
            print(result)

    def _move_shorthand(self) -> None:  # legacy helper
        line = input("Enter shorthand (e.g. 'mv 3 d'): ").strip().lower()
        parts = line.split()
        if parts and parts[0] == 'mv':
            parts = parts[1:]
        if len(parts) != 2:
            print("Format: mv <id> <status>")
            return
        id_part, status_part = parts
        if not id_part.isdigit():
            print("Invalid id.")
            return
        tid = int(id_part)
        new_status = STATUS_ALIASES.get(status_part)
        if not new_status:
            print("Invalid status.")
            return
        result = self.board.move_task_by_id(tid, new_status)
        if not (result.startswith('Task') and 'moved' in result):
            print(result)

    def _remove(self) -> None:
        tid_raw = input("Enter task id to remove: ").strip()
        if not tid_raw.isdigit():
            print("Invalid id.")
            return
        tid = int(tid_raw)
        result = self.board.remove_task_by_id(tid)
        print(result)

if __name__ == '__main__':  # pragma: no cover
    tasks = Storage.load_tasks()
    board = Board(tasks)
    CLI(board).run()