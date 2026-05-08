"""
Sims 4 Auto Save — backs up your save files on a timer so a crash never
costs you hours of gameplay.

Run this script while playing The Sims 4. It detects the game process and
copies your Saves folder to a rolling set of timestamped backups.

Usage:
    python autosave.py

Requirements:
    pip install psutil
"""

import os
import sys
import shutil
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


# ── platform defaults ────────────────────────────────────────────────────────

SIMS_PROCESS_NAMES = {"TS4_x64.exe", "TS4.exe", "The Sims 4"}

def default_saves_path() -> Path:
    base = Path.home() / "Documents" / "Electronic Arts" / "The Sims 4" / "Saves"
    return base

def default_backup_path() -> Path:
    return Path.home() / "Documents" / "Sims4_AutoBackups"


# ── helpers ──────────────────────────────────────────────────────────────────

def sims_is_running() -> bool:
    if not PSUTIL_AVAILABLE:
        return True  # assume running if we can't check
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] in SIMS_PROCESS_NAMES:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def perform_backup(saves_path: Path, backup_root: Path, keep: int) -> str:
    """Copy the Saves folder to a timestamped directory. Returns a status string."""
    if not saves_path.exists():
        return f"Saves folder not found: {saves_path}"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = backup_root / f"backup_{timestamp}"
    try:
        shutil.copytree(saves_path, dest)
    except Exception as exc:
        return f"Backup failed: {exc}"

    # prune old backups – keep the N most recent
    _prune_backups(backup_root, keep)
    return f"Backed up at {datetime.now().strftime('%I:%M %p')}"


def _prune_backups(backup_root: Path, keep: int):
    backups = sorted(backup_root.glob("backup_*"), key=lambda p: p.stat().st_mtime)
    while len(backups) > keep:
        old = backups.pop(0)
        shutil.rmtree(old, ignore_errors=True)


def human_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    else:
        return f"{int(seconds // 3600)}h ago"


# ── GUI ───────────────────────────────────────────────────────────────────────

PINK    = "#e91e8c"
PURPLE  = "#9b59b6"
DARK    = "#1a0a2e"
DARKER  = "#12071f"
WHITE   = "#f0e6ff"
GREEN   = "#2ecc71"
ORANGE  = "#e67e22"
RED     = "#e74c3c"
GREY    = "#6c5a8a"


class AutoSaveApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sims 4 Auto Save 💾")
        self.resizable(False, False)
        self.configure(bg=DARKER)
        self._set_icon()

        # state
        self.saves_path   = tk.StringVar(value=str(default_saves_path()))
        self.backup_path  = tk.StringVar(value=str(default_backup_path()))
        self.interval_min = tk.IntVar(value=10)
        self.keep_count   = tk.IntVar(value=10)

        self._running       = False
        self._worker_thread = None
        self._last_backup_at = None  # float timestamp or None
        self._backup_log: list[str] = []
        self._status_sims   = ""
        self._status_backup = "No backup yet"

        self._build_ui()
        self._tick()

    # ── icon ────────────────────────────────────────────────────────────────
    def _set_icon(self):
        # draw a tiny plumbob-shaped icon in memory
        try:
            img = tk.PhotoImage(width=32, height=32)
            for y in range(32):
                for x in range(32):
                    cx, cy = abs(x - 16), abs(y - 16)
                    if cx + cy <= 12:
                        img.put("#2ecc71", (x, y))
            self.iconphoto(True, img)
        except Exception:
            pass

    # ── layout ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        pad = {"padx": 14, "pady": 6}

        # ── header ──────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=DARK, pady=10)
        header.pack(fill="x")
        tk.Label(
            header, text="♦  Sims 4 Auto Save  ♦",
            font=("Segoe UI", 16, "bold"), fg=PINK, bg=DARK
        ).pack()
        tk.Label(
            header, text="Keep your game safe from crashes",
            font=("Segoe UI", 9), fg=GREY, bg=DARK
        ).pack()

        # ── status panel ────────────────────────────────────────────────────
        status_frame = tk.Frame(self, bg=DARKER, pady=8)
        status_frame.pack(fill="x", **pad)

        row1 = tk.Frame(status_frame, bg=DARKER)
        row1.pack(fill="x")
        tk.Label(row1, text="Game status:", font=("Segoe UI", 9), fg=GREY, bg=DARKER, width=14, anchor="w").pack(side="left")
        self._lbl_sims = tk.Label(row1, text="Checking…", font=("Segoe UI", 9, "bold"), fg=WHITE, bg=DARKER)
        self._lbl_sims.pack(side="left")

        row2 = tk.Frame(status_frame, bg=DARKER)
        row2.pack(fill="x", pady=(4, 0))
        tk.Label(row2, text="Last backup:", font=("Segoe UI", 9), fg=GREY, bg=DARKER, width=14, anchor="w").pack(side="left")
        self._lbl_backup = tk.Label(row2, text="—", font=("Segoe UI", 9, "bold"), fg=WHITE, bg=DARKER)
        self._lbl_backup.pack(side="left")

        # ── divider ─────────────────────────────────────────────────────────
        tk.Frame(self, bg=PURPLE, height=1).pack(fill="x", padx=14, pady=2)

        # ── settings ────────────────────────────────────────────────────────
        settings = tk.Frame(self, bg=DARKER)
        settings.pack(fill="x", **pad)

        self._path_row(settings, "Saves folder:", self.saves_path, self._browse_saves)
        self._path_row(settings, "Backup folder:", self.backup_path, self._browse_backup)

        opts = tk.Frame(settings, bg=DARKER)
        opts.pack(fill="x", pady=(6, 0))

        tk.Label(opts, text="Every", font=("Segoe UI", 9), fg=GREY, bg=DARKER).pack(side="left")
        interval_menu = ttk.Combobox(
            opts, textvariable=self.interval_min,
            values=[1, 2, 5, 10, 15, 20, 30], width=4, state="readonly"
        )
        interval_menu.pack(side="left", padx=4)
        tk.Label(opts, text="minutes  |  Keep", font=("Segoe UI", 9), fg=GREY, bg=DARKER).pack(side="left")
        keep_menu = ttk.Combobox(
            opts, textvariable=self.keep_count,
            values=[3, 5, 10, 20, 50], width=4, state="readonly"
        )
        keep_menu.pack(side="left", padx=4)
        tk.Label(opts, text="backups", font=("Segoe UI", 9), fg=GREY, bg=DARKER).pack(side="left")

        # ── buttons ─────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=DARKER)
        btn_frame.pack(fill="x", padx=14, pady=8)

        self._btn_start = tk.Button(
            btn_frame, text="▶  Start Auto Save",
            font=("Segoe UI", 10, "bold"), fg=WHITE, bg=PINK,
            activebackground="#c0176d", activeforeground=WHITE,
            relief="flat", padx=16, pady=6, cursor="hand2",
            command=self._toggle
        )
        self._btn_start.pack(side="left")

        tk.Button(
            btn_frame, text="Save Now",
            font=("Segoe UI", 9), fg=WHITE, bg=PURPLE,
            activebackground="#7d3f9b", activeforeground=WHITE,
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=self._manual_backup
        ).pack(side="left", padx=(8, 0))

        # ── log ─────────────────────────────────────────────────────────────
        tk.Frame(self, bg=PURPLE, height=1).pack(fill="x", padx=14, pady=(4, 0))
        log_frame = tk.Frame(self, bg=DARK)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        tk.Label(log_frame, text="Backup log", font=("Segoe UI", 8), fg=GREY, bg=DARK, anchor="w").pack(fill="x", padx=8, pady=(4, 0))
        self._log_box = tk.Text(
            log_frame, height=6, bg=DARK, fg="#a0a0c0",
            font=("Consolas", 8), relief="flat", state="disabled",
            insertbackground=WHITE
        )
        self._log_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # apply ttk style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=DARK, background=DARK, foreground=WHITE, selectbackground=PURPLE)

    def _path_row(self, parent, label, var, browse_cmd):
        row = tk.Frame(parent, bg=DARKER)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, font=("Segoe UI", 9), fg=GREY, bg=DARKER, width=14, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=var, font=("Segoe UI", 8), bg=DARK, fg=WHITE,
                 insertbackground=WHITE, relief="flat", width=34).pack(side="left", padx=(0, 4))
        tk.Button(row, text="…", font=("Segoe UI", 8), bg=PURPLE, fg=WHITE,
                  relief="flat", padx=4, cursor="hand2", command=browse_cmd).pack(side="left")

    # ── browse dialogs ───────────────────────────────────────────────────────
    def _browse_saves(self):
        d = filedialog.askdirectory(title="Select your Sims 4 Saves folder", initialdir=self.saves_path.get())
        if d:
            self.saves_path.set(d)

    def _browse_backup(self):
        d = filedialog.askdirectory(title="Select backup destination folder", initialdir=self.backup_path.get())
        if d:
            self.backup_path.set(d)

    # ── start / stop ─────────────────────────────────────────────────────────
    def _toggle(self):
        if self._running:
            self._running = False
            self._btn_start.config(text="▶  Start Auto Save", bg=PINK, activebackground="#c0176d")
            self._log("Auto save stopped.")
        else:
            saves = Path(self.saves_path.get())
            if not saves.exists():
                messagebox.showwarning(
                    "Saves folder not found",
                    f"Can't find:\n{saves}\n\nCheck the path and try again."
                )
                return
            self._running = True
            self._btn_start.config(text="⏹  Stop Auto Save", bg=RED, activebackground="#c0044a")
            self._log("Auto save started — watching for The Sims 4…")
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    # ── background worker ────────────────────────────────────────────────────
    def _worker(self):
        while self._running:
            interval_sec = self.interval_min.get() * 60
            elapsed = 0
            while self._running and elapsed < interval_sec:
                time.sleep(1)
                elapsed += 1

            if not self._running:
                break

            if sims_is_running():
                saves  = Path(self.saves_path.get())
                backup = Path(self.backup_path.get())
                backup.mkdir(parents=True, exist_ok=True)
                msg = perform_backup(saves, backup, self.keep_count.get())
                self._last_backup_at = time.time()
                self.after(0, lambda m=msg: self._log(m))
            else:
                self.after(0, lambda: self._log("Sims 4 not detected — skipping backup."))

    # ── manual backup ────────────────────────────────────────────────────────
    def _manual_backup(self):
        saves  = Path(self.saves_path.get())
        backup = Path(self.backup_path.get())
        backup.mkdir(parents=True, exist_ok=True)
        msg = perform_backup(saves, backup, self.keep_count.get())
        self._last_backup_at = time.time()
        self._log(msg)

    # ── log helper ───────────────────────────────────────────────────────────
    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {message}\n"
        self._log_box.config(state="normal")
        self._log_box.insert("end", line)
        self._log_box.see("end")
        self._log_box.config(state="disabled")
        self._backup_log.append(line)

    # ── periodic UI refresh ──────────────────────────────────────────────────
    def _tick(self):
        # game status
        if PSUTIL_AVAILABLE:
            if sims_is_running():
                self._lbl_sims.config(text="Running  ✓", fg=GREEN)
            else:
                self._lbl_sims.config(text="Not detected", fg=ORANGE)
        else:
            self._lbl_sims.config(text="psutil not installed — status unknown", fg=ORANGE)

        # last backup time
        if self._last_backup_at is not None:
            elapsed = time.time() - self._last_backup_at
            self._lbl_backup.config(text=human_elapsed(elapsed), fg=GREEN)
        else:
            self._lbl_backup.config(text="—", fg=GREY)

        self.after(5000, self._tick)  # refresh every 5 s


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    if not PSUTIL_AVAILABLE:
        print("Warning: 'psutil' is not installed.")
        print("Game-process detection will be disabled.")
        print("Install it with:  pip install psutil\n")

    app = AutoSaveApp()
    app.mainloop()


if __name__ == "__main__":
    main()
