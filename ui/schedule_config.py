"""
schedule_config.py  —  Match / Schedule editor screen.

Lets the operator add, edit and delete match start times.
Changes are held in memory until "Save" is clicked (dirty-state tracking).
"""

import datetime
import customtkinter as ctk
from tkinter import messagebox

SIDEBAR_BG   = "#111827"
CONTENT_BG   = "#1f2937"
CARD_BG      = "#253347"
ACCENT       = "#3b82f6"
ACCENT_HOVER = "#2563eb"
TEXT_PRIMARY = "#f9fafb"
TEXT_MUTED   = "#9ca3af"
DANGER       = "#ef4444"
DANGER_HOVER = "#dc2626"
SUCCESS      = "#10b981"


class ScheduleConfigFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=CONTENT_BG, corner_radius=0)
        self.app = app
        self._selected = None   # currently selected MatchEntry
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_topbar()
        self._build_toolbar()
        self._build_list()
        self._build_bottombar()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0, height=70)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="📅  Schedule Editor",
                     font=ctk.CTkFont("Arial", 18, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, padx=24, pady=20)

        self._dirty_label = ctk.CTkLabel(bar, text="",
                                         font=ctk.CTkFont("Arial", 12),
                                         text_color="#f59e0b")
        self._dirty_label.grid(row=0, column=2, padx=24)

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=52)
        tb.grid(row=1, column=0, sticky="ew")
        tb.grid_propagate(False)

        ctk.CTkButton(tb, text="＋  Add Match", width=130, height=34,
                      fg_color=SUCCESS, hover_color="#059669",
                      font=ctk.CTkFont("Arial", 13),
                      command=self._add_match).pack(side="left", padx=(16, 6), pady=9)

        ctk.CTkButton(tb, text="✏  Edit", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      font=ctk.CTkFont("Arial", 13),
                      command=self._edit_match).pack(side="left", padx=4, pady=9)

        ctk.CTkButton(tb, text="🗑  Delete", width=100, height=34,
                      fg_color=DANGER, hover_color=DANGER_HOVER,
                      font=ctk.CTkFont("Arial", 13),
                      command=self._delete_match).pack(side="left", padx=4, pady=9)

    def _build_list(self):
        # Header row
        hdr = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=0, height=36)
        hdr.grid(row=2, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(2, weight=1)
        for col, (txt, w) in enumerate([("#", 40), ("Date & Time", 200), ("Match Name", 0)]):
            kwargs = {"text": txt, "font": ctk.CTkFont("Arial", 11, "bold"),
                      "text_color": TEXT_MUTED, "anchor": "w"}
            if w:
                kwargs["width"] = w
            ctk.CTkLabel(hdr, **kwargs).grid(
                row=0, column=col, padx=(20 if col == 0 else 8, 4), pady=6, sticky="w")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=CONTENT_BG, corner_radius=0)
        self._scroll.grid(row=3, column=0, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)
        self._scroll.grid_columnconfigure(2, weight=1)
        self._refresh_list()

    def _build_bottombar(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0, height=56)
        bar.grid(row=4, column=0, sticky="ew")
        bar.grid_propagate(False)

        ctk.CTkButton(bar, text="💾  Save", width=110, height=36,
                      fg_color=SUCCESS, hover_color="#059669",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=self._save).pack(side="right", padx=16, pady=10)

        ctk.CTkButton(bar, text="↩  Discard", width=110, height=36,
                      fg_color="#374151", hover_color="#4b5563",
                      font=ctk.CTkFont("Arial", 13),
                      command=self._discard).pack(side="right", padx=4, pady=10)

    # ── List rendering ────────────────────────────────────────────────────────

    def _refresh_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._row_frames = {}

        matches = self.app.match_manager.get_sorted()
        for i, entry in enumerate(matches):
            bg = CARD_BG if i % 2 == 0 else "#1e2d40"
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6, height=40)
            row.grid(row=i, column=0, columnspan=3, sticky="ew", padx=12, pady=2)
            row.grid_propagate(False)
            row.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(row, text=str(i + 1), width=40,
                         font=ctk.CTkFont("Arial", 12), text_color=TEXT_MUTED,
                         anchor="w").grid(row=0, column=0, padx=(16, 4), pady=6, sticky="w")

            ctk.CTkLabel(row, text=entry.start_dt.strftime("%Y-%m-%d  %H:%M"),
                         width=200, font=ctk.CTkFont("Courier", 12),
                         text_color=TEXT_PRIMARY, anchor="w").grid(
                row=0, column=1, padx=8, pady=6, sticky="w")

            ctk.CTkLabel(row, text=entry.name or "—",
                         font=ctk.CTkFont("Arial", 12),
                         text_color=TEXT_PRIMARY if entry.name else TEXT_MUTED,
                         anchor="w").grid(row=0, column=2, padx=8, pady=6, sticky="w")

            # Click to select
            for widget in (row, *row.winfo_children()):
                widget.bind("<Button-1>", lambda e, en=entry, r=row: self._select(en, r))

            self._row_frames[entry.uid] = row

        self._dirty_label.configure(
            text="● Unsaved changes" if self.app.match_manager.is_dirty else "")

    def _select(self, entry, row_frame):
        # Reset previous selection
        for uid, frame in self._row_frames.items():
            frame.configure(border_width=0)
        self._selected = entry
        row_frame.configure(border_width=2, border_color=ACCENT)

    # ── CRUD operations ───────────────────────────────────────────────────────

    def _add_match(self):
        _MatchDialog(self, self.app, mode="add")

    def _edit_match(self):
        if not self._selected:
            messagebox.showinfo("Edit", "Please select a match first.")
            return
        _MatchDialog(self, self.app, mode="edit", entry=self._selected)

    def _delete_match(self):
        if not self._selected:
            messagebox.showinfo("Delete", "Please select a match first.")
            return
        if messagebox.askyesno("Delete match",
                               f"Delete match at {self._selected.start_dt.strftime('%Y-%m-%d %H:%M')}?"):
            self.app.match_manager.delete(self._selected)
            self._selected = None
            self._refresh_list()

    def _save(self):
        overlaps = self.app.match_manager.overlapping_pairs(threshold_minutes=30)
        if overlaps:
            msg = "Warning: some matches are within 30 minutes of each other:\n"
            for a, b in overlaps:
                msg += f"  • {a.start_dt.strftime('%H:%M')} and {b.start_dt.strftime('%H:%M')}\n"
            msg += "\nSave anyway?"
            if not messagebox.askyesno("Overlap warning", msg):
                return
        self.app.match_manager.save()
        self.app.rebuild()
        self._refresh_list()
        messagebox.showinfo("Saved", "Schedule saved and scheduler reloaded.")

    def _discard(self):
        if self.app.match_manager.is_dirty:
            if not messagebox.askyesno("Discard", "Discard all unsaved changes?"):
                return
        self.app.match_manager.load()
        self._selected = None
        self._refresh_list()

    def on_show(self):
        self._selected = None
        self._refresh_list()


# ── Add / Edit dialog ─────────────────────────────────────────────────────────

class _MatchDialog(ctk.CTkToplevel):
    DT_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, parent_screen, app, mode="add", entry=None):
        super().__init__(parent_screen)
        self.app = app
        self.parent_screen = parent_screen
        self.mode = mode
        self.entry = entry

        self.title("Add Match" if mode == "add" else "Edit Match")
        self.geometry("440x440")
        self.resizable(False, False)
        self.configure(fg_color=CONTENT_BG)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 24, "pady": 8}

        ctk.CTkLabel(self, text="Date (YYYY-MM-DD)",
                     text_color=TEXT_MUTED, font=ctk.CTkFont("Arial", 12)).pack(anchor="w", **pad)
        self._date_entry = ctk.CTkEntry(self, width=360, height=36,
                                        placeholder_text="2024-05-10")
        self._date_entry.pack(**pad)

        ctk.CTkLabel(self, text="Time (HH:MM or HH:MM:SS)",
                     text_color=TEXT_MUTED, font=ctk.CTkFont("Arial", 12)).pack(anchor="w", **pad)
        self._time_entry = ctk.CTkEntry(self, width=360, height=36,
                                        placeholder_text="09:00:00")
        self._time_entry.pack(**pad)

        ctk.CTkLabel(self, text="Match Name (optional)",
                     text_color=TEXT_MUTED, font=ctk.CTkFont("Arial", 12)).pack(anchor="w", **pad)
        self._name_entry = ctk.CTkEntry(self, width=360, height=36,
                                        placeholder_text="Pool A — Court 1")
        self._name_entry.pack(**pad)

        if self.entry:
            self._date_entry.insert(0, self.entry.start_dt.strftime("%Y-%m-%d"))
            self._time_entry.insert(0, self.entry.start_dt.strftime("%H:%M:%S"))
            self._name_entry.insert(0, self.entry.name)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=16)
        ctk.CTkButton(btn_row, text="Cancel", width=100,
                      fg_color="#374151", hover_color="#4b5563",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Save", width=100,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._save).pack(side="left", padx=6)

    def _save(self):
        date_str = self._date_entry.get().strip()
        time_str = self._time_entry.get().strip()
        name     = self._name_entry.get().strip()

        # Normalise time
        if len(time_str) == 5:
            time_str += ":00"

        try:
            dt = datetime.datetime.strptime(f"{date_str} {time_str}", self.DT_FMT)
        except ValueError:
            messagebox.showerror("Invalid input",
                                 "Use YYYY-MM-DD for date and HH:MM or HH:MM:SS for time.")
            return

        if self.mode == "add":
            self.app.match_manager.add(dt, name)
        else:
            self.app.match_manager.update(self.entry, start_dt=dt, name=name)

        self.parent_screen._refresh_list()
        self.destroy()
