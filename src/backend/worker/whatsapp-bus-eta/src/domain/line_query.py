from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Matches a bare line code ("483", "SN123") or one prefixed with a mode
# ("brt 22", "sppo 483") — anything else (a normal chat sentence) won't match,
# which is what keeps this from misfiring on regular conversation.
_LINE_RE = re.compile(r"^(?:(brt|sppo)\s+)?([A-Za-z0-9]{1,6})$", re.IGNORECASE)


@dataclass
class LineQuery:
    mode: str
    line_code: str


def parse_line_query(text: Optional[str]) -> Optional[LineQuery]:
    if not text:
        return None
    match = _LINE_RE.match(text.strip())
    if not match:
        return None
    mode = (match.group(1) or "sppo").lower()
    line_code = match.group(2).upper()
    return LineQuery(mode=mode, line_code=line_code)
