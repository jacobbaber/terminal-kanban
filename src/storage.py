"""Persistence helpers (load/save/cleanup) for the Kanban board.

Internal status key uses "todo" (no hyphen). User interface renders
header as "TO DO" (design decision for readability without changing
stored key / backward compatibility).
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

TASKS_FILE = Path(__file__).parent.parent / 'data' / 'tasks.json'

TasksDict = Dict[str, List[Dict[str, Any]]]
TaskEntry = Dict[str, Any]

class Storage:
    @staticmethod
    def load_tasks() -> TasksDict:
        """Load tasks JSON from disk, performing legacy key migration.

        Returns a dict with keys: todo, in-progress, done.
        Missing file -> empty structure.
        """
        if not TASKS_FILE.exists():
            return {"todo": [], "in-progress": [], "done": []}
        with open(TASKS_FILE, 'r') as f:
            data = json.load(f)
        # migrate key 'doing' -> 'in-progress'
        if 'doing' in data and 'in-progress' not in data:
            data['in-progress'] = data.pop('doing')
        for key in ['todo', 'in-progress', 'done']:
            data.setdefault(key, [])
        return data  # type: ignore[return-value]

    @staticmethod
    def save_tasks(tasks_dict: TasksDict) -> None:
        """Persist tasks to disk (pretty-printed)."""
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks_dict, f, indent=4)

    @staticmethod
    def clean_done_tasks(tasks_dict: TasksDict) -> TasksDict:
        """Remove done tasks older than one week; renumber remaining tasks.

        A Board instance is reconstructed to leverage its renumber logic.
        Returns the refreshed tasks dict suitable for saving.
        """
        now = datetime.now()
        tasks_dict['done'] = [task for task in tasks_dict['done'] if not _is_old(task, now)]
        from board import Board  # local import to avoid cycle
        board = Board(tasks_dict)
        board.renumber_sequential()
        return board.get_tasks()

def _is_old(task: TaskEntry, now: datetime) -> bool:
    """Return True if a task's completion_date is > 1 week before 'now'."""
    date_str = task.get('completion_date')
    if not date_str:
        return False
    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        return False
    return (now - dt) > timedelta(weeks=1)