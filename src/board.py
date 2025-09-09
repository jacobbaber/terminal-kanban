"""Board logic: holds columns, ID management, task mutation, and rendering.

Internal status keys: "todo", "in-progress", "done".
User-facing header for "todo" is rendered as "TO DO" to improve legibility
while keeping storage key stable (decision: prefer unhyphenated internal key).
"""
from datetime import datetime
from typing import Dict, List, Optional, Iterable, Mapping, Any, Tuple
from models import Task
from theme import color, HEADER_COLOR, STATUS_COLOR, ID_COLOR, EMPTY_COLOR, BOLD
import re, shutil

STATUSES: Tuple[str, ...] = ("todo", "in-progress", "done")
HEADER_TITLES: Dict[str, str] = {"todo": "TO DO", "in-progress": "IN-PROGRESS", "done": "DONE"}
MIN_COL_WIDTH = 18
SEP = " | "
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

class Board:
    def __init__(self, tasks_dict: Optional[Mapping[str, Iterable[Mapping[str, Any]]]] = None):
        self.columns: Dict[str, List[Task]] = { 'todo': [], 'in-progress': [], 'done': [] }
        self._next_id: int = 1
        if tasks_dict:
            self._load_from_dict(tasks_dict)

    # -------------------- loading / migration --------------------
    def _load_from_dict(self, tasks_dict: Mapping[str, Iterable[Mapping[str, Any]]]) -> None:
        collected: List[Task] = []
        for status, tasks in tasks_dict.items():
            mapped_status = 'in-progress' if status == 'doing' else status  # legacy migration
            if mapped_status not in self.columns:
                continue
            for raw in tasks:
                raw_title = raw.get('title')
                if raw_title is None:
                    continue
                tid = raw.get('id')
                if isinstance(tid, int):
                    assigned_id = tid
                else:
                    assigned_id = self._next_id
                    self._next_id += 1
                task = Task(
                    id=assigned_id,
                    title=str(raw_title),
                    status=mapped_status,
                    completion_date=raw.get('completion_date'),
                    created_at=raw.get('created_at')
                )
                collected.append(task)
        if collected:
            self._next_id = max(t.id for t in collected) + 1
        for task in collected:
            self.columns[task.status].append(task)

    # -------------------- id management --------------------
    def _allocate_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def renumber_sequential(self) -> None:
        """Renumber tasks starting at 1 preserving creation order.
        Sort key: (created_at or empty string, old id).
        """
        all_tasks = self.all_tasks()
        all_tasks.sort(key=lambda t: (t.created_at or '', t.id))
        for new_id, task in enumerate(all_tasks, start=1):
            task.id = new_id
        self._next_id = len(all_tasks) + 1

    # -------------------- queries --------------------
    def all_tasks(self) -> List[Task]:
        return self.columns['todo'] + self.columns['in-progress'] + self.columns['done']

    # -------------------- task operations --------------------
    def add_task(self, task: Task) -> None:
        task.id = self._allocate_id()
        task.status = 'todo'
        if not task.created_at:
            task.created_at = datetime.now().isoformat()
        self.columns['todo'].append(task)

    def move_task(self, task_title: str, new_status: str) -> str:
        """Move by title (legacy path)."""
        for task in self.all_tasks():
            if task.title == task_title:
                return self._move_found_task(task, new_status, f'Task "{task_title}"')
        return f'Task "{task_title}" not found.'

    def move_task_by_index(self, current_status: str, task_number: int, new_status: str) -> str:
        if current_status not in self.columns:
            return f'Invalid current status: {current_status}'
        if new_status not in self.columns:
            return f'Invalid new status: {new_status}'
        idx = task_number - 1
        tasks_list = self.columns[current_status]
        if idx < 0 or idx >= len(tasks_list):
            return f'No task #{task_number} in {current_status}.'
        task = tasks_list[idx]
        return self._move_found_task(task, new_status, f'Task "{task.title}"')

    def move_task_by_id(self, task_id: int, new_status: str) -> str:
        if new_status not in self.columns:
            return f'Invalid status: {new_status}'
        for task in self.all_tasks():
            if task.id == task_id:
                return self._move_found_task(task, new_status, f'Task {task_id}')
        return f'Task id {task_id} not found.'

    def _move_found_task(self, task: Task, new_status: str, label: str) -> str:
        if new_status not in self.columns:
            return f'Invalid status: {new_status}'
        if task.status == new_status:
            return f'{label} already in {new_status}.'
        # mutate columns
        self.columns[task.status].remove(task)
        task.status = new_status
        if new_status == 'done' and not task.completion_date:
            task.completion_date = datetime.now().isoformat()
        self.columns[new_status].append(task)
        return f'{label} moved to "{new_status}".'

    def remove_task(self, task_title: str) -> str:
        for tasks in self.columns.values():
            for task in list(tasks):
                if task.title == task_title:
                    tasks.remove(task)
                    return f'Task "{task_title}" removed.'
        return f'Task "{task_title}" not found.'

    def remove_task_by_id(self, task_id: int) -> str:
        for tasks in self.columns.values():
            for task in list(tasks):
                if task.id == task_id:
                    tasks.remove(task)
                    return f'Task {task_id} removed.'
        return f'Task id {task_id} not found.'

    # -------------------- serialization --------------------
    def get_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = { 'todo': [], 'in-progress': [], 'done': [] }
        for status, tasks in self.columns.items():
            for task in tasks:
                data[status].append({
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'completion_date': task.completion_date,
                    'created_at': task.created_at
                })
        return data

    # -------------------- display --------------------
    def display(self) -> None:
        term_width = shutil.get_terminal_size((120, 30)).columns
        widths = self._compute_column_widths(term_width)
        wrapped = self._wrap_all_columns(widths)
        self._render(widths, wrapped)

    # ---- width calculation ----
    def _compute_column_widths(self, term_width: int) -> Dict[str, int]:
        sep_total = len(SEP) * (len(STATUSES) - 1)
        desired: Dict[str, int] = {}
        for status in STATUSES:
            longest = len(HEADER_TITLES[status])
            for t in self.columns[status]:
                pv, _, title_text, _, done_suffix, _ = self._task_segments(t)
                candidate = len(pv) + len(title_text) + len(done_suffix)
                if candidate > longest:
                    longest = candidate
            desired[status] = max(MIN_COL_WIDTH, longest)
        widths = {s: desired[s] for s in STATUSES}
        total = sum(widths.values()) + sep_total
        if total > term_width:
            target_space = max(term_width - sep_total, len(STATUSES) * MIN_COL_WIDTH)
            while sum(widths.values()) > target_space:
                widest = max(STATUSES, key=lambda s: widths[s])
                if widths[widest] <= MIN_COL_WIDTH:
                    break
                widths[widest] -= 1
        else:
            extra = term_width - (sum(widths.values()) + sep_total)
            i = 0
            while extra > 0:
                widths[STATUSES[i % len(STATUSES)]] += 1
                extra -= 1
                i += 1
        return widths

    # ---- wrapping ----
    def _wrap_all_columns(self, widths: Mapping[str, int]) -> Dict[str, List[str]]:
        wrapped: Dict[str, List[str]] = {}
        for status in STATUSES:
            if not self.columns[status]:
                wrapped[status] = [color('(empty)', EMPTY_COLOR)]
            else:
                acc: List[str] = []
                for t in self.columns[status]:
                    acc.extend(self._wrap_task(t, widths[status]))
                wrapped[status] = acc
        return wrapped

    def _task_segments(self, task: Task):
        prefix_visible = f"{task.id}. "
        prefix_colored = color(f"{task.id}.", ID_COLOR, BOLD) + ' '
        status_col = STATUS_COLOR.get(task.status, '')
        title_text = task.title if task.title else '<untitled>'
        done_suffix = ''
        done_suffix_colored = ''
        if task.status == 'done' and task.completion_date:
            day = task.completion_date.split('T')[0]
            done_suffix = f" (\u2713 {day})"
            done_suffix_colored = color(done_suffix, STATUS_COLOR['done'])
        return prefix_visible, prefix_colored, title_text, status_col, done_suffix, done_suffix_colored

    def _wrap_task(self, task: Task, col_width: int) -> List[str]:
        pv, pc, title_text, status_col, done_suffix, done_suffix_colored = self._task_segments(task)
        words = title_text.split()
        lines_raw: List[str] = []
        current = ''
        first = True
        prefix_space = len(pv)
        # separate limits kept for clarity; currently identical but could diverge
        limit_first = max(1, col_width - prefix_space)
        limit_other = max(1, col_width - prefix_space)
        for w in words:
            limit = limit_first if first else limit_other
            candidate = w if not current else current + ' ' + w
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    lines_raw.append(current)
                current = w
                first = False
        if current:
            lines_raw.append(current)
        # attempt to append done suffix to last line
        if done_suffix:
            last = lines_raw[-1] if lines_raw else ''
            limit = limit_first if len(lines_raw) == 1 else limit_other
            if len(last) + len(done_suffix) <= limit:
                lines_raw[-1] = last + done_suffix
            else:
                lines_raw.append(done_suffix.strip())
        colored: List[str] = []
        for idx, raw_line in enumerate(lines_raw):
            if idx == 0:
                if done_suffix and raw_line.endswith(done_suffix) and raw_line != done_suffix.strip():
                    base_part = raw_line[:-len(done_suffix)]
                    colored.append(pc + color(base_part, status_col) + done_suffix_colored)
                elif done_suffix and raw_line == done_suffix.strip():
                    colored.append(pc + done_suffix_colored)
                else:
                    colored.append(pc + color(raw_line, status_col))
            else:
                indent = ' ' * prefix_space
                if done_suffix and raw_line.endswith(done_suffix) and raw_line != done_suffix.strip():
                    base_part = raw_line[:-len(done_suffix)]
                    colored.append(indent + color(base_part, status_col) + done_suffix_colored)
                elif done_suffix and raw_line == done_suffix.strip():
                    colored.append(indent + done_suffix_colored)
                else:
                    colored.append(indent + color(raw_line, status_col))
        return colored if colored else [pc + color('<empty>', status_col)]

    # ---- rendering ----
    def _render(self, widths: Mapping[str, int], wrapped_lines: Mapping[str, List[str]]) -> None:
        rows = max(len(wrapped_lines[s]) for s in STATUSES)
        header_cells: List[str] = []
        for s in STATUSES:
            h = color(HEADER_TITLES[s], HEADER_COLOR, BOLD)
            pad = widths[s] - self._visible_len(h)
            if pad > 0:
                h += ' ' * pad
            header_cells.append(h)
        header_line = SEP.join(header_cells)
        sep_line = SEP.join(color('-' * widths[s], HEADER_COLOR) for s in STATUSES)
        print(header_line)
        print(sep_line)
        for r in range(rows):
            row_cells: List[str] = []
            for s in STATUSES:
                col_lines = wrapped_lines[s]
                if r < len(col_lines):
                    line = col_lines[r]
                    pad = widths[s] - self._visible_len(line)
                    if pad > 0:
                        line += ' ' * pad
                    row_cells.append(line)
                else:
                    row_cells.append(' ' * widths[s])
            print(SEP.join(row_cells))

    @staticmethod
    def _visible_len(s: str) -> int:
        return len(ANSI_RE.sub('', s))

    def __str__(self) -> str:
        return (f'Todo: {len(self.columns["todo"])} tasks, ' \
                f'In-Progress: {len(self.columns["in-progress"])} tasks, ' \
                f'Done: {len(self.columns["done"])} tasks')