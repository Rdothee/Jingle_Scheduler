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
        self._loading_overlay = None  # CTkFrame shown while refresh runs
        self._spinner_step = 0
        # When False, on_show() skips refresh because the dashboard already
        # reflects current state. Flipped to True by app._schedule_refresh()
        # while the dashboard is hidden, and after rebuild().
        self._needs_refresh = False
        self._build_ui()
        self._start_pulse()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_schedule_list()
        self._build_nowplaying_bar()
        # All widgets exist → safe to populate
        self.refresh()

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
        # Whatever queued this rebuild, we're servicing it now.
        self._needs_refresh = False
        # Show overlay while we destroy/rebuild every card — the gap can be
        # 100-300 ms on a slow machine and looks like a hang otherwise.
        self._show_loading_overlay()

        for w in self._scroll.winfo_children():
            w.destroy()
        # Drop stale badge references — they belong to destroyed widgets
        self._playing_badges = []
        self._focus_card = None

        matches = self.app.match_manager.get_sorted()
        if not matches:
            ctk.CTkLabel(self._scroll, text="No matches scheduled.",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont("Arial", 14)).pack(pady=40)
            self._hide_loading_overlay()
            return

        now = datetime.datetime.now()
        # Focus rule: currently-playing match wins; else earliest match
        # whose start time is in the future
        focus_uid = None
        for m in matches:
            jobs = self.app.match_jobs.get(m.uid, [])
            if any(j.status.value == "PLAYING" for j in jobs):
                focus_uid = m.uid
                break
        if focus_uid is None:
            upcoming = [m for m in matches if m.start_dt >= now]
            if upcoming:
                focus_uid = upcoming[0].uid

        for i, match in enumerate(matches):
            jobs = self.app.match_jobs.get(match.uid, [])
            is_current = any(j.status.value == "PLAYING" for j in jobs)

            card = self._build_match_card(match, jobs, i, is_current)
            if match.uid == focus_uid:
                self._focus_card = card

        # Update now-playing bar
        current_job = self.app.engine.current_job
        if current_job:
            name = getattr(current_job, "jingle_name", os.path.basename(current_job.path))
            self._nowplaying_label.configure(text=f"🔊  {name}")
        else:
            self._nowplaying_label.configure(text="—")

        if self._focus_card is not None:
            self.after(50, self._scroll_to_focus)

        # Defer hide so the user can actually see it briefly on long refreshes
        self.after(80, self._hide_loading_overlay)

    # ── Loading overlay ───────────────────────────────────────────────────────

    def _show_loading_overlay(self):
        if self._loading_overlay is not None and self._loading_overlay.winfo_exists():
            return  # already visible
        # Place overlay on top of the scrollable list area (row 1)
        self._loading_overlay = ctk.CTkFrame(self, fg_color=CONTENT_BG)
        self._loading_overlay.grid(row=1, column=0, sticky="nsew")
        self._loading_overlay.grid_rowconfigure(0, weight=1)
        self._loading_overlay.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(self._loading_overlay, fg_color="transparent")
        inner.grid(row=0, column=0)

        self._spinner_label = ctk.CTkLabel(
            inner, text="⠋", font=ctk.CTkFont("Arial", 36, "bold"),
            text_color=ACCENT)
        self._spinner_label.pack(pady=(0, 8))
        ctk.CTkLabel(
            inner, text="Loading schedule…",
            font=ctk.CTkFont("Arial", 13),
            text_color=TEXT_MUTED).pack()

        self._loading_overlay.tkraise()
        self._spin()

    def _spin(self):
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        if self._loading_overlay is None or not self._loading_overlay.winfo_exists():
            return
        self._spinner_step = (self._spinner_step + 1) % len(frames)
        try:
            self._spinner_label.configure(text=frames[self._spinner_step])
        except Exception:
            return
        self.after(80, self._spin)

    def _hide_loading_overlay(self):
        if self._loading_overlay is not None and self._loading_overlay.winfo_exists():
            self._loading_overlay.destroy()
        self._loading_overlay = None

    def _scroll_to_focus(self):
        """Scroll the schedule list so the focused match sits near the top."""
        card = getattr(self, "_focus_card", None)
        if card is None or not card.winfo_exists():
            return
        try:
            canvas = self._scroll._parent_canvas
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            total_height = bbox[3]
            visible_height = canvas.winfo_height()
            if total_height <= visible_height:
                return  # Nothing to scroll
            target_y = max(0, card.winfo_y() - 80)
            fraction = min(1.0, target_y / max(total_height - visible_height, 1))
            canvas.yview_moveto(fraction)
        except (AttributeError, KeyError):
            pass

    def _build_match_card(self, match, jobs, index, is_current):
        is_past = all(j.status.value in ("PLAYED", "SKIPPED") for j in jobs) and jobs
        is_active = any(j.status.value == "PLAYING" for j in jobs)

        border_color = "#3b82f6" if is_active else ("#374151" if not is_past else "#1f2937")
        card = ctk.CTkFrame(
            self._scroll, fg_color=CARD_BG if not is_past else "#1a2233",
            corner_radius=10, border_width=2, border_color=border_color
        )
        card.grid(row=index, column=0, sticky="ew", padx=20, pady=6)
        # Columns: 0 icon | 1 connector | 2 time | 3 name (weight) | 4 badge
        card.grid_columnconfigure(3, weight=1)

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

        # Match time + name (spans the right side)
        label = match.display_label
        time_str = match.start_dt.strftime("%Y-%m-%d  %H:%M")
        header_text = f"{time_str}   —   {label}"
        ctk.CTkLabel(card, text=header_text,
                     font=ctk.CTkFont("Arial", 14, "bold"),
                     text_color=TEXT_PRIMARY if not is_past else TEXT_MUTED,
                     anchor="w").grid(row=0, column=1, columnspan=4,
                                       sticky="w", pady=14)

        if not jobs:
            ctk.CTkLabel(card, text="No jingles defined",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont("Arial", 11)).grid(
                row=1, column=1, columnspan=4, padx=(16, 16),
                pady=(0, 10), sticky="w")
            return card

        # Jingle rows — gridded directly onto the card (no inner frame)
        for j_idx, job in enumerate(jobs):
            self._build_jingle_row(card, job, j_idx + 1, len(jobs))

        return card

    def _build_jingle_row(self, card, job, row_num, total):
        fire_str = job.scheduled_dt.strftime("%H:%M:%S")
        name     = getattr(job, "jingle_name", os.path.basename(job.path))
        status   = job.status.value if hasattr(job.status, "value") else str(job.status)
        bg, fg   = STATUS_COLORS.get(status, STATUS_COLORS["PENDING"])

        # Connector line (column 1, padded so it sits ~52px from the card edge)
        connector = "└─" if row_num == total else "├─"
        ctk.CTkLabel(card, text=connector, text_color="#4b5563",
                     font=ctk.CTkFont("Courier", 11), width=24).grid(
            row=row_num, column=1, sticky="w", padx=(16, 0), pady=2)

        # Time
        ctk.CTkLabel(card, text=fire_str,
                     font=ctk.CTkFont("Courier", 12),
                     text_color=TEXT_MUTED, width=70).grid(
            row=row_num, column=2, sticky="w", padx=(4, 12), pady=2)

        # Name (fills remaining horizontal space)
        ctk.CTkLabel(card, text=name,
                     font=ctk.CTkFont("Arial", 12),
                     text_color=TEXT_PRIMARY if status != "PLAYED" else TEXT_MUTED,
                     anchor="w").grid(row=row_num, column=3, sticky="ew", pady=2)

        # Status badge
        badge = ctk.CTkLabel(
            card, text=f"  {status}  ",
            font=ctk.CTkFont("Arial", 10, "bold"),
            fg_color=bg, text_color=fg, corner_radius=6
        )
        badge.grid(row=row_num, column=4, padx=(12, 16), pady=3, sticky="e")

        # Store PLAYING badges for pulse animation
        if status == "PLAYING":
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
        # Skip the (expensive) full rebuild if nothing has changed since the
        # last refresh — large schedules can take 1-3 s to re-render.
        if self._needs_refresh:
            self._needs_refresh = False
            self.refresh()
        if self.app.engine.is_paused:
            self._play_btn.configure(text="▶  Resume", fg_color="#374151")
        else:
            self._play_btn.configure(text="⏸  Pause", fg_color=ACCENT)
