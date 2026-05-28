#!/usr/bin/env python3
"""
Sleep Timer Pro — Windows Edition
stdlib only: tkinter, threading, subprocess, time, json, pathlib, os
"""

import tkinter as tk
from tkinter import messagebox
import threading
import subprocess
import time
import json
import os
from pathlib import Path

CONFIG_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "SleepTimerPro"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"minutes": 45, "action": "suspend"}


def save_config(minutes, action):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"minutes": minutes, "action": action}, f)


class SleepTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sleep Timer Pro")
        self.root.geometry("340x340")
        self.root.resizable(False, False)

        self.running       = False
        self.target_time   = None
        self.warning_shown = False

        cfg = load_config()
        self.minutes_var = tk.IntVar(value=cfg.get("minutes", 45))
        self.action_var  = tk.StringVar(value=cfg.get("action", "suspend"))

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        tk.Label(self.root, text="⏰  Sleep Timer Pro",
                 font=("Segoe UI", 15, "bold")).pack(pady=(16, 2))

        tk.Label(self.root, text="Suspend or shut down after N minutes",
                 font=("Segoe UI", 9), fg="#666666").pack()

        tk.Frame(self.root, height=1, bg="#cccccc").pack(fill=tk.X,
                                                          padx=20, pady=10)

        # Minutes row
        row = tk.Frame(self.root)
        row.pack()
        tk.Label(row, text="Minutes:", font=("Segoe UI", 11)).pack(side=tk.LEFT)
        self.spin = tk.Spinbox(row, from_=1, to=720,
                               textvariable=self.minutes_var,
                               width=6, font=("Segoe UI", 11))
        self.spin.pack(side=tk.LEFT, padx=8)

        # Preset buttons
        pre = tk.Frame(self.root)
        pre.pack(pady=(6, 0))
        for m in [15, 30, 45, 60, 90]:
            tk.Button(pre, text=f"{m}m",
                      command=lambda v=m: self.minutes_var.set(v),
                      width=4, relief=tk.GROOVE).pack(side=tk.LEFT, padx=2)

        # Action
        af = tk.LabelFrame(self.root, text=" Action ",
                           font=("Segoe UI", 9), padx=10, pady=6)
        af.pack(padx=20, pady=10, fill=tk.X)

        tk.Radiobutton(af, text="💤  Suspend  (preserves session)",
                       variable=self.action_var, value="suspend",
                       font=("Segoe UI", 10)).pack(anchor=tk.W)
        tk.Radiobutton(af, text="🔌  Shutdown  (full power off)",
                       variable=self.action_var, value="shutdown",
                       font=("Segoe UI", 10)).pack(anchor=tk.W)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Segoe UI", 11, "bold"),
                 fg="#005f87").pack(pady=(2, 8))

        # Buttons
        bf = tk.Frame(self.root)
        bf.pack()

        self.start_btn = tk.Button(bf, text="▶  Start Timer",
                                   command=self._start,
                                   width=14, height=2,
                                   bg="#27ae60", fg="white",
                                   font=("Segoe UI", 10, "bold"),
                                   relief=tk.FLAT, cursor="hand2")
        self.start_btn.pack(side=tk.LEFT, padx=6)

        self.cancel_btn = tk.Button(bf, text="✖  Cancel",
                                    command=self._cancel,
                                    width=10, height=2,
                                    bg="#e74c3c", fg="white",
                                    font=("Segoe UI", 10),
                                    relief=tk.FLAT, cursor="hand2",
                                    state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=6)

    # ----------------------------------------------------------------- logic

    def _start(self):
        try:
            minutes = self.minutes_var.get()
        except tk.TclError:
            messagebox.showerror("Invalid Input",
                                 "Please enter a valid number of minutes.")
            return
        if minutes < 1:
            messagebox.showerror("Invalid Input", "Minimum is 1 minute.")
            return

        save_config(minutes, self.action_var.get())

        self.running       = True
        self.warning_shown = False
        self.target_time   = time.time() + minutes * 60

        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.spin.config(state=tk.DISABLED)

        threading.Thread(target=self._countdown_loop, daemon=True).start()

    def _countdown_loop(self):
        while self.running:
            remaining = self.target_time - time.time()

            if remaining <= 0:
                if self.running:
                    self.root.after(0, self._execute_action)
                break

            mins = int(remaining // 60)
            secs = int(remaining % 60)
            text = f"{self.action_var.get().capitalize()} in {mins:02d}:{secs:02d}"
            self.root.after(0, lambda t=text: self.status_var.set(t))

            if not self.warning_shown and remaining <= 60:
                self.warning_shown = True
                self.root.after(0, self._show_warning)

            time.sleep(0.5)

    def _show_warning(self):
        action = self.action_var.get()
        dlg = tk.Toplevel(self.root)
        dlg.title(f"{action.capitalize()} Imminent")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        tk.Label(dlg,
                 text=f"System will {action} in 60 seconds.\n\nCancel the timer?",
                 font=("Segoe UI", 10), padx=20, pady=16).pack()

        bf = tk.Frame(dlg)
        bf.pack(pady=(0, 12))

        tk.Button(bf, text="Yes, Cancel",
                  command=lambda: [dlg.destroy(), self._cancel()],
                  width=12, bg="#e74c3c", fg="white",
                  relief=tk.FLAT).pack(side=tk.LEFT, padx=6)

        tk.Button(bf, text="No, Continue",
                  command=dlg.destroy,
                  width=12).pack(side=tk.LEFT, padx=6)

        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()  - 300) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 140) // 2
        dlg.geometry(f"300x140+{x}+{y}")

    def _execute_action(self):
        self.running = False  # race-condition guard — must be first
        action = self.action_var.get()
        try:
            if action == "suspend":
                subprocess.run(["rundll32.exe",
                                "powrprof.dll,SetSuspendState", "0,1,0"])
            else:
                subprocess.run(["shutdown", "/s", "/t", "0"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to {action}:\n{e}")
        self._reset_ui()

    def _cancel(self):
        self.running = False
        self._reset_ui()
        self.status_var.set("Cancelled")
        self.root.after(2000, lambda: self.status_var.set("Ready")
                        if not self.running else None)

    def _reset_ui(self):
        self.start_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.spin.config(state=tk.NORMAL)

    def _on_close(self):
        if self.running:
            if messagebox.askyesno("Timer Running",
                                   "A timer is running. Cancel it and close?"):
                self.running = False
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app  = SleepTimerApp(root)
    root.mainloop()
