"""Color & style helpers.

Decisions:
- Internal status key uses 'todo'; header shows 'TO DO'.
- Truecolor preferred; falls back to 256-color cube if unsupported.
- Disables automatically when not a TTY unless FORCE_COLOR=1.
- Honors NO_COLOR for complete disable.
- Supports palette overrides via environment or project .env file.
"""
from __future__ import annotations
import os, sys
from pathlib import Path

_FORCE = os.environ.get("FORCE_COLOR", "").lower() in {"1", "true", "yes", "on"}
_NO_COLOR = os.environ.get("NO_COLOR") is not None
_ENABLE = (_FORCE or sys.stdout.isatty()) and not _NO_COLOR
_COLORTERM = os.environ.get("COLORTERM", "").lower()
_USE_TRUECOLOR = _ENABLE and any(tok in _COLORTERM for tok in ("truecolor", "24bit"))

def _code(part: str) -> str:
    """Generate ANSI escape code for a given style part."""
    return f"\033[{part}m" if _ENABLE else ''

def _hex_to_rgb(hex_code: str) -> tuple[int,int,int]:
    """Convert a hex color code to an RGB tuple."""
    h = hex_code.lstrip('#')
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def _fg_truecolor(r: int, g: int, b: int) -> str:
    """Generate ANSI escape code for truecolor foreground."""
    return f"\033[38;2;{r};{g};{b}m"

def _fg_256(r: int, g: int, b: int) -> str:
    """Approximate RGB to xterm 256-color cube."""
    def to_6(x: int) -> int:
        return int(round(x / 255 * 5))
    r6, g6, b6 = to_6(r), to_6(g), to_6(b)
    idx = 16 + 36 * r6 + 6 * g6 + b6
    return f"\033[38;5;{idx}m"

def _from_hex(hex_code: str) -> str:
    """Convert a hex color code to an ANSI escape sequence."""
    if not _ENABLE:
        return ''
    r, g, b = _hex_to_rgb(hex_code)
    if _USE_TRUECOLOR:
        return _fg_truecolor(r, g, b)
    return _fg_256(r, g, b)

RESET = _code('0')
BOLD = _code('1')
DIM = _code('2')
UNDERLINE = _code('4')

# Default palette (user provided originals)
HEX_PRIMARY_DEFAULT = '#476EAE'
HEX_TODO_DEFAULT = '#48B3AF'
HEX_DONE_DEFAULT = '#A7E399'
HEX_INPROGRESS_DEFAULT = '#F6FF99'

# Load overrides from environment and optional .env file
_ENV_OVERRIDES: dict[str, str] = {}
_env_path = Path(__file__).resolve().parent.parent / '.env'
if _env_path.exists():
    try:
        for line in _env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k,v = line.split('=',1)
            k = k.strip()
            v = v.strip()
            if k in { 'KANBAN_PRIMARY','KANBAN_TODO','KANBAN_INPROGRESS','KANBAN_DONE' }:
                h = v.lstrip('#')
                if len(h) == 6 and all(c in '0123456789abcdefABCDEF' for c in h):
                    _ENV_OVERRIDES[k] = '#' + h
    except Exception:
        pass  # ignore .env parsing errors silently

# Resolve final hex values (priority: real env var > .env override > default)
HEX_PRIMARY = str(os.environ.get('KANBAN_PRIMARY') or _ENV_OVERRIDES.get('KANBAN_PRIMARY', HEX_PRIMARY_DEFAULT))
HEX_TODO = str(os.environ.get('KANBAN_TODO') or _ENV_OVERRIDES.get('KANBAN_TODO', HEX_TODO_DEFAULT))
HEX_INPROGRESS = str(os.environ.get('KANBAN_INPROGRESS') or _ENV_OVERRIDES.get('KANBAN_INPROGRESS', HEX_INPROGRESS_DEFAULT))
HEX_DONE = str(os.environ.get('KANBAN_DONE') or _ENV_OVERRIDES.get('KANBAN_DONE', HEX_DONE_DEFAULT))

# Generate ANSI sequences
PRIMARY = _from_hex(HEX_PRIMARY)
C_TODO = _from_hex(HEX_TODO)
C_DONE = _from_hex(HEX_DONE)
C_INPROGRESS = _from_hex(HEX_INPROGRESS)

STATUS_COLOR = {
    'todo': C_TODO,
    'in-progress': C_INPROGRESS,
    'done': C_DONE,
}

HEADER_COLOR = PRIMARY
ID_COLOR = PRIMARY + BOLD  # emphasize IDs with bold primary
EMPTY_COLOR = DIM + PRIMARY

def color(text: str, *styles: str) -> str:
    """Apply ANSI styles to a given text."""
    if not _ENABLE:
        return text
    return ''.join(styles) + text + RESET

__all__ = [
    'color','RESET','BOLD','DIM','UNDERLINE','STATUS_COLOR','HEADER_COLOR','ID_COLOR','EMPTY_COLOR',
    'HEX_PRIMARY','HEX_TODO','HEX_DONE','HEX_INPROGRESS','_ENABLE','_USE_TRUECOLOR','_FORCE'
]
