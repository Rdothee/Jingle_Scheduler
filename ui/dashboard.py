"""
dashboard.py  —  Live schedule overview screen.

Shows all matches for today + upcoming days, with per-jingle status badges,
a play/pause button, live clock, and a "now playing" bar at the bottom.
"""

import datetime
import os
import customtkinter as ctk

# ── Colour palette (mirrors app.py) ───────────────────────────────────────────
SIDEBAR_BG   = "#111827"
CONTENT_BG   = "#1f2937"
CARD_BG      = "#253347"
CARD_BORDER  = "#374151"
ACCENT       = "#3b82f6"
TEXT_PRIMARY = "#f9fafb"
TEXT_MUTED   = "#9ca3af"

STATUS_COLORS = {
    "PENDING": ("#374151", "#93c5fd"),   # (bg, fg)
    "PLAYING": ("#065f46", "#6ee7b7"),
    "PLAYED":  ("#1f2937", "#4b5563"),
    "SKIPPED": ("#78350f", "#fcd34d"),
}


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=CONTENT_BG, corner_radius=0)
        self.app = app
        self._pulse_state = True      # for PLAYING animation
        self._build_ui()
        self._start_pulse()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_schedule_list()
        self._build_nowplaying_bar()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0, height=70)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(bar, text="Live Dashboard",
                     font=ctk.CTkFont("Arial", 18, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, padx=24, pady=20)

        # Play / Pause
        self._play_btn = ctk.CTkButton(
            bar, text="⏸  Pause", width=120, height=36,
            fg_color=ACCENT, hover_color="#2563eb",
            font=ctk.CTkFont("Arial", 13, "bold"),
            command=self._toggle_play,
        )
        self._play_btn.grid(row=0, column=1, padx=8)

        # Reload
        ctk.CTkButton(
            bar, text="⟳  Reload", width=100, height=36,
            fg_color="#374151", hover_color="#4b5563",
            font=ctk.CTkFont("Arial", 13),
            command=self._reload,
        ).grid(row=0, column=2, padx=4)

        # Live clock (right-aligned)
        self._clock_label = ctk.CTkLabel(
            bar, text="", font=ctk.CTkFont("Arial", 20, "bold"),
            text_color=ACCENT
        )
        self._clock_label.grid(row=0, column=4, padx=24)
        self._update_clock()

    def _build_schedule_list(self):
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=CONTENT_BG, corner_radius=0
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)
        self.refresh()

    def _build_nowplaying_bar(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0, height=52)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="NOW PLAYING",
                     font=ctk.CTkFont("Arial", 10, "bold"),
                     text_color=TEXT_MUTED).grid(row=0, column=0, padx=16, pady=16)
        self._nowplaying_label = ctk.CTkLabel(
            bar, text="—", font=ctk.CTkFont("Arial", 13),
            text_color="#6ee7b7", anchor="w"
        )
        self._nowplaying_label.grid(row=0, column=1, padx=8, sticky="w")

    # ── Refresh / build match cards ────────────────────────────────────────────

    def refresh(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        matches = self.app.match_manager.get_sorted()
        if not matches:
            ctk.CTkLabel(self._scroll, text="No matches scheduled.",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont("Arial", 14)).pack(pady=40)
            return

        now = datetime.datetime.now()
        found_current = False

        for i, match in enumerate(matches):
            jobs = self.app.match_jobs.get(match.uid, [])
            is_current = any(j.status.value == "PLAYING" for j in jobs)
            is_past    = all(j.status.value in ("PLAYED", "SKIPPED") for j in jobs) and jobs
            is_upcoming = not is_current and not is_past

            self._build_match_card(match, jobs, i, is_current)

        # Update now-playing bar
        current_job = self.app.engine.current_job
        if current_job:
            name = getattr(current_job, "jingle_name", os.path.basename(current_job.path))
            self._nowplaying_label.configure(text=f"🔊  {name}")
        else:
            self._nowplaying_label.configure(text="—")

    def _build_match_card(self, match, jobs, index, is_current):
        now = datetime.datetime.now()
        is_past = all(j.status.value in ("PLAYED", "SKIPPED") for j in jobs) and jobs
        is_active = any(j.status.value == "PLAYING" for j in jobs)

        border_color = "#3b82f6" if is_active else ("#374151" if not is_past else "#1f2937")
        card = ctk.CTkFrame(
            self._scroll, fg_color=CARD_BG if not is_past else "#1a2233",
            corner_radius=10, border_width=2, border_color=border_color
        )
        card.grid(row=index, column=0, sticky="ew", padx=20, pady=6)
        card.grid_columnconfigure(1, weight=1)

        # Match header icon
        if is_active:
            icon = "▶"
        elif is_past:
            icon = "✓"
        else:
            icon = "⏳"

        icon_color = "#6ee7b7" if is_active else ("#4b5563" if is_past else TEXT_MUTED)

        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont("Arial", 18, "bold"),
                     text_color=icon_color, width=36).grid(
            row=0, column=0, padx=(16, 4), pady=14)

        # Match time + name
        label = match.display_label
        time_str = match.start_dt.strftime("%Y-%m-%d  %H:%M")
        header_text = f"{time_str}   —   {label}"
        ctk.CTkLabel(card, text=header_text,
                     font=ctk.CTkFont("Arial", 14, "bold"),
                     text_color=TEXT_PRIMARY if not is_past else TEXT_MUTED,
                     anchor="w").grid(row=0, column=1, sticky="w", pady=14)

        if not jobs:
            ctk.CTkLabel(card, text="No jingles defined",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont("Arial", 11)).grid(
                row=1, column=0, columnspan=3, padx=56, pady=(0, 10), sticky="w")
            return

        # Jingle rows
        for j_idx, job in enumerate(jobs):
            self._build_jingle_row(card, job, j_idx + 1, len(jobs))

    def _build_jingle_row(self, card, job, row_num, total):
        fire_str = job.scheduled_dt.strftime("%H:%M:%S")
        name     = getattr(job, "jingle_name", os.path.basename(job.path))
        status   = job.status.value if hasattr(job.status, "value") else str(job.status)
        bg, fg   = STATUS_COLORS.get(status, STATUS_COLORS["PENDING"])

        row_frame = ctk.CTkFrame(card, fg_color="transparent")
        row_frame.grid(row=row_num, column=0, columnspan=3, sticky="ew",
                       padx=(52, 16), pady=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Connector line
        connector = "└─" if row_num == total else "├─"
        ctk.CTkLabel(row_frame, text=connector, text_color="#4b5563",
                     font=ctk.CTkFont("Courier", 11), width=24).grid(
            row=0, column=0, sticky="w")

        # Time
        ctk.CTkLabel(row_frame, text=fire_str,
                     font=ctk.CTkFont("Courier", 12),
                     text_color=TEXT_MUTED, width=70).grid(
            row=0, column=1, sticky="w", padx=(4, 12))

        # Name
        ctk.CTkLabel(row_frame, text=name,
                     font=ctk.CTkFont("Arial", 12),
                     text_color=TEXT_PRIMARY if status != "PLAYED" else TEXT_MUTED,
                     anchor="w").grid(row=0, column=2, sticky="w")

        # Status badge
        badge = ctk.CTkLabel(
            row_frame, text=f"  {status}  ",
            font=ctk.CTkFont("Arial", 10, "bold"),
            fg_color=bg, text_color=fg, corner_radius=6
        )
        badge.grid(row=0, column=3, padx=(12, 0), pady=3)

        # Store PLAYING badges for pulse animation
        if status == "PLAYING":
            self._playing_badges = getattr(self, "_playing_badges", [])
            self._playing_badges.append(badge)

    # ── Controls ──────────────────────────────────────────────────────────────

    def _toggle_play(self):
        if self.app.engine.is_paused:
            self.app.engine.resume()
            self._play_btn.configure(text="⏸  Pause", fg_color=ACCENT)
        else:
            self.app.engine.pause()
            self._play_btn.configure(text="▶  Resume", fg_color="#374151")
        self.app._update_status_label()

    def _reload(self):
        self.app.rebuild()
        if not self.app.engine.is_paused:
            self._play_btn.configure(text="⏸  Pause", fg_color=ACCENT)

    # ── Clock & pulse ─────────────────────────────────────────────────────────

    def tick(self):
        """Called every second by the engine's on_tick callback."""
        self._update_clock()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        if hasattr(self, "_clock_label"):
            self._clock_label.configure(text=now)

    def _start_pulse(self):
        """Animate PLAYING status badges by toggling colours every 600 ms."""
        self._pulse_state = not getattr(self, "_pulse_state", True)
        badges = getattr(self, "_playing_badges", [])
        for badge in badges:
            try:
                if self._pulse_state:
                    badge.configure(fg_color="#065f46", text_color="#6ee7b7")
                else:
                    badge.configure(fg_color="#047857", text_color="#a7f3d0")
            except Exception:
                pass
        self._playing_badges = [b for b in badges if b.winfo_exists()]
        self.after(600, self._start_pulse)

    def on_show(self):
        self.refresh()
        if self.app.engine.is_paused:
            self._play_btn.configure(text="▶  Resume", fg_color="#374151")
        else:
            self._play_btn.configure(text="⏸  Pause", fg_color=ACCENT)
