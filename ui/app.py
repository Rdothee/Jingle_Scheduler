"""
app.py  —  Root CustomTkinter window.

Owns the shared backend objects (MatchManager, JingleManager, SchedulerEngine)
and orchestrates navigation between the three screens.
"""

import os
import sys
from datetime import timedelta

import customtkinter as ctk

# Add project root to path so backend imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.scheduler_engine import SchedulerEngine
from backend.match_manager import MatchManager
from backend.jingle_manager import JingleManager
from Jingle import Jingle

# ── Paths ──────────────────────────────────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
RESOURCES = os.path.join(_ROOT, "Resources")
SCHEDULE_JSON = os.path.join(RESOURCES, "schedule.json")
JINGLES_JSON  = os.path.join(RESOURCES, "jingles.json")
SCHEDULE_CSV  = os.path.join(RESOURCES, "Schedule.csv")
JINGLES_CSV   = os.path.join(RESOURCES, "Jingles.csv")

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SIDEBAR_BG  = "#111827"
CONTENT_BG  = "#1f2937"
ACCENT      = "#3b82f6"
ACCENT_HOVER= "#2563eb"
TEXT_PRIMARY= "#f9fafb"
TEXT_MUTED  = "#9ca3af"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎵 Jingle Scheduler")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.configure(fg_color=CONTENT_BG)

        # ── Shared backend ──────────────────────────────────────────────────
        self.match_manager  = MatchManager(SCHEDULE_JSON, SCHEDULE_CSV)
        self.jingle_manager = JingleManager(JINGLES_JSON, JINGLES_CSV)
        self.engine         = SchedulerEngine()
        # match_uid → list[ScheduledJob]  (populated by load_and_start)
        self.match_jobs: dict[int, list] = {}

        # Debounce token: cancel id of the pending refresh, if any
        self._pending_refresh_id = None

        # ── Layout ─────────────────────────────────────────────────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # ── Wire engine callbacks ───────────────────────────────────────────
        self.engine.on_status_change = lambda job: self.after(0, self._schedule_refresh)
        self.engine.on_tick          = lambda: self.after(0, self._on_tick)

        # ── Initial load ────────────────────────────────────────────────────
        self.load_and_start()
        self.show_screen("dashboard")

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self._sidebar = ctk.CTkFrame(self, width=220, fg_color=SIDEBAR_BG, corner_radius=0)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_rowconfigure(10, weight=1)

        # Logo
        ctk.CTkLabel(
            self._sidebar, text="🎵 Jingle", font=ctk.CTkFont("Arial", 22, "bold"),
            text_color=ACCENT
        ).grid(row=0, column=0, padx=24, pady=(28, 0), sticky="w")
        ctk.CTkLabel(
            self._sidebar, text="Scheduler", font=ctk.CTkFont("Arial", 22, "bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=1, column=0, padx=24, pady=(0, 24), sticky="w")

        ctk.CTkFrame(self._sidebar, height=1, fg_color="#374151").grid(
            row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        # Nav buttons
        self._nav_buttons = {}
        nav_items = [
            ("dashboard", "📊  Dashboard",   3),
            ("schedule",  "📅  Schedule",    4),
            ("jingles",   "🎵  Jingles",     5),
        ]
        for key, label, row in nav_items:
            btn = ctk.CTkButton(
                self._sidebar, text=label, anchor="w",
                font=ctk.CTkFont("Arial", 14),
                fg_color="transparent", text_color=TEXT_MUTED,
                hover_color="#1f2937", corner_radius=8, height=40,
                command=lambda k=key: self.show_screen(k),
            )
            btn.grid(row=row, column=0, padx=12, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        # Version / status at bottom
        self._status_label = ctk.CTkLabel(
            self._sidebar, text="⏹  Stopped",
            font=ctk.CTkFont("Arial", 12), text_color=TEXT_MUTED
        )
        self._status_label.grid(row=11, column=0, padx=24, pady=20, sticky="w")

    # ── Content area ───────────────────────────────────────────────────────────

    def _build_content_area(self):
        self._content = ctk.CTkFrame(self, fg_color=CONTENT_BG, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Import screens lazily to avoid circular deps
        from ui.dashboard       import DashboardFrame
        from ui.schedule_config import ScheduleConfigFrame
        from ui.jingle_config   import JingleConfigFrame

        self._screens = {
            "dashboard": DashboardFrame(self._content, self),
            "schedule":  ScheduleConfigFrame(self._content, self),
            "jingles":   JingleConfigFrame(self._content, self),
        }
        for s in self._screens.values():
            s.grid(row=0, column=0, sticky="nsew")

        self._current = None

    # ── Navigation ─────────────────────────────────────────────────────────────

    def show_screen(self, name: str):
        for key, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=ACCENT if key == name else "transparent",
                text_color=TEXT_PRIMARY if key == name else TEXT_MUTED,
            )
        screen = self._screens[name]
        screen.tkraise()
        if hasattr(screen, "on_show"):
            screen.on_show()
        self._current = name

    # ── Schedule orchestration ─────────────────────────────────────────────────

    def load_and_start(self):
        """Build ScheduledJob list from current config and (re)start engine."""
        self.match_jobs.clear()
        self.engine.clear_jobs()

        jingle_defs = self.jingle_manager.get_all()
        for match in self.match_manager.get_sorted():
            jobs = []
            for jd in jingle_defs:
                fire_dt  = match.start_dt + timedelta(minutes=jd.offset)
                j = Jingle(
                    path     = jd.path,
                    date     = fire_dt.strftime("%Y-%m-%d"),
                    time_str = fire_dt.strftime("%H:%M:%S"),
                )
                job = self.engine.add_job(j)
                # Attach display metadata directly on the job
                job.jingle_name = jd.display_name
                job.offset      = jd.offset
                job.match_uid   = match.uid
                jobs.append(job)
            self.match_jobs[match.uid] = jobs

        if not self.engine.is_running:
            self.engine.start()

    def rebuild(self):
        """Called after config changes: reload managers and restart engine."""
        was_paused = self.engine.is_paused
        self.engine.stop()

        self.engine = SchedulerEngine()
        self.engine.on_status_change = lambda job: self.after(0, self._schedule_refresh)
        self.engine.on_tick          = lambda: self.after(0, self._on_tick)

        self.match_manager.load()
        self.jingle_manager.load()
        self.load_and_start()

        if was_paused:
            self.engine.pause()

        # Refresh dashboard if visible
        if "dashboard" in self._screens:
            self._screens["dashboard"].refresh()
        self._update_status_label()

    # ── Engine callbacks (main thread) ─────────────────────────────────────────

    REFRESH_DEBOUNCE_MS = 120  # Coalesce rapid status changes into one refresh

    def _schedule_refresh(self):
        """Coalesce bursts of on_status_change calls into a single refresh.

        Several jobs flipping to SKIPPED on startup, or a rebuild touching many
        jobs at once, would otherwise trigger N back-to-back full refreshes —
        freezing the UI for a couple of seconds.
        """
        if self._pending_refresh_id is not None:
            try:
                self.after_cancel(self._pending_refresh_id)
            except Exception:
                pass
        self._pending_refresh_id = self.after(
            self.REFRESH_DEBOUNCE_MS, self._on_status_change)

    def _on_status_change(self):
        self._pending_refresh_id = None
        if self._current == "dashboard":
            self._screens["dashboard"].refresh()
        else:
            # Dashboard isn't visible — mark it dirty so on_show() rebuilds.
            dash = self._screens.get("dashboard")
            if dash is not None:
                dash._needs_refresh = True
        self._update_status_label()

    def _on_tick(self):
        if self._current == "dashboard":
            self._screens["dashboard"].tick()

    def _update_status_label(self):
        if self.engine.is_paused:
            self._status_label.configure(text="⏸  Paused",  text_color="#f59e0b")
        elif self.engine.is_running:
            self._status_label.configure(text="▶  Running", text_color="#10b981")
        else:
            self._status_label.configure(text="⏹  Stopped", text_color=TEXT_MUTED)

    def on_closing(self):
        self.engine.stop()
        self.destroy()
