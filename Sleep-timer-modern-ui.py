#!/usr/bin/env python3
"""
Sleep Timer — ttkbootstrap Professional Edition
Teal accent, circular arc progress, clean dark UI
"""

import tkinter as tk
import subprocess, threading, time
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageDraw
import pystray

TEAL       = "#00BCD4"
TEAL_DARK  = "#00838F"
WARN       = "#FF7043"
RING_TRACK = "#1E3035"
TEXT_DIM   = "#78909C"


class ProfessionalSleepTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Sleep Timer Pro")
        self.root.geometry("460x620")
        self.root.resizable(False, False)

        self.target_time = None
        self.running = False
        self.warning_shown = False
        self._reset_callback_id = None
        self._total_seconds = 0

        self.tray_icon = None
        self._tray_thread = None
        self._generation = 0

        self.root.style.theme_use("darkly")
        self._bg = str(self.root.style.colors.bg)

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ UI --

    def setup_ui(self):
        main = tb.Frame(self.root, padding=(24, 18, 24, 0))
        main.pack(fill=BOTH, expand=YES)

        # Header
        tb.Label(main, text="⏰  Sleep Timer Pro",
                 font=("Helvetica", 20, "bold"),
                 bootstyle="inverse-primary").pack()

        tb.Label(main, text="System power management",
                 font=("Helvetica", 10),
                 bootstyle="secondary").pack(pady=(2, 0))

        tb.Separator(main, bootstyle="secondary").pack(fill=X, pady=14)

        # Circular arc display
        self._setup_arc(main)

        tb.Separator(main, bootstyle="secondary").pack(fill=X, pady=14)

        # Duration row
        dur_row = tb.Frame(main)
        dur_row.pack(fill=X, pady=(0, 8))

        tb.Label(dur_row, text="Duration",
                 font=("Helvetica", 11),
                 bootstyle="secondary").pack(side=LEFT)

        self.minutes_var = tk.IntVar(value=45)
        self.time_spin = tb.Spinbox(dur_row, from_=1, to=720,
                                    textvariable=self.minutes_var,
                                    width=7, font=("Helvetica", 12))
        self.time_spin.pack(side=LEFT, padx=(10, 6))

        tb.Label(dur_row, text="min",
                 font=("Helvetica", 11),
                 bootstyle="secondary").pack(side=LEFT)

        # Preset buttons
        preset_row = tb.Frame(main)
        preset_row.pack(fill=X, pady=(0, 14))

        for m in [15, 30, 45, 60, 90, 120]:
            tb.Button(preset_row, text=f"{m}m",
                      command=lambda v=m: self.set_preset(v),
                      bootstyle="outline-secondary",
                      width=5).pack(side=LEFT, padx=2)

        # Action selection — teal-bordered card
        card_outer = tk.Frame(main, bg=TEAL_DARK, padx=1, pady=1)
        card_outer.pack(fill=X, pady=(0, 16))

        card_inner = tk.Frame(card_outer, bg="#1A2328")
        card_inner.pack(fill=X)

        self.action_var = tk.StringVar(value="suspend")

        for val, label in [("suspend",  "💤  Suspend  —  preserves session"),
                            ("shutdown", "🔌  Shutdown  —  full power off")]:
            tk.Radiobutton(card_inner, text=label,
                           variable=self.action_var, value=val,
                           bg="#1A2328", fg="white",
                           selectcolor="#1A2328",
                           activebackground="#1A2328",
                           activeforeground=TEAL,
                           font=("Helvetica", 10),
                           indicatoron=True).pack(anchor=W, padx=14, pady=5)

        # Start button — full width
        self.start_btn = tb.Button(main, text="▶   Start Timer",
                                   command=self.start_timer,
                                   bootstyle="success")
        self.start_btn.pack(fill=X, pady=(0, 6))

        # Cancel + Tray row
        btn_row = tb.Frame(main)
        btn_row.pack(fill=X)

        self.cancel_btn = tb.Button(btn_row, text="✖  Cancel",
                                    command=self.cancel_timer,
                                    bootstyle="outline-danger",
                                    state=DISABLED)
        self.cancel_btn.pack(side=LEFT, expand=YES, fill=X, padx=(0, 4))

        self.tray_btn = tb.Button(btn_row, text="⬇  To Tray",
                                  command=self.minimize_to_tray,
                                  bootstyle="outline-secondary")
        self.tray_btn.pack(side=LEFT, expand=YES, fill=X)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        tb.Label(self.root, textvariable=self.status_var,
                 bootstyle="inverse-secondary",
                 font=("Helvetica", 9),
                 anchor=W, padding=(12, 4)).pack(side=BOTTOM, fill=X)

    def _setup_arc(self, parent):
        SIZE, PAD = 210, 16
        self._arc_size = SIZE

        self.canvas = tk.Canvas(parent, width=SIZE, height=SIZE,
                                bg=self._bg, highlightthickness=0)
        self.canvas.pack()

        # Track ring
        self.canvas.create_oval(PAD, PAD, SIZE-PAD, SIZE-PAD,
                                outline=RING_TRACK, width=14, fill="")

        # Progress arc — starts empty (no timer running)
        self._arc = self.canvas.create_arc(PAD, PAD, SIZE-PAD, SIZE-PAD,
                                           start=90, extent=0,
                                           outline=TEAL, width=14,
                                           style=tk.ARC)

        cx, cy = SIZE // 2, SIZE // 2

        self._time_txt = self.canvas.create_text(cx, cy - 14,
                                                  text="00:00",
                                                  font=("Helvetica", 40, "bold"),
                                                  fill="white")
        self._sub_txt = self.canvas.create_text(cx, cy + 22,
                                                 text="No timer active",
                                                 font=("Helvetica", 10),
                                                 fill=TEXT_DIM)

    def _set_arc(self, fraction, warn=False):
        """fraction: 1.0 = full ring (timer just started), 0.0 = empty."""
        extent = -(fraction * 359.9)   # negative = clockwise depletion
        self.canvas.itemconfig(self._arc,
                               extent=extent,
                               outline=WARN if warn else TEAL)

    # --------------------------------------------------------- Timer logic --

    def set_preset(self, minutes):
        self.minutes_var.set(minutes)
        self.status_var.set(f"Preset: {minutes} minutes")

    def start_timer(self):
        try:
            minutes = self.minutes_var.get()
        except tk.TclError:
            Messagebox.show_error("Please enter a valid whole number of minutes.", "Invalid Input")
            return

        if minutes < 1:
            Messagebox.show_error("Minimum duration is 1 minute.", "Invalid Input")
            return

        self._total_seconds = minutes * 60
        self.target_time = time.time() + self._total_seconds
        self.running = True
        self.warning_shown = False
        self._generation += 1

        self.start_btn.config(state=DISABLED)
        self.cancel_btn.config(state=NORMAL)
        self.time_spin.config(state=DISABLED)

        self._set_arc(1.0)

        threading.Thread(target=self.countdown_loop, daemon=True).start()
        self.status_var.set(f"Running — will {self.action_var.get()} in {minutes} min")

    def countdown_loop(self):
        gen = self._generation
        while self.running:
            remaining = self.target_time - time.time()

            if remaining <= 0:
                if self.running:
                    self.root.after(0, self.execute_action)
                break

            mins     = int(remaining // 60)
            secs     = int(remaining % 60)
            time_str = f"{mins:02d}:{secs:02d}"
            fraction = remaining / self._total_seconds
            warn     = remaining <= 60

            self.root.after(0, lambda ts=time_str, f=fraction, w=warn, g=gen:
                            self.update_display(ts, f, w) if g == self._generation else None)

            if not self.warning_shown and remaining <= 60:
                self.warning_shown = True
                self.root.after(0, self.show_warning)

            time.sleep(0.5)

    def update_display(self, time_str, fraction, warn=False):
        self.canvas.itemconfig(self._time_txt,
                               text=time_str,
                               fill=WARN if warn else "white")

        sub = f"⚠  {self.action_var.get().upper()} IMMINENT" if warn \
              else f"will {self.action_var.get()} in {time_str}"
        self.canvas.itemconfig(self._sub_txt,
                               text=sub,
                               fill=WARN if warn else TEXT_DIM)

        self._set_arc(fraction, warn)
        self._update_tray_tooltip(time_str)

    def show_warning(self):
        action = self.action_var.get()
        result = Messagebox.show_question(
            f"The system will {action} in 60 seconds!\n\nCancel the timer?",
            f"{action.capitalize()} Imminent",
            buttons=["Yes", "No"]
        )
        if result == "Yes" and self.running:
            self.cancel_timer()

    def execute_action(self):
        if not self.running:
            return
        self.running = False
        action = self.action_var.get()
        try:
            if action == "suspend":
                subprocess.run(["systemctl", "suspend"], check=True)
            else:
                subprocess.run(["systemctl", "poweroff"], check=True)
        except Exception as e:
            Messagebox.show_error(f"Failed to {action}: {str(e)}", "Error")
        self.reset_ui()

    def cancel_timer(self):
        self.running = False
        if self._reset_callback_id is not None:
            self.root.after_cancel(self._reset_callback_id)
            self._reset_callback_id = None

        self.reset_ui()
        self.status_var.set("Timer cancelled")
        self.canvas.itemconfig(self._sub_txt, text="Timer cancelled", fill=WARN)
        self._reset_callback_id = self.root.after(2000, self._deferred_reset_display)
        self._update_tray_tooltip()

    def _deferred_reset_display(self):
        self._reset_callback_id = None
        if not self.running:
            self.canvas.itemconfig(self._sub_txt,
                                   text="No timer active", fill=TEXT_DIM)

    def reset_ui(self):
        self.start_btn.config(state=NORMAL)
        self.cancel_btn.config(state=DISABLED)
        self.time_spin.config(state=NORMAL)
        self.canvas.itemconfig(self._time_txt, text="00:00", fill="white")
        self._set_arc(0)

    # --------------------------------------------------------- Tray icon --

    def _build_tray_image(self):
        size = 64
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, size-4, size-4],
                     fill=(0, 188, 212), outline=(255, 255, 255), width=2)
        cx, cy = size // 2, size // 2
        draw.line([cx, cy, cx - 10, cy - 14], fill="white", width=3)
        draw.line([cx, cy, cx + 12, cy - 10], fill="white", width=2)
        return img

    def minimize_to_tray(self):
        if self.tray_icon is not None:
            return
        image = self._build_tray_image()
        menu  = pystray.Menu(
            pystray.MenuItem("Show",         self._restore_from_tray, default=True),
            pystray.MenuItem("Cancel Timer", self._tray_cancel),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",         self._tray_quit),
        )
        self.tray_icon = pystray.Icon("sleep_timer", image, "Sleep Timer", menu)
        self.root.withdraw()
        self._tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self._tray_thread.start()

    def _restore_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def _tray_cancel(self, icon=None, item=None):
        self.root.after(0, self.cancel_timer)
        self._restore_from_tray()

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self._quit_app)

    def _update_tray_tooltip(self, time_str=None):
        if self.tray_icon is None:
            return
        if self.running and time_str:
            self.tray_icon.title = f"Sleep Timer — {time_str} remaining"
        elif self.running:
            self.tray_icon.title = "Sleep Timer — running"
        else:
            self.tray_icon.title = "Sleep Timer — idle"

    # --------------------------------------------------------------- Close --

    def _quit_app(self):
        self.running = False
        if self._reset_callback_id is not None:
            self.root.after_cancel(self._reset_callback_id)
            self._reset_callback_id = None
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.destroy()

    def on_close(self):
        if self.running:
            result = Messagebox.show_question(
                "A timer is currently running.\n\nWhat do you want to do?",
                "Timer Active",
                buttons=["Minimize to Tray", "Cancel & Close", "Keep Running"]
            )
            if result == "Minimize to Tray":
                self.minimize_to_tray()
            elif result == "Cancel & Close":
                self.running = False
                if self._reset_callback_id is not None:
                    self.root.after_cancel(self._reset_callback_id)
                    self._reset_callback_id = None
                self.root.destroy()
        else:
            self._quit_app()


if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    app  = ProfessionalSleepTimer(root)
    root.mainloop()
