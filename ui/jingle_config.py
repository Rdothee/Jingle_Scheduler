"""
jingle_config.py  —  Jingle Library editor screen.

Lets the operator add / edit / delete jingle definitions (file path + offset),
reorder them, preview playback, and save back to jingles.json.
"""

import os
import threading
import customtkinter as ctk
from tkinter import messagebox, filedialog

try:
    from playsound import playsound
except ImportError:
    playsound = None

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
PURPLE       = "#8b5cf6"
PURPLE_HOVER = "#7c3aed"


class JingleConfigFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=CONTENT_BG, corner_radius=0)
        self.app = app
        self._selected = None   # JingleDef
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_topbar()
        self._build_toolbar()
        self._build_list()
        self._build_timeline()
        self._build_bottombar()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0, height=70)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        ctk.CTkLabel(bar, text="🎵  Jingle Library",
                     font=ctk.CTkFont("Arial", 18, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, padx=24, pady=20)

        self._dirty_label = ctk.CTkLabel(bar, text="",
                                         font=ctk.CTkFont("Arial", 12),
                                         text_color="#f59e0b")
        self._dirty_label.grid(row=0, column=1, padx=24)

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=52)
        tb.grid(row=1, column=0, sticky="ew")
        tb.grid_propagate(False)

        for text, color, hover, cmd in [
            ("＋  Add",    SUCCESS,  "#059669",    self._add),
            ("✏  Edit",   ACCENT,   ACCENT_HOVER, self._edit),
            ("🗑  Delete", DANGER,   DANGER_HOVER, self._delete),
            ("▲  Up",     "#374151","#4b5563",    self._move_up),
            ("▼  Down",   "#374151","#4b5563",    self._move_down),
            ("▶  Preview",PURPLE,   PURPLE_HOVER, self._preview),
        ]:
            ctk.CTkButton(tb, text=text, width=95, height=34,
                          fg_color=color, hover_color=hover,
                          font=ctk.CTkFont("Arial", 12),
                          command=cmd).pack(side="left", padx=4, pady=9)

    def _build_list(self):
        # Column header
        hdr = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=0, height=36)
        hdr.grid(row=2, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(2, weight=1)

        for col, (txt, w) in enumerate([("#", 40), ("Offset", 80), ("Name / File", 0), ("Path", 0)]):
            ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont("Arial", 11, "bold"),
                         text_color=TEXT_MUTED, width=w if w else None,
                         anchor="w").grid(row=0, column=col,
                                          padx=(20 if col == 0 else 8, 4),
                                          pady=6, sticky="w")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=CONTENT_BG, corner_radius=0)
        self._scroll.grid(row=3, column=0, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)
        self._scroll.grid_columnconfigure(2, weight=1)
        self._refresh_list()

    def _build_timeline(self):
        """Horizontal visual showing when each jingle fires relative to match start."""
        self._timeline_frame = ctk.CTkFrame(self, fg_color=SIDEBAR_BG,
                                            corner_radius=0, height=70)
        self._timeline_frame.grid(row=4, column=0, sticky="ew")
        self._timeline_frame.grid_propagate(False)
        self._timeline_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self._timeline_frame, text="OFFSET TIMELINE  (relative to match start)",
                     font=ctk.CTkFont("Arial", 9, "bold"),
                     text_color=TEXT_MUTED).grid(row=0, column=0, padx=16, pady=(8, 2), sticky="w")

        self._timeline_canvas_frame = ctk.CTkFrame(self._timeline_frame,
                                                   fg_color="transparent")
        self._timeline_canvas_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        self._refresh_timeline()

    def _build_bottombar(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0, height=56)
        bar.grid(row=5, column=0, sticky="ew")
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

        for i, jd in enumerate(self.app.jingle_manager.get_all()):
            bg = CARD_BG if i % 2 == 0 else "#1e2d40"
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6, height=44)
            row.grid(row=i, column=0, columnspan=4, sticky="ew", padx=12, pady=2)
            row.grid_propagate(False)
            row.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(row, text=str(i + 1), width=40,
                         font=ctk.CTkFont("Arial", 12),
                         text_color=TEXT_MUTED, anchor="w").grid(
                row=0, column=0, padx=(16, 4), sticky="w")

            sign = "+" if jd.offset >= 0 else ""
            ctk.CTkLabel(row, text=f"{sign}{jd.offset}m", width=70,
                         font=ctk.CTkFont("Courier", 12),
                         text_color=ACCENT, anchor="w").grid(
                row=0, column=1, padx=8, sticky="w")

            ctk.CTkLabel(row, text=jd.display_name,
                         font=ctk.CTkFont("Arial", 12),
                         text_color=TEXT_PRIMARY, anchor="w").grid(
                row=0, column=2, padx=8, sticky="w")

            exists = os.path.isfile(jd.path)
            path_color = TEXT_MUTED if exists else DANGER
            path_text  = (os.path.basename(jd.path) if exists
                          else f"⚠ NOT FOUND: {os.path.basename(jd.path)}")
            ctk.CTkLabel(row, text=path_text, font=ctk.CTkFont("Arial", 10),
                         text_color=path_color, anchor="w").grid(
                row=0, column=3, padx=(0, 16), sticky="w")

            for widget in (row, *row.winfo_children()):
                widget.bind("<Button-1>", lambda e, j=jd, r=row: self._select(j, r))

            self._row_frames[jd.uid] = row

        self._dirty_label.configure(
            text="● Unsaved changes" if self.app.jingle_manager.is_dirty else "")
        self._refresh_timeline()

    def _refresh_timeline(self):
        for w in self._timeline_canvas_frame.winfo_children():
            w.destroy()

        jingles = self.app.jingle_manager.get_all()
        if not jingles:
            ctk.CTkLabel(self._timeline_canvas_frame, text="No jingles defined.",
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont("Arial", 11)).pack()
            return

        offsets = [j.offset for j in jingles]
        min_off, max_off = min(offsets), max(offsets)
        span = max(max_off - min_off, 1)

        colors = ["#3b82f6","#10b981","#f59e0b","#8b5cf6","#ef4444",
                  "#06b6d4","#84cc16","#f97316"]

        for i, jd in enumerate(jingles):
            pct = (jd.offset - min_off) / span
            label = f"{jd.display_name}  ({jd.offset_label})"
            color = colors[i % len(colors)]
            dot = ctk.CTkLabel(self._timeline_canvas_frame,
                               text="●", text_color=color,
                               font=ctk.CTkFont("Arial", 11))
            dot.place(relx=pct * 0.88 + 0.02, rely=0.3)
            ctk.CTkLabel(self._timeline_canvas_frame,
                         text=label, text_color=color,
                         font=ctk.CTkFont("Arial", 9)).place(
                relx=pct * 0.88 + 0.02, rely=0.6)

    def _select(self, jd, row_frame):
        for frame in self._row_frames.values():
            frame.configure(border_width=0)
        self._selected = jd
        row_frame.configure(border_width=2, border_color=ACCENT)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _add(self):
        _JingleDialog(self, self.app, mode="add")

    def _edit(self):
        if not self._selected:
            messagebox.showinfo("Edit", "Please select a jingle first.")
            return
        _JingleDialog(self, self.app, mode="edit", jd=self._selected)

    def _delete(self):
        if not self._selected:
            messagebox.showinfo("Delete", "Please select a jingle first.")
            return
        if messagebox.askyesno("Delete", f"Delete '{self._selected.display_name}'?"):
            self.app.jingle_manager.delete(self._selected)
            self._selected = None
            self._refresh_list()

    def _move_up(self):
        if not self._selected:
            return
        self.app.jingle_manager.move_up(self._selected)
        self._refresh_list()

    def _move_down(self):
        if not self._selected:
            return
        self.app.jingle_manager.move_down(self._selected)
        self._refresh_list()

    def _preview(self):
        if not self._selected:
            messagebox.showinfo("Preview", "Please select a jingle first.")
            return
        if not os.path.isfile(self._selected.path):
            messagebox.showerror("File not found", f"Cannot find:\n{self._selected.path}")
            return
        if playsound is None:
            messagebox.showerror("playsound missing", "Install playsound to enable preview.")
            return
        path = self._selected.path
        threading.Thread(target=lambda: playsound(path), daemon=True).start()

    def _save(self):
        missing = self.app.jingle_manager.validate_paths()
        if missing:
            msg = "These jingle files were not found on disk:\n" + \
                  "\n".join(f"  • {j.display_name}" for j in missing) + \
                  "\n\nSave anyway?"
            if not messagebox.askyesno("Missing files", msg):
                return
        self.app.jingle_manager.save()
        self.app.rebuild()
        self._refresh_list()
        messagebox.showinfo("Saved", "Jingle library saved and scheduler reloaded.")

    def _discard(self):
        if self.app.jingle_manager.is_dirty:
            if not messagebox.askyesno("Discard", "Discard all unsaved changes?"):
                return
        self.app.jingle_manager.load()
        self._selected = None
        self._refresh_list()

    def on_show(self):
        self._selected = None
        self._refresh_list()


# ── Add / Edit dialog ─────────────────────────────────────────────────────────

class _JingleDialog(ctk.CTkToplevel):
    def __init__(self, parent_screen, app, mode="add", jd=None):
        super().__init__(parent_screen)
        self.app = app
        self.parent_screen = parent_screen
        self.mode = mode
        self.jd = jd

        self.title("Add Jingle" if mode == "add" else "Edit Jingle")
        self.geometry("520x320")
        self.resizable(False, False)
        self.configure(fg_color=CONTENT_BG)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 24, "pady": 6}

        ctk.CTkLabel(self, text="File Path",
                     text_color=TEXT_MUTED, font=ctk.CTkFont("Arial", 12)).pack(anchor="w", **pad)

        path_row = ctk.CTkFrame(self, fg_color="transparent")
        path_row.pack(fill="x", padx=24, pady=4)
        path_row.grid_columnconfigure(0, weight=1)

        self._path_entry = ctk.CTkEntry(path_row, height=36,
                                         placeholder_text="C:\\path\\to\\jingle.mp3")
        self._path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(path_row, text="📁", width=40, height=36,
                      fg_color="#374151", hover_color="#4b5563",
                      command=self._browse).grid(row=0, column=1)

        ctk.CTkLabel(self, text="Display Name (optional)",
                     text_color=TEXT_MUTED, font=ctk.CTkFont("Arial", 12)).pack(anchor="w", **pad)
        self._name_entry = ctk.CTkEntry(self, height=36,
                                         placeholder_text="e.g. Pre-game fanfare")
        self._name_entry.pack(fill="x", padx=24, pady=4)

        ctk.CTkLabel(self, text="Offset from match start (minutes, can be negative)",
                     text_color=TEXT_MUTED, font=ctk.CTkFont("Arial", 12)).pack(anchor="w", **pad)
        self._offset_entry = ctk.CTkEntry(self, height=36, width=120,
                                           placeholder_text="-5")
        self._offset_entry.pack(anchor="w", padx=24, pady=4)

        if self.jd:
            self._path_entry.insert(0, self.jd.path)
            self._name_entry.insert(0, self.jd.name)
            self._offset_entry.insert(0, str(self.jd.offset))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=14)
        ctk.CTkButton(btn_row, text="Cancel", width=100,
                      fg_color="#374151", hover_color="#4b5563",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Save", width=100,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._save).pack(side="left", padx=6)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Jingle File",
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg"), ("All files", "*.*")]
        )
        if path:
            self._path_entry.delete(0, "end")
            self._path_entry.insert(0, path)

    def _save(self):
        path   = self._path_entry.get().strip()
        name   = self._name_entry.get().strip()
        offset_str = self._offset_entry.get().strip()

        if not path:
            messagebox.showerror("Missing path", "Please provide a file path.")
            return
        try:
            offset = int(offset_str)
        except ValueError:
            messagebox.showerror("Invalid offset", "Offset must be a whole number.")
            return

        if self.mode == "add":
            self.app.jingle_manager.add(path, offset, name)
        else:
            self.app.jingle_manager.update(self.jd, path=path, offset=offset, name=name)

        self.parent_screen._refresh_list()
        self.destroy()
