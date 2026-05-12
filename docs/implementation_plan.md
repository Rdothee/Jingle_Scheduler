# Jingle Scheduler — UI Implementation Plan

## Overview

The existing app is a headless Python script: it reads two CSVs (`Jingles.csv`, `Schedule.csv`), builds `Match` objects (each with timed `Jingle` objects), and plays MP3s via a background thread. The goal is to wrap this with a **desktop GUI** (Python `tkinter` + `ttk`) that gives operators a live dashboard, full schedule editing, and jingle configuration — all without touching the audio logic more than necessary.

---

## Decisions

> Resolved choices that drove the implementation. Update this section if the
> design changes.

1. **GUI toolkit** — **CustomTkinter** (drop-in tkinter replacement, dark-mode out of the box, no C deps). Imported in `ui/app.py`.
2. **Match name** — `Match` accepts an optional `name=""` (`Match.py:6`). The UI can surface it, but `Schedule.csv` does not yet carry a name column.
3. **Pause behaviour — soft pause** — `pause()` blocks *future* jingles only; a jingle that is already playing finishes naturally. The engine has **no `stop_playback()`**.
   **Catch-up rule:** any pending jingle whose scheduled time slipped more than **30 seconds** behind the wall clock is marked `SKIPPED` rather than fired late — this applies whether the engine is paused OR just got started/reloaded mid-day. Without this rule, launching the scheduler at 14:00 would dump every morning jingle out of the speakers at once (`scheduler_engine.py:_run_loop`).
4. **Per-match jingle sets** — out of scope for now. All matches share the same jingle list loaded from `Jingles.csv`.
5. **Storage** — **JSON** (`Resources/schedule.json`, `Resources/jingles.json`). The legacy `Schedule.csv` / `Jingles.csv` are migrated automatically on first run (see `match_manager._migrate_from_csv`, `jingle_manager._migrate_from_csv`) and then ignored — subsequent edits write JSON only.
6. **Legacy `Mp3Scheduler.py`** — no longer referenced by `Main.py` or any backend/UI module. Kept on disk as dead code pending an explicit delete; see `task.md`.

---

## Proposed Architecture

```
Jingle_Scheduler/
├── Main.py                  ← entry point, launches GUI
├── backend/
│   ├── __init__.py
│   ├── scheduler_engine.py  ← refactored Mp3Scheduler with pause/resume + state tracking
│   ├── match_manager.py     ← creates/edits/deletes matches, wraps Match + CsvReader
│   └── jingle_manager.py    ← CRUD for jingle definitions, wraps Jingle + CsvReader
├── ui/
│   ├── __init__.py
│   ├── app.py               ← root window, navigation sidebar/tabs
│   ├── dashboard.py         ← Screen 1: Live Schedule Dashboard
│   ├── schedule_config.py   ← Screen 2: Match / Schedule Editor
│   └── jingle_config.py     ← Screen 3: Jingle Library Editor
├── CsvReader.py             ← unchanged
├── Jingle.py                ← unchanged
├── Match.py                 ← unchanged
├── Mp3Scheduler.py          ← legacy, no longer imported (pending delete)
└── Resources/
    ├── Jingles.csv
    └── Schedule.csv
```

---

## Screen Designs

### Screen 1 — Live Dashboard (main screen)

**Purpose:** Real-time overview of the current day's schedule with play/pause control.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  🎵 Jingle Scheduler          [●] LIVE   14:32:07        │
│─────────────────────────────────────────────────────────│
│  [▶ PLAY / ⏸ PAUSE]   [⟳ Reload]   [⚙ Schedule] [🎵 Jingles] │
│─────────────────────────────────────────────────────────│
│  TODAY — Thursday 12 May 2026                           │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✅ 09:00 — Match  │ -5min  PianoSaloon1 (PLAYED) │   │
│  │                   │  +0    LetTheGamesBegin (PLAYED)│ │
│  │                   │ +45   5min-left       (PLAYED)│   │
│  │                   │ +50   Time-is-over    (PLAYED)│   │
│  ├─────────────────────────────────────────────────┤   │
│  │ ▶ 10:00 — Match  │ -5min  PianoSaloon1 (PLAYING)│   │  ← highlighted row
│  │                   │  +0    LetTheGamesBegin       │   │
│  │                   │ +45   5min-left               │   │
│  │                   │ +50   Time-is-over            │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ ⏳ 11:30 — Match  │ ...                           │   │  ← upcoming
│  │ ⏳ 12:30 — Match  │ ...                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  NOW PLAYING: 🔊 PianoSaloon1_Games-start-in-5-min.mp3  │
│  ████████████░░░░░░░░░░░░░░░░  [progress bar]           │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- **Status column per jingle**: `PLAYED` (grey), `PLAYING` (green pulse animation), `UPCOMING` (white), `SKIPPED` (past + paused, orange)
- **Auto-scroll**: the list auto-scrolls to keep the active match visible
- **Live clock** in the header, ticking every second
- **Play/Pause button**: calls `scheduler_engine.pause()` / `scheduler_engine.resume()`
- **Reload button**: re-reads CSVs and rebuilds schedule (useful after editing config)
- **Now Playing bar** at the bottom showing the currently active jingle filename

---

### Screen 2 — Schedule Config

**Purpose:** Add, edit, and delete match start times.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Dashboard          📅 Schedule Editor         │
│─────────────────────────────────────────────────────────│
│  [+ Add Match]   [✏ Edit Selected]   [🗑 Delete Selected] │
│─────────────────────────────────────────────────────────│
│  #   Date          Time      Name (optional)             │
│  ─────────────────────────────────────────────────       │
│  1   2024-05-09   13:24     Pool A                       │
│  2   2024-05-10   09:00     Pool B     ← selected        │
│  3   2024-05-10   10:00     Pool C                       │
│  ...                                                     │
│─────────────────────────────────────────────────────────│
│  [💾 Save]                       [↩ Discard Changes]     │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Inline date/time picker for editing
- Import from CSV / export to CSV buttons
- Validation: warns if two matches overlap (within 60 min of each other)
- Unsaved changes indicator (`*` in title bar)

---

### Screen 3 — Jingle Library Config

**Purpose:** Manage the list of jingles and their minute offsets relative to match start.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Dashboard          🎵 Jingle Library          │
│─────────────────────────────────────────────────────────│
│  [+ Add Jingle]   [✏ Edit Selected]   [🗑 Delete Selected]│
│  [▲ Move Up]      [▼ Move Down]                          │
│─────────────────────────────────────────────────────────│
│  Order  File Path                              Offset    │
│  ──────────────────────────────────────────────────────  │
│  1      .../PianoSaloon1_Games-start...mp3     -5 min   │
│  2      .../countryroads_LetTheGamesBegin.mp3   0 min   │  ← selected
│  3      .../SweetHomeAlabama_Only-5min.mp3     +45 min  │
│  4      .../Time-is-over-farmanimals.mp3       +50 min  │
│─────────────────────────────────────────────────────────│
│  [📁 Browse File]  Path: [________________________]      │
│  Offset (minutes): [____]   [▶ Preview]                  │
│─────────────────────────────────────────────────────────│
│  [💾 Save]                       [↩ Discard Changes]     │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- **File browser** button opens a system dialog to pick an `.mp3`
- **Offset spinner**: integer input, can be negative (before match) or positive (during/after)
- **Preview button**: plays the selected jingle immediately for testing
- **Reorder**: up/down arrows change playback order within a match
- **Offset visualizer**: small horizontal timeline showing when each jingle fires relative to match start

---

## Backend Changes Required

### 1. `backend/scheduler_engine.py` (refactor of `Mp3Scheduler.py`)

| Change | Reason |
|--------|--------|
| Add `paused` flag + `threading.Event` | Enable play/pause without killing the thread |
| Add jingle state tracking: `PENDING`, `PLAYING`, `PLAYED`, `SKIPPED` | Power the live dashboard status indicators |
| Fire a callback/event when a jingle state changes | Decouple UI updates from playback logic |
| Thread-safe job list (use `threading.Lock`) | Prevent race conditions during edits on the job list itself. *Note:* `_paused`/`_running`/`_current_job` are still read across threads without the lock — safe in CPython for these atomic flags but not a general guarantee. |

**Known behaviours to be aware of:**
- **History loss on reload.** `clear_jobs()` keeps only currently-`PLAYING` jobs; `PLAYED` and `SKIPPED` history is dropped. After a Dashboard *Reload*, the grey "PLAYED" indicators from earlier in the day will disappear.
- **Concurrent playback.** `_play_job` spawns a fresh daemon thread per fire. Two jingles scheduled at the same instant will overlap rather than queue.
- **`on_status_change` runs on the engine thread.** UI consumers must bridge back via `root.after(0, ...)` or a thread-safe queue — never touch tkinter widgets directly from the callback.

### 2. `backend/match_manager.py` (new)

- Load/save `Schedule.csv`
- CRUD for match entries
- Expose `get_matches_for_date(date)` for the dashboard filter

### 3. `backend/jingle_manager.py` (new)

- Load/save `Jingles.csv`
- CRUD for jingle definitions (path + offset)
- Validate that file paths exist on disk

### 4. `Match.py` / `Jingle.py` — minor additions

- `Jingle`: add `status` field (`PENDING` | `PLAYING` | `PLAYED` | `SKIPPED`)
- `Match`: add optional `name` field

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| GUI framework | **CustomTkinter** (`pip install customtkinter`) | Modern dark-mode widgets, drop-in tkinter replacement, no extra C deps |
| Date input | Plain `CTkEntry` with text validation | `tkcalendar` was considered but ultimately not added — keeps deps minimal. Revisit if operators ask for a popup calendar. |
| Audio | `playsound` (`pip install playsound==1.2.2`) | 1.3+ has [known issues on Windows](https://github.com/TaylorSMarks/playsound/issues/) |
| Config storage | JSON (`Resources/*.json`) | Migrated from the original CSV format on first run; see Decisions §5 |

---

## Proposed File Changes

### Backend Layer

#### [NEW] [scheduler_engine.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/backend/scheduler_engine.py)
Full rewrite of `Mp3Scheduler` with pause/resume, state callbacks, and thread safety.

#### [NEW] [match_manager.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/backend/match_manager.py)
CRUD wrapper around `Schedule.csv` + `Match` objects.

#### [NEW] [jingle_manager.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/backend/jingle_manager.py)
CRUD wrapper around `Jingles.csv` + `Jingle` objects.

---

### UI Layer

#### [NEW] [app.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/ui/app.py)
Root `CTk` window. Contains the sidebar navigation and hosts the three screen frames.

#### [NEW] [dashboard.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/ui/dashboard.py)
Live schedule view with auto-refreshing schedule table, play/pause, live clock, and now-playing bar.

#### [NEW] [schedule_config.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/ui/schedule_config.py)
Schedule editor with date/time pickers and save/discard logic.

#### [NEW] [jingle_config.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/ui/jingle_config.py)
Jingle library editor with file browser, offset input, reorder controls, and preview button.

---

### Entry Point

#### [MODIFY] [Main.py](file:///c:/Users/robbe/OneDrive/Documenten/Gspot/scheduler/Jingle_Scheduler/Main.py)
Replace `main.run()` headless loop with `ui.app.App().mainloop()`.

---

## Build Order (Phases)

| Phase | Status | Work | Deliverable |
|-------|--------|------|-------------|
| **1 — Backend Refactor** | ✅ done | `scheduler_engine.py`, `match_manager.py`, `jingle_manager.py` | Testable backend with no UI dependency |
| **2 — App Shell** | ✅ done | `app.py` with navigation, window chrome, sidebar | Empty-but-navigable window |
| **3 — Dashboard** | ✅ done | `dashboard.py` with live clock, schedule table, play/pause | Core operator screen |
| **4 — Jingle Config** | ✅ done | `jingle_config.py` with file browse, offset spinner, preview | Jingle editing working end-to-end |
| **5 — Schedule Config** | ✅ done | `schedule_config.py` with date picker, CRUD | Schedule editing working end-to-end |
| **6 — Polish** | ⏳ in progress | Animations, colour-coded states, auto-scroll, unsaved indicator | Final UX pass |

---

## Verification Plan

> ⚠️ **Prerequisite:** the shipped `Resources/Schedule.csv` only contains
> 2024 dates, so the dashboard will look empty out-of-the-box. Add at least
> one current-day match (via Schedule Config or by editing the CSV) before
> running these checks.

### Automated / Semi-automated
- Run `python Main.py` — window should open without errors
- Add a match 2 minutes in the future, press Play, verify jingle fires and status changes to `PLAYING` → `PLAYED`
- Press Pause during countdown, verify no jingle fires past the pause point (currently-playing jingle should still finish — this is the soft-pause decision)
- Edit a jingle path in config screen, save, reload dashboard — verify new path shows (note: `PLAYED`/`SKIPPED` history is cleared on reload)

### Manual
- Confirm that saving in Schedule Config writes correct rows to `Schedule.csv`
- Confirm that file-browse dialog filters to `.mp3` only
- Confirm the now-playing bar updates in real time
- Test with the existing `Resources/` CSVs to ensure no regressions
