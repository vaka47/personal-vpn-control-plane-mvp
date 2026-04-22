from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import empty_state


class JsonStore:
    """Small JSON store for the portfolio MVP.

    This is intentionally simple. In production this boundary should be
    replaced with PostgreSQL repositories.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(empty_state())

    def load(self) -> Dict[str, List[Dict[str, Any]]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: Dict[str, List[Dict[str, Any]]]) -> None:
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def find_one(self, collection: str, **where: Any) -> Optional[Dict[str, Any]]:
        state = self.load()
        for row in state[collection]:
            if all(row.get(key) == value for key, value in where.items()):
                return row
        return None

    def replace_one(self, collection: str, row_id: str, row: Dict[str, Any]) -> None:
        state = self.load()
        rows = state[collection]
        for index, existing in enumerate(rows):
            if existing["id"] == row_id:
                rows[index] = row
                self.save(state)
                return
        raise KeyError(f"{collection} row not found: {row_id}")

    def append(self, collection: str, row: Dict[str, Any]) -> None:
        state = self.load()
        state[collection].append(row)
        self.save(state)

