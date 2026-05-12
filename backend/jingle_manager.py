"""
jingle_manager.py  —  CRUD for jingle definitions (JSON storage).

JSON format  (Resources/jingles.json):
    {
        "jingles": [
            {"path": "C:\\...\\file.mp3", "offset": -5, "name": "Pre-game"},
            ...
        ]
    }

Falls back to migrating the legacy Jingles.csv on first run.
"""

import csv
import json
import os
from dataclasses import dataclass, field


def _next_id():
    _next_id.counter += 1
    return _next_id.counter
_next_id.counter = 0


@dataclass
class JingleDef:
    path: str
    offset: int          # minutes relative to match start (can be negative)
    name: str = ""
    uid: int = field(default_factory=_next_id)

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        return os.path.basename(self.path)

    @property
    def offset_label(self) -> str:
        sign = "+" if self.offset >= 0 else ""
        return f"{sign}{self.offset} min"


class JingleManager:
    def __init__(self, json_path: str, legacy_csv_path: str = ""):
        self.json_path = json_path
        self.legacy_csv_path = legacy_csv_path
        self._jingles: list[JingleDef] = []
        self._dirty = False
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self):
        self._jingles.clear()
        if os.path.exists(self.json_path):
            self._load_json()
        elif self.legacy_csv_path and os.path.exists(self.legacy_csv_path):
            self._migrate_from_csv()
            self.save()
        self._dirty = False

    def _load_json(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("jingles", []):
            try:
                self._jingles.append(JingleDef(
                    path=item["path"],
                    offset=int(item.get("offset", 0)),
                    name=item.get("name", ""),
                ))
            except (KeyError, ValueError):
                pass

    def _migrate_from_csv(self):
        with open(self.legacy_csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)   # skip header row (Jingle,offset)
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    self._jingles.append(JingleDef(
                        path=row[0].strip(),
                        offset=int(row[1].strip()),
                    ))
                except ValueError:
                    pass

    def save(self):
        data = {
            "jingles": [
                {"path": j.path, "offset": j.offset, "name": j.name}
                for j in self._jingles
            ]
        }
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self._dirty = False

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get_all(self) -> list[JingleDef]:
        return list(self._jingles)

    def add(self, path: str, offset: int, name: str = "") -> JingleDef:
        jd = JingleDef(path=path, offset=offset, name=name)
        self._jingles.append(jd)
        self._dirty = True
        return jd

    def update(self, jd: JingleDef, path: str = None, offset: int = None, name: str = None):
        if path is not None:
            jd.path = path
        if offset is not None:
            jd.offset = offset
        if name is not None:
            jd.name = name
        self._dirty = True

    def delete(self, jd: JingleDef):
        self._jingles = [j for j in self._jingles if j.uid != jd.uid]
        self._dirty = True

    def move_up(self, jd: JingleDef):
        idx = next((i for i, j in enumerate(self._jingles) if j.uid == jd.uid), None)
        if idx and idx > 0:
            self._jingles[idx - 1], self._jingles[idx] = self._jingles[idx], self._jingles[idx - 1]
            self._dirty = True

    def move_down(self, jd: JingleDef):
        idx = next((i for i, j in enumerate(self._jingles) if j.uid == jd.uid), None)
        if idx is not None and idx < len(self._jingles) - 1:
            self._jingles[idx], self._jingles[idx + 1] = self._jingles[idx + 1], self._jingles[idx]
            self._dirty = True

    def validate_paths(self) -> list[JingleDef]:
        """Return jingles whose file path does not exist on disk."""
        return [j for j in self._jingles if not os.path.isfile(j.path)]

    @property
    def is_dirty(self) -> bool:
        return self._dirty
