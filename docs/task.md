# Jingle Scheduler UI — Task Tracker

> **Status as of 2026-05-12:** Phases 1-5 done. Phase 6 polish complete; only
> end-to-end verification remains.

## Phase 1 — Backend Refactor
- `[x]` Create `backend/__init__.py`
- `[x]` Create `backend/scheduler_engine.py` (pause/resume, state tracking, callbacks)
- `[x]` Create `backend/match_manager.py` (CRUD for schedule, JSON storage + CSV migration)
- `[x]` Create `backend/jingle_manager.py` (CRUD for jingles, JSON storage + CSV migration)
- `[x]` Add `status` field to `Jingle.py`
- `[x]` Add optional `name` field to `Match.py`

## Phase 2 — App Shell
- `[x]` Create `ui/__init__.py`
- `[x]` Create `ui/app.py` (root CTk window, sidebar navigation)

## Phase 3 — Dashboard
- `[x]` Create `ui/dashboard.py` (live clock, schedule table, play/pause, now-playing bar)

## Phase 4 — Jingle Config
- `[x]` Create `ui/jingle_config.py` (file browse, offset spinner, preview, reorder)

## Phase 5 — Schedule Config
- `[x]` Create `ui/schedule_config.py` (date picker, CRUD, save/discard)

## Phase 6 — Entry Point & Polish
- `[x]` Modify `Main.py` to launch GUI
- `[x]` Colour-coded jingle states (PENDING / PLAYING / PLAYED / SKIPPED)
- `[x]` Pulse animation on PLAYING badge
- `[x]` Unsaved-changes indicator on both config screens
- `[x]` Auto-scroll dashboard to active/upcoming match
- `[x]` Refresh `Resources/Schedule.csv` with current-year demo dates
- `[x]` End-to-end smoke verification: App instantiates, all 3 screens render, navigation works, rebuild works, pause/resume works, past-time jingles correctly marked SKIPPED instead of firing (manual interactive verification still recommended)
- `[ ]` **Audio backend**: `playsound 1.3.0` is currently installed and broken on Windows ("Error 259: The driver cannot recognize the specified command parameter"). Downgrade to `playsound==1.2.2` or switch backend before shipping.
- `[ ]` Decide fate of legacy `Mp3Scheduler.py` (unused — see Decisions §6 in `implementation_plan.md`)
