"""Data models for the terminal Kanban application.

Currently only exposes the Task dataclass. The internal status key is
"todo" (no hyphen) for persistence stability; user-facing header renders
as "TO DO". This decision keeps JSON keys simple and backward compatible.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Task:
    """A single Kanban task.

    Fields:
        id: Sequential integer id (renumbered compactly after cleanup).
        title: Short, single-line title (no separate description stored).
        status: One of: "todo", "in-progress", "done".
        completion_date: ISO timestamp when moved to done (None otherwise).
        created_at: ISO timestamp when task was originally created.
    """
    id: int
    title: str
    status: str = "todo"
    completion_date: Optional[str] = None
    created_at: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"Task(id={self.id}, title={self.title}, status={self.status})"