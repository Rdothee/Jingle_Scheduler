"""
match_manager.py  —  CRUD for scheduled matches (JSON storage).

JSON format  (Resources/schedule.json):
    {
        "matches": [
            {"start": "2024-05-09 13:24:00", "name": "Pool A"},
            ...
        ]
    }

Falls back to migrating the legacy Schedule.csv on first run.
"""

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

DT_FORMAT = "%Y-%m-%d %H:%M:%S"


def _next_id():
    _next_id.counter += 1
    return _next_id.counter
_next_id.counter = 0


@dataclass
class MatchEntry:
    start_dt: datetime
    name: str = ""
    uid: int = field(default_factory=_next_id)

    @property
    def display_label(self) -> str:
        return self.name if self.name else "Match"

    @property
    def datetime_str(self) -> str:
        return self.start_dt.strftime(DT_FORMAT)


class MatchManager:
    def __init__(self, json_path: str, legacy_csv_path: str = ""):
        self.json_path = json_path
        self.legacy_csv_path = legacy_csv_path
        self._entries: list[MatchEntry] = []
        self._dirty = False
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self):
        self._entries.clear()
        if os.path.exists(self.json_path):
            self._load_json()
        elif self.legacy_csv_path and os.path.exists(self.legacy_csv_path):
            self._migrate_from_csv()
            self.save()   # immediately persist migration
        self._dirty = False

    def _load_json(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("matches", []):
            try:
                dt = datetime.strptime(item["start"], DT_FORMAT)
                self._entries.append(MatchEntry(start_dt=dt, name=item.get("name", "")))
            except (ValueError, KeyError):
                pass

    def _migrate_from_csv(self):
        with open(self.legacy_csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)          # skip header
            for row in reader:
                if not row:
                    continue
                try:
                    dt = datetime.strptime(row[0].strip(), DT_FORMAT)
                    name = row[1].strip() if len(row) > 1 else ""
                    self._entries.append(MatchEntry(start_dt=dt, name=name))
                except ValueError:
                    pass

    def save(self):
        data = {
            "matches": [
                {"start": e.datetime_str, "name": e.name}
                for e in self._entries
            ]
        }
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self._dirty = False

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get_sorted(self) -> list[MatchEntry]:
        return sorted(self._entries, key=lambda e: e.start_dt)

    def add(self, start_dt: datetime, name: str = "") -> MatchEntry:
        entry = MatchEntry(start_dt=start_dt, name=name)
        self._entries.append(entry)
        self._dirty = True
        return entry

    def update(self, entry: MatchEntry, start_dt: datetime = None, name: str = None):
        if start_dt is not None:
            entry.start_dt = start_dt
        if name is not None:
            entry.name = name
        self._dirty = True

    def delete(self, entry: MatchEntry):
        self._entries = [e for e in self._entries if e.uid != entry.uid]
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def overlapping_pairs(self, threshold_minutes: int = 60) -> list[tuple]:
        sorted_list = self.get_sorted()
        return [
            (sorted_list[i], sorted_list[i + 1])
            for i in range(len(sorted_list) - 1)
            if (sorted_list[i + 1].start_dt - sorted_list[i].start_dt) < timedelta(minutes=threshold_minutes)
        ]
