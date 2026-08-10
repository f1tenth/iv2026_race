#!/usr/bin/env python3
"""
Roboracer Event Manager - GUI tool for managing race event configurations.

This tool allows organizers to:
- Configure event details (conference name, venue, dates, etc.)
- Automatically calculate timeline dates from the race day
- Update all HTML/MD files with new event information
- Import registrants from Excel files
- Generate registrant HTML tables

Run with: uv run python Utils/event_manager.py
"""

import io
import json
import os
import re
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk
from typing import Any

import cairosvg
from PIL import Image
from tkcalendar import Calendar
from ttkthemes import ThemedTk

import certification as cert
import schedule as sched

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "event_config.json"


def load_config() -> dict:
    """Load event configuration from JSON file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_config()


def save_config(config: dict) -> None:
    """Save event configuration to JSON file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def _is_int(value: str) -> bool:
    """True if the string is a (possibly negative) integer token."""
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def get_default_config() -> dict:
    """Return default configuration template."""
    return {
        "event": {
            "conference_name": "ICRA",
            "conference_full_name": "IEEE Conference on Robotics and Automation",
            "race_number": "25TH",
            "year": "2026",
            "venue_name": "Venue Name",
            "location": "City, State, Country",
            "venue_url": "https://venue-website.com",
            "conference_url": "https://conference-website.com",
            "conference_logo": "images/ICRA2026.png",
            "contact_email": "roboracer@email.com",
            "cname": "icra2026-race.roboracer.ai",
            "conference_dates_display": "Month Day - Day",
        },
        "dates": {
            "race_day": datetime.now().strftime("%Y-%m-%d"),
            "offsets": {
                "qualification": -1,
                "team_training": -2,
                "track_setup": -3,
                "orientation_2": -38,
                "registration_closes": -40,
                "orientation_1": -66,
                "registration_open": -113,
            },
        },
        "competition_days": {
            "track_setup": {"enabled": True, "date_override": "", "time_display": ""},
            "team_training": {"enabled": True, "date_override": "", "time_display": ""},
            "qualification": {"enabled": True, "date_override": "", "time_display": ""},
            "race": {"enabled": True, "date_override": "", "time_display": ""},
        },
        "orientation_1": {
            "time_display": "11:00AM - 12:00PM ET",
            "date_override": "",
            "zoom_link": "",
            "slides_link": "",
            "video_link": "",
        },
        "orientation_2": {
            "time_display": "11:00AM - 12:00PM ET",
            "date_override": "",
            "zoom_link": "",
            "slides_link": "",
            "video_link": "",
        },
        "registration": {
            "status": "closed",
            "form_link": "",
            "video_demo_form_link": "",
            "hardware_list_form_link": "",
            "hide_participants": False,
            "registration_open_date_override": "",
            "registration_closes_date_override": "",
        },
        "results": {
            "time_trial_sheet_link": "",
            "bracket_link": "",
            "bracket_embed_url": "",
            "twitch_parent_domains": ["localhost"],
            "youtube_stream_id": "",
            "show_stream_placeholder": True,
            "stream_placeholder_text": "Live stream will appear here during the event.",
            "show_results_placeholder": True,
            "results_placeholder_text": "Results will be posted after the competition.",
        },
        "sim_racing": {
            "enabled": True,
            "edition": "3rd",
            "website_url": "",
            "registration_url": "",
            "timeline_url": "",
        },
        "extra_resources": "",
        "certification": {
            "csv_paths": {"registration": "", "video": "", "hardware": ""},
            "ticks": {},
            "overrides": {
                "submission_links": {},
                "ignored_submissions": [],
                "blocked_links": [],
                "allowed_links": [],
            },
            "member_overrides": {},
            "manual_teams": [],
            "email": {
                "signature": "RoboRacer Organizing Team",
                "conference_registration_url": "",
                "conference_registration_note": "",
                "confirmation_extra": "",
                "reminder_extra": "",
            },
        },
        "schedule": {
            "timezone_label": "ET",
            "csv_path": "",
            "group_size": 4,
            "groups": {},
            "days": [],
        },
        "organizers": [
            {
                "name": "Rahul Mangharam",
                "image": "images/organizer/rahul.jpeg",
                "profile_url": "https://www.seas.upenn.edu/~rahulm/",
                "title": "Associate Professor",
                "department": "Department of Electrical and Systems Engineering",
                "institution": "University of Pennsylvania",
            },
            {
                "name": "Venkat Krovi",
                "image": "images/organizer/venkat.jpeg",
                "profile_url": "https://www.clemson.edu/cecas/departments/automotive-engineering/people/Venkat%20Krovi.html",
                "title": "Michelin Chair Professor",
                "department": "Department of Automotive Engineering",
                "institution": "Clemson University",
            },
            {
                "name": "Radu Grosu",
                "image": "images/organizer/Radu.png",
                "profile_url": "https://tiss.tuwien.ac.at/person/248818.html",
                "title": "Full Professor and Head of Research Unit",
                "department": "Research Unit of Cyber-Physical Systems",
                "institution": "TU Wien (Vienna University of Technology)",
            },
            {
                "name": "Ezio Bartocci",
                "image": "images/organizer/Ezio.jpg",
                "profile_url": "https://tiss.tuwien.ac.at/person/251490.html",
                "title": "Full Professor",
                "department": "Research Unit of Cyber-Physical Systems",
                "institution": "TU Wien (Vienna University of Technology)",
            },
        ],
    }


def calculate_dates(race_day: str, offsets: dict) -> dict:
    """Calculate all event dates based on race day and offsets."""
    race_date = datetime.strptime(race_day, "%Y-%m-%d")
    dates = {"race": race_date}

    for event_name, offset in offsets.items():
        dates[event_name] = race_date + timedelta(days=offset)

    return dates


def format_date_display(date: datetime, include_ordinal: bool = True) -> str:
    """Format date for display (e.g., 'May 22nd')."""
    day = date.day
    if include_ordinal:
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{date.strftime('%B')} {day}{suffix}"
    return f"{date.strftime('%B')} {day}"


class ScaleDialog:
    """Dialog to get a scale factor from the user."""

    def __init__(self, parent, title: str, message: str, default_value: float = 1.0):
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Dark theme styling
        self.dialog.configure(bg="#1e1e2e")

        # Center the dialog
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)

        # Message label
        msg_label = tk.Label(
            self.dialog,
            text=message,
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
            justify="left"
        )
        msg_label.pack(padx=20, pady=(20, 10))

        # Scale entry
        entry_frame = tk.Frame(self.dialog, bg="#1e1e2e")
        entry_frame.pack(pady=10)

        tk.Label(
            entry_frame,
            text="Scale factor:",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Ubuntu", 10)
        ).pack(side="left", padx=(0, 10))

        self.scale_entry = tk.Entry(
            entry_frame,
            width=10,
            bg="#3c3c3c",
            fg="white",
            insertbackground="white",
            font=("Ubuntu", 10)
        )
        self.scale_entry.pack(side="left")
        self.scale_entry.insert(0, str(default_value))
        self.scale_entry.select_range(0, tk.END)
        self.scale_entry.focus_set()

        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#1e1e2e")
        btn_frame.pack(pady=20)

        ok_btn = tk.Button(
            btn_frame,
            text="OK",
            command=self.on_ok,
            bg="#45475a",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
            width=10
        )
        ok_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self.on_cancel,
            bg="#45475a",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
            width=10
        )
        cancel_btn.pack(side="left", padx=5)

        # Bind Enter key
        self.scale_entry.bind("<Return>", lambda e: self.on_ok())
        self.dialog.bind("<Escape>", lambda e: self.on_cancel())

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def on_ok(self):
        try:
            self.result = float(self.scale_entry.get())
            if self.result <= 0:
                raise ValueError("Scale must be positive")
            self.dialog.destroy()
        except ValueError:
            tk.messagebox.showerror(
                "Invalid Input",
                "Please enter a valid positive number."
            )

    def on_cancel(self):
        self.result = None
        self.dialog.destroy()


class OrganizerEditDialog:
    """Dialog to add or edit an organizer."""

    def __init__(self, parent, title: str, organizer: dict | None = None):
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Dark theme styling
        self.dialog.configure(bg="#1e1e2e")

        # Center the dialog
        self.dialog.geometry("500x350")
        self.dialog.resizable(False, False)

        # Main frame
        main_frame = tk.Frame(self.dialog, bg="#1e1e2e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Entry fields
        self.entries = {}
        fields = [
            ("name", "Name:"),
            ("profile_url", "Profile URL:"),
            ("title", "Title:"),
            ("department", "Department:"),
            ("institution", "Institution:"),
        ]

        for i, (field_key, label_text) in enumerate(fields):
            tk.Label(
                main_frame,
                text=label_text,
                bg="#1e1e2e",
                fg="#cdd6f4",
                font=("Ubuntu", 10),
            ).grid(row=i, column=0, sticky="w", pady=5)

            entry = tk.Entry(
                main_frame,
                width=45,
                bg="#2a2a3c",
                fg="#cdd6f4",
                insertbackground="#cdd6f4",
                relief=tk.FLAT,
                font=("Ubuntu", 10),
                highlightthickness=1,
                highlightcolor="#89b4fa",
                highlightbackground="#45475a",
            )
            entry.grid(row=i, column=1, sticky="ew", pady=5, ipady=4)
            self.entries[field_key] = entry

        # Image field with browse button
        row = len(fields)
        tk.Label(
            main_frame,
            text="Image:",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
        ).grid(row=row, column=0, sticky="w", pady=5)

        image_frame = tk.Frame(main_frame, bg="#1e1e2e")
        image_frame.grid(row=row, column=1, sticky="ew", pady=5)

        self.image_entry = tk.Entry(
            image_frame,
            width=35,
            bg="#2a2a3c",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief=tk.FLAT,
            font=("Ubuntu", 10),
            highlightthickness=1,
            highlightcolor="#89b4fa",
            highlightbackground="#45475a",
        )
        self.image_entry.pack(side="left", fill="x", expand=True, ipady=4)

        browse_btn = tk.Button(
            image_frame,
            text="Browse",
            command=self.browse_image,
            bg="#45475a",
            fg="#cdd6f4",
            font=("Ubuntu", 9),
            relief=tk.FLAT,
            padx=10,
            cursor="hand2",
        )
        browse_btn.pack(side="left", padx=(5, 0))

        # Populate fields if editing
        if organizer:
            for key, entry in self.entries.items():
                entry.insert(0, organizer.get(key, ""))
            self.image_entry.insert(0, organizer.get("image", ""))

        # Buttons frame
        btn_frame = tk.Frame(self.dialog, bg="#1e1e2e")
        btn_frame.pack(pady=15)

        save_btn = tk.Button(
            btn_frame,
            text="Save",
            command=self.on_save,
            bg="#89b4fa",
            fg="#1e1e2e",
            font=("Ubuntu", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=6,
            cursor="hand2",
        )
        save_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self.on_cancel,
            bg="#45475a",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
            relief=tk.FLAT,
            padx=20,
            pady=6,
            cursor="hand2",
        )
        cancel_btn.pack(side="left", padx=5)

        # Bind keys
        self.dialog.bind("<Return>", lambda e: self.on_save())
        self.dialog.bind("<Escape>", lambda e: self.on_cancel())

        # Focus first entry
        self.entries["name"].focus_set()

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def browse_image(self):
        """Open file dialog to select organizer image."""
        initial_dir = PROJECT_ROOT / "images" / "organizer"
        if not initial_dir.exists():
            initial_dir = PROJECT_ROOT / "images"

        filepath = filedialog.askopenfilename(
            title="Select Organizer Image",
            initialdir=initial_dir,
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.gif"),
                ("All files", "*.*"),
            ],
        )

        if filepath:
            try:
                rel_path = Path(filepath).relative_to(PROJECT_ROOT)
                self.image_entry.delete(0, tk.END)
                self.image_entry.insert(0, str(rel_path))
            except ValueError:
                messagebox.showwarning(
                    "File Location",
                    "Please select an image from within the project directory.",
                )

    def on_save(self):
        """Validate and save organizer data."""
        name = self.entries["name"].get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Name is required.")
            return

        self.result = {
            "name": name,
            "profile_url": self.entries["profile_url"].get().strip(),
            "title": self.entries["title"].get().strip(),
            "department": self.entries["department"].get().strip(),
            "institution": self.entries["institution"].get().strip(),
            "image": self.image_entry.get().strip(),
        }
        self.dialog.destroy()

    def on_cancel(self):
        self.result = None
        self.dialog.destroy()


class EventManagerApp:
    """Main application class for the Event Manager GUI."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Roboracer Event Manager")

        # Load configuration (needed before styling for the UI scale).
        self.config = load_config()

        # Resolve and apply HiDPI scaling before any widgets/styles are created.
        self.ui_scale = self._resolve_ui_scale()
        self._apply_ui_scaling()

        # Configure custom styles
        self.setup_styles()

        # Certification state (persisted under config["certification"]).
        self.certification_data = self.config.get(
            "certification", get_default_config()["certification"]
        )
        # Ensure all sub-keys exist for configs saved by older versions.
        self.certification_data.setdefault(
            "csv_paths", {"registration": "", "video": "", "hardware": ""}
        )
        self.certification_data.setdefault("ticks", {})
        self.certification_data.setdefault("member_overrides", {})
        self.certification_data.setdefault("manual_teams", [])
        self.certification_data.setdefault("email", {
            "signature": "RoboRacer Organizing Team",
            "conference_registration_url": "",
            "conference_registration_note": "",
            "confirmation_extra": "",
            "reminder_extra": "",
        })
        self.cert_teams: list = []  # last processed Team objects
        self.cert_registrations: list = []

        # Schedule state (persisted under config["schedule"]).
        self.schedule_data = self.config.get(
            "schedule", get_default_config()["schedule"]
        )
        self.schedule_data.setdefault("timezone_label", "ET")
        self.schedule_data.setdefault("csv_path", "")
        self.schedule_data.setdefault("group_size", 4)
        self.schedule_data.setdefault("groups", {})
        self.schedule_data.setdefault("days", [])

        # Create main notebook (tabs). Packed last so the bottom button row
        # (packed to side=BOTTOM first) always keeps its space.
        self.notebook = ttk.Notebook(root)

        # Create tabs
        self.create_event_tab()
        self.create_dates_tab()
        self.create_competition_days_tab()
        self.create_orientations_tab()
        self.create_registration_tab()
        self.create_results_tab()
        self.create_organizers_tab()
        self.create_registrants_tab()
        self.create_schedule_tab()
        self.create_resources_tab()

        # Create bottom button frame (reserves the bottom edge), then let the
        # notebook expand into the remaining space.
        self.create_button_frame()
        self.notebook.pack(
            fill=tk.BOTH, expand=True, padx=self.px(10), pady=self.px(10)
        )

        # Scale inline fonts on all tk widgets created above (ttk uses styles).
        self._scale_widget_fonts(self.root)

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _resolve_ui_scale(self) -> float:
        """Resolve the UI scale: env override > config > auto-detect (clamped)."""
        self._ui_scale_setting = self.config.get("ui_scale")  # None = auto
        value = None
        env = os.environ.get("EVENT_MANAGER_UI_SCALE")
        if env:
            try:
                value = float(env)
            except ValueError:
                value = None
        if value is None and self._ui_scale_setting:
            try:
                value = float(self._ui_scale_setting)
            except (TypeError, ValueError):
                value = None
        if value is None:
            try:
                value = self.root.winfo_fpixels("1i") / 96.0
            except Exception:
                value = 1.0
        return max(1.0, min(4.0, value))

    def _apply_ui_scaling(self) -> None:
        """Apply the resolved scale to the window, named fonts, and Tk scaling.

        Tk's ``tk scaling`` is unreliable for enlarging fonts on Linux/Xft, so we
        pin it to a fixed 96-DPI baseline and instead scale font *sizes* explicitly
        (named fonts here; ttk styles in setup_styles; inline tk widget fonts via
        _scale_widget_fonts). Pinning the baseline avoids double-scaling.
        """
        self.root.tk.call("tk", "scaling", 96.0 / 72.0)

        # Scale the default/named fonts (message boxes, menus, default widgets).
        if self.ui_scale != 1.0:
            for name in tkfont.names(self.root):
                self._scale_font_object(tkfont.nametofont(name))

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = min(self.px(1000), screen_w - 100)
        h = min(self.px(850), screen_h - 100)
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(min(self.px(900), w), min(self.px(750), h))

    def _scale_font_object(self, f: tkfont.Font) -> None:
        """Multiply a font's size by ui_scale (preserving point/pixel sign)."""
        size = f.cget("size")
        if size:
            new = int(round(abs(size) * self.ui_scale))
            f.configure(size=new if size > 0 else -new)

    def _scaled_font_from_spec(self, spec: str):
        """Build a scaled Font from a Tk font spec string (e.g. 'Ubuntu 12 bold').

        Parses the integer size token out of the spec ourselves rather than asking
        Tk to resolve it (unreliable when the family isn't installed). Returns a
        cached Font, or None if no size is found.
        """
        cache = self.__dict__.setdefault("_scaled_font_cache", {})
        if spec in cache:
            return cache[spec]
        try:
            tokens = list(self.root.tk.splitlist(spec))
        except tk.TclError:
            return None
        size_idx = next((i for i, t in enumerate(tokens) if _is_int(t)), None)
        if size_idx is None or size_idx == 0:
            return None
        family = " ".join(tokens[:size_idx])
        size = int(tokens[size_idx])
        styles = [t.lower() for t in tokens[size_idx + 1:]]
        new_size = int(round(abs(size) * self.ui_scale))
        if size < 0:
            new_size = -new_size
        try:
            f = tkfont.Font(
                root=self.root, family=family, size=new_size,
                weight="bold" if "bold" in styles else "normal",
                slant="italic" if "italic" in styles else "roman",
                underline="underline" in styles, overstrike="overstrike" in styles,
            )
        except tk.TclError:
            return None
        cache[spec] = f  # keep a ref alive (Font.__del__ deletes the Tcl font)
        return f

    def _scale_widget_fonts(self, widget) -> None:
        """Recursively scale inline (non-named) fonts on tk widgets in a tree.

        ttk widgets are font-styled via setup_styles and skipped here; widgets
        using a named font are skipped (already scaled in _apply_ui_scaling).
        """
        if self.ui_scale == 1.0:
            return
        named = set(tkfont.names(self.root))

        def walk(w):
            try:
                spec = str(w.cget("font"))
            except tk.TclError:
                spec = ""
            if spec and spec not in named:
                f = self._scaled_font_from_spec(spec)
                if f is not None:
                    try:
                        w.configure(font=f)
                    except tk.TclError:
                        pass
            for child in w.winfo_children():
                walk(child)

        walk(widget)

    def px(self, n: float) -> int:
        """Scale a pixel value by the current UI scale."""
        return int(round(n * self.ui_scale))

    def _bind_mousewheel(self, canvas) -> None:
        """Enable mouse-wheel scrolling over a Canvas (Linux/X11 uses Button-4/5)."""
        def on_wheel(event):
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            elif getattr(event, "delta", 0):
                canvas.yview_scroll(int(-event.delta / 120), "units")

        def _bind(_=None):
            canvas.bind_all("<Button-4>", on_wheel)
            canvas.bind_all("<Button-5>", on_wheel)
            canvas.bind_all("<MouseWheel>", on_wheel)

        def _unbind(_=None):
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)

    def setup_styles(self) -> None:
        """Configure custom styles for the application."""
        style = ttk.Style()

        # Use 'clam' as base theme - it's the most customizable
        style.theme_use("clam")

        # Dark theme colors
        bg_dark = "#1e1e2e"  # Dark background
        bg_surface = "#2a2a3c"  # Surface/card background
        bg_hover = "#3a3a4c"  # Hover state
        text_primary = "#cdd6f4"  # Primary text
        text_secondary = "#a6adc8"  # Secondary text
        accent = "#89b4fa"  # Blue accent
        accent_hover = "#b4befe"  # Lighter blue
        success = "#a6e3a1"  # Green
        border = "#45475a"  # Border color

        # Font - using commonly available fonts on Linux (sizes scaled for HiDPI)
        def _fs(pt: int) -> int:
            return max(1, int(round(pt * self.ui_scale)))

        main_font = ("Ubuntu", _fs(10))
        main_font_bold = ("Ubuntu", _fs(10), "bold")
        header_font = ("Ubuntu", _fs(12), "bold")
        mono_font = ("Ubuntu Mono", _fs(10))

        # Configure notebook tab styling
        style.configure(
            "TNotebook",
            background=bg_dark,
            borderwidth=0,
            tabmargins=[8, 8, 8, 0],
        )
        style.configure(
            "TNotebook.Tab",
            background=bg_surface,
            foreground=text_secondary,
            padding=[16, 8],
            font=main_font,
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#00bcd4"), ("active", bg_hover)],
            foreground=[("selected", "#1e1e2e"), ("active", text_primary)],
            padding=[("selected", [18, 12])],
            expand=[("selected", [0, 2, 0, 0])],
        )

        # Configure frame background
        style.configure("TFrame", background=bg_dark)

        # Configure labels
        style.configure(
            "TLabel",
            background=bg_dark,
            foreground=text_primary,
            font=main_font,
        )
        style.configure(
            "Header.TLabel",
            background=bg_dark,
            foreground=accent,
            font=header_font,
        )

        # Configure entry fields
        style.configure(
            "TEntry",
            fieldbackground=bg_surface,
            foreground=text_primary,
            insertcolor=text_primary,
            padding=8,
            font=main_font,
        )

        # Configure buttons
        style.configure(
            "TButton",
            background=bg_surface,
            foreground=text_primary,
            padding=[14, 8],
            font=main_font,
            borderwidth=1,
        )
        style.map(
            "TButton",
            background=[("active", bg_hover), ("pressed", accent)],
            foreground=[("pressed", bg_dark)],
        )

        style.configure(
            "Accent.TButton",
            background=accent,
            foreground=bg_dark,
            padding=[14, 8],
            font=main_font_bold,
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover)],
        )

        # Configure checkbuttons and radiobuttons
        style.configure(
            "TCheckbutton",
            background=bg_dark,
            foreground=text_primary,
            font=main_font,
        )
        style.configure(
            "TRadiobutton",
            background=bg_dark,
            foreground=text_primary,
            font=main_font,
        )

        # Configure separators
        style.configure("TSeparator", background=border)

        # Configure label frames (section cards) with an accent title
        style.configure(
            "TLabelframe",
            background=bg_dark,
            bordercolor=border,
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "TLabelframe.Label",
            background=bg_dark,
            foreground=accent,
            font=main_font_bold,
        )

        # Configure tree views (registrants / certification tables)
        style.configure(
            "Treeview",
            background=bg_surface,
            fieldbackground=bg_surface,
            foreground=text_primary,
            borderwidth=0,
            rowheight=self.px(24),
            font=main_font,
        )
        style.map(
            "Treeview",
            background=[("selected", accent)],
            foreground=[("selected", bg_dark)],
        )
        style.configure(
            "Treeview.Heading",
            background=bg_dark,
            foreground=accent,
            font=main_font_bold,
            borderwidth=0,
            padding=[6, 6],
        )
        style.map("Treeview.Heading", background=[("active", bg_hover)])

        # Configure comboboxes (certification submission/registration pickers)
        style.configure(
            "TCombobox",
            fieldbackground=bg_surface,
            background=bg_surface,
            foreground=text_primary,
            arrowcolor=text_primary,
            bordercolor=border,
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", bg_surface)],
            foreground=[("readonly", text_primary)],
            selectbackground=[("readonly", bg_surface)],
            selectforeground=[("readonly", text_primary)],
        )

        # Configure text widget colors (for preview areas)
        self.text_bg = bg_surface
        self.text_fg = text_primary

        # Set root background
        self.root.configure(bg=bg_dark)

    def create_labeled_entry(
        self, parent: tk.Widget, label: str, row: int, default: str = ""
    ) -> tk.Entry:
        """Create a labeled entry field with dark theme styling."""
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        entry = tk.Entry(
            parent,
            width=60,
            bg="#2a2a3c",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief=tk.FLAT,
            font=("Ubuntu", 10),
            highlightthickness=1,
            highlightcolor="#89b4fa",
            highlightbackground="#45475a",
        )
        entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5, ipady=5)
        entry.insert(0, default)
        return entry

    def create_event_tab(self) -> None:
        """Create the Event Details tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Event Details")

        # Configure grid
        frame.columnconfigure(1, weight=1)

        event = self.config.get("event", {})

        row = 0
        self.conference_name_entry = self.create_labeled_entry(
            frame, "Conference Acronym (e.g., ICRA):", row, event.get("conference_name", "")
        )
        row += 1
        self.conference_full_name_entry = self.create_labeled_entry(
            frame, "Conference Full Name (no year):", row, event.get("conference_full_name", "")
        )
        row += 1
        self.race_number_entry = self.create_labeled_entry(
            frame, "Race Number (e.g., 24TH):", row, event.get("race_number", "")
        )
        row += 1
        self.year_entry = self.create_labeled_entry(
            frame, "Year:", row, event.get("year", "")
        )
        row += 1
        self.venue_name_entry = self.create_labeled_entry(
            frame, "Venue Name:", row, event.get("venue_name", "")
        )
        row += 1
        self.location_entry = self.create_labeled_entry(
            frame, "Location:", row, event.get("location", "")
        )
        row += 1
        self.venue_url_entry = self.create_labeled_entry(
            frame, "Venue URL:", row, event.get("venue_url", "")
        )
        row += 1
        self.conference_url_entry = self.create_labeled_entry(
            frame, "Conference URL:", row, event.get("conference_url", "")
        )
        row += 1
        # Conference logo with file picker
        ttk.Label(frame, text="Conference Logo:").grid(
            row=row, column=0, sticky="w", padx=5, pady=2
        )
        logo_frame = ttk.Frame(frame)
        logo_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.conference_logo_entry = tk.Entry(logo_frame, width=40, bg="#3c3c3c", fg="white", insertbackground="white")
        self.conference_logo_entry.pack(side="left", fill="x", expand=True)
        self.conference_logo_entry.insert(0, event.get("conference_logo", ""))
        browse_btn = ttk.Button(
            logo_frame, text="Browse...", command=self.browse_conference_logo, style="Accent.TButton"
        )
        browse_btn.pack(side="left", padx=(5, 0))
        row += 1
        self.contact_email_entry = self.create_labeled_entry(
            frame, "Contact Email:", row, event.get("contact_email", "")
        )
        row += 1
        self.cname_entry = self.create_labeled_entry(
            frame, "CNAME (domain):", row, event.get("cname", "")
        )
        row += 1
        self.conference_dates_display_entry = self.create_labeled_entry(
            frame,
            "Conference Dates (no year, e.g., May 19th - 23rd):",
            row,
            event.get("conference_dates_display", ""),
        )

    def create_dates_tab(self) -> None:
        """Create the Dates/Timeline tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Dates & Timeline")

        frame.columnconfigure(1, weight=1)

        dates = self.config.get("dates", {})
        offsets = dates.get("offsets", {})

        row = 0
        ttk.Label(
            frame, text="Set the Race Day and offsets to calculate all dates:"
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)

        row += 1
        ttk.Label(frame, text="Race Day:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )

        # Date picker frame with entry and button
        date_frame = ttk.Frame(frame)
        date_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        self.race_day_var = tk.StringVar(value=dates.get("race_day", ""))
        self.race_day_entry = tk.Entry(
            date_frame,
            textvariable=self.race_day_var,
            width=15,
            bg="#2a2a3c",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief=tk.FLAT,
            font=("Ubuntu", 10),
            highlightthickness=1,
            highlightcolor="#89b4fa",
            highlightbackground="#45475a",
        )
        self.race_day_entry.pack(side=tk.LEFT, padx=(0, 5), ipady=5)

        ttk.Button(date_frame, text="Pick Date...", command=self.open_calendar_dialog).pack(
            side=tk.LEFT
        )

        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=10
        )

        row += 1
        ttk.Label(frame, text="Day Offsets (relative to race day):").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5
        )

        self.offset_entries = {}
        offset_labels = {
            "qualification": "Qualification (day before race)",
            "team_training": "Team Training",
            "track_setup": "Track Setup",
            "orientation_2": "Orientation 2",
            "registration_closes": "Registration Closes",
            "orientation_1": "Orientation 1",
            "registration_open": "Registration Opens",
        }

        for name, label in offset_labels.items():
            row += 1
            ttk.Label(frame, text=f"{label}:").grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=4
            )
            entry = tk.Entry(
                frame,
                width=10,
                bg="#2a2a3c",
                fg="#cdd6f4",
                insertbackground="#cdd6f4",
                relief=tk.FLAT,
                font=("Ubuntu", 10),
                highlightthickness=1,
                highlightcolor="#89b4fa",
                highlightbackground="#45475a",
            )
            entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4, ipady=3)
            entry.insert(0, str(offsets.get(name, 0)))
            self.offset_entries[name] = entry

        row += 1
        ttk.Button(frame, text="Calculate & Preview Dates", command=self.preview_dates).grid(
            row=row, column=0, columnspan=2, pady=20
        )

        row += 1
        self.dates_preview = tk.Text(
            frame,
            height=12,
            width=60,
            state=tk.DISABLED,
            bg="#2a2a3c",
            fg="#cdd6f4",
            font=("Ubuntu Mono", 10),
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.dates_preview.grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5
        )

    def create_competition_days_tab(self) -> None:
        """Create the Competition Days tab with per-day toggle, date override, and time."""
        outer_frame = ttk.Frame(self.notebook, padding=0)
        self.notebook.add(outer_frame, text="Competition Days")

        canvas = tk.Canvas(outer_frame, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=10)

        frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(canvas)

        frame.columnconfigure(1, weight=1)

        comp_days_config = self.config.get("competition_days", {})

        row = 0
        ttk.Label(
            frame,
            text="Configure each on-site competition day. Disable a day to hide it from the timeline.\nTip: set Qualification and Race to the same date to merge them into one day.",
            foreground="#a6adc8",
        ).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        self.comp_days_enabled: dict[str, tk.BooleanVar] = {}
        self.comp_days_date_override: dict[str, tk.Entry] = {}
        self.comp_days_time: dict[str, tk.Entry] = {}
        self.comp_days_date_labels: dict[str, ttk.Label] = {}

        day_defs = [
            ("track_setup", "Day 1: On-site Registration & Training"),
            ("team_training", "Day 2: Training / Practice Sessions"),
            ("qualification", "Day 3: Qualification Time Trials"),
            ("race", "Day 4: Head-to-Head Tournament"),
        ]

        for day_key, day_title in day_defs:
            day_cfg = comp_days_config.get(day_key, {})

            row += 1
            ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
                row=row, column=0, columnspan=3, sticky=tk.EW, pady=10
            )

            row += 1
            header_frame = ttk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

            ttk.Label(header_frame, text=day_title, font=("Ubuntu", 11, "bold")).pack(
                side=tk.LEFT, padx=(0, 15)
            )
            enabled_var = tk.BooleanVar(value=day_cfg.get("enabled", True))
            self.comp_days_enabled[day_key] = enabled_var
            ttk.Checkbutton(header_frame, text="Enabled", variable=enabled_var).pack(side=tk.LEFT)

            row += 1
            ttk.Label(frame, text="Calculated Date:").grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=3
            )
            date_label = ttk.Label(
                frame, text="(calculate in Dates tab)", foreground="#00bcd4"
            )
            date_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
            self.comp_days_date_labels[day_key] = date_label

            row += 1
            ttk.Label(frame, text="Date Override (e.g., June 21st):").grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=3
            )
            date_frame = ttk.Frame(frame)
            date_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)

            date_entry = tk.Entry(
                date_frame,
                width=20,
                bg="#2a2a3c",
                fg="#cdd6f4",
                insertbackground="#cdd6f4",
                relief=tk.FLAT,
                font=("Ubuntu", 10),
                highlightthickness=1,
                highlightcolor="#89b4fa",
                highlightbackground="#45475a",
            )
            date_entry.pack(side=tk.LEFT, padx=(0, 5), ipady=5)
            date_entry.insert(0, day_cfg.get("date_override", ""))
            self.comp_days_date_override[day_key] = date_entry

            ttk.Button(
                date_frame,
                text="Pick Date...",
                command=lambda e=date_entry: self.open_date_picker_for_entry(e),
            ).pack(side=tk.LEFT)

            row += 1
            ttk.Label(frame, text="Time (e.g., 9:00AM - 6:00PM ET):").grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=3
            )
            time_entry = tk.Entry(
                frame,
                width=30,
                bg="#2a2a3c",
                fg="#cdd6f4",
                insertbackground="#cdd6f4",
                relief=tk.FLAT,
                font=("Ubuntu", 10),
                highlightthickness=1,
                highlightcolor="#89b4fa",
                highlightbackground="#45475a",
            )
            time_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3, ipady=3)
            time_entry.insert(0, day_cfg.get("time_display", ""))
            self.comp_days_time[day_key] = time_entry

        self.update_competition_day_labels()

    def open_date_picker_for_entry(self, entry_widget: tk.Entry) -> None:
        """Open a calendar dialog and set a formatted display date in an entry widget."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Date")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#1e1e2e")

        current_date = datetime.now()

        cal = Calendar(
            dialog,
            selectmode="day",
            year=current_date.year,
            month=current_date.month,
            day=current_date.day,
            date_pattern="yyyy-mm-dd",
            background="#1e1e2e",
            foreground="#cdd6f4",
            headersbackground="#2a2a3c",
            headersforeground="#89b4fa",
            selectbackground="#89b4fa",
            selectforeground="#1e1e2e",
            normalbackground="#2a2a3c",
            normalforeground="#cdd6f4",
            weekendbackground="#2a2a3c",
            weekendforeground="#f5c2e7",
            othermonthbackground="#1e1e2e",
            othermonthforeground="#45475a",
            othermonthwebackground="#1e1e2e",
            othermonthweforeground="#45475a",
            bordercolor="#45475a",
            font=("Ubuntu", 11),
        )
        cal.pack(padx=15, pady=15)

        def on_select():
            date = datetime.strptime(cal.get_date(), "%Y-%m-%d")
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, format_date_display(date))
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg="#1e1e2e")
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame,
            text="Select",
            command=on_select,
            bg="#89b4fa",
            fg="#1e1e2e",
            font=("Ubuntu", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            bg="#2a2a3c",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.wait_window()

    def update_competition_day_labels(self) -> None:
        """Update the calculated-date labels on the Competition Days tab."""
        if not hasattr(self, "comp_days_date_labels"):
            return
        try:
            race_day = self.race_day_var.get().strip()
            if not race_day:
                return
            offsets = {name: int(e.get().strip()) for name, e in self.offset_entries.items()}
            dates = calculate_dates(race_day, offsets)
            key_map = {
                "track_setup": "track_setup",
                "team_training": "team_training",
                "qualification": "qualification",
                "race": "race",
            }
            for day_key, dates_key in key_map.items():
                if day_key in self.comp_days_date_labels and dates_key in dates:
                    self.comp_days_date_labels[day_key].config(
                        text=format_date_display(dates[dates_key])
                    )
        except Exception:
            pass

    def create_orientations_tab(self) -> None:
        """Create the Orientations tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Orientations")

        frame.columnconfigure(1, weight=1)

        # Info label
        row = 0
        ttk.Label(
            frame,
            text="Dates are calculated from the Dates & Timeline tab. Use Date Override to change (shows original strikethrough).",
            foreground="#a6adc8",
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # Orientation 1
        row += 1
        ttk.Label(frame, text="Orientation 1", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )

        o1 = self.config.get("orientation_1", {})

        row += 1
        ttk.Label(frame, text="Date (calculated):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.o1_date_label = ttk.Label(frame, text="(click 'Calculate Dates' in Dates tab)", foreground="#00bcd4")
        self.o1_date_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.o1_date_override_entry = self.create_labeled_entry(
            frame, "Date Override (e.g., May 10th):", row, o1.get("date_override", "")
        )
        row += 1
        self.o1_time_entry = self.create_labeled_entry(
            frame, "Time (e.g., 11:00AM - 12:00PM ET):", row, o1.get("time_display", "")
        )
        row += 1
        self.o1_zoom_entry = self.create_labeled_entry(
            frame, "Zoom Link:", row, o1.get("zoom_link", "")
        )
        row += 1
        self.o1_slides_entry = self.create_labeled_entry(
            frame, "Slides Link:", row, o1.get("slides_link", "")
        )
        row += 1
        self.o1_video_entry = self.create_labeled_entry(
            frame, "Video Link:", row, o1.get("video_link", "")
        )

        # Orientation 2
        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=15
        )
        row += 1
        ttk.Label(frame, text="Orientation 2", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )

        o2 = self.config.get("orientation_2", {})

        row += 1
        ttk.Label(frame, text="Date (calculated):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.o2_date_label = ttk.Label(frame, text="(click 'Calculate Dates' in Dates tab)", foreground="#00bcd4")
        self.o2_date_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.o2_date_override_entry = self.create_labeled_entry(
            frame, "Date Override (e.g., May 10th):", row, o2.get("date_override", "")
        )
        row += 1
        self.o2_time_entry = self.create_labeled_entry(
            frame, "Time (e.g., 11:00AM - 12:00PM ET):", row, o2.get("time_display", "")
        )
        row += 1
        self.o2_zoom_entry = self.create_labeled_entry(
            frame, "Zoom Link:", row, o2.get("zoom_link", "")
        )
        row += 1
        self.o2_slides_entry = self.create_labeled_entry(
            frame, "Slides Link:", row, o2.get("slides_link", "")
        )
        row += 1
        self.o2_video_entry = self.create_labeled_entry(
            frame, "Video Link:", row, o2.get("video_link", "")
        )

        # Update orientation dates on load
        self.update_orientation_dates()

    def create_registration_tab(self) -> None:
        """Create the Registration tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Registration")

        frame.columnconfigure(1, weight=1)

        reg = self.config.get("registration", {})

        row = 0
        ttk.Label(frame, text="Registration Status:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.reg_status_var = tk.StringVar(value=reg.get("status", "closed"))
        status_frame = ttk.Frame(frame)
        status_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(
            status_frame, text="Open", variable=self.reg_status_var, value="open"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            status_frame, text="Closed", variable=self.reg_status_var, value="closed"
        ).pack(side=tk.LEFT, padx=5)

        row += 1
        self.reg_form_entry = self.create_labeled_entry(
            frame, "Registration Form Link:", row, reg.get("form_link", "")
        )
        row += 1
        self.video_demo_form_entry = self.create_labeled_entry(
            frame, "Video Demo Submission Form:", row, reg.get("video_demo_form_link", "")
        )
        row += 1
        self.hardware_list_form_entry = self.create_labeled_entry(
            frame, "Hardware List Submission Form:", row, reg.get("hardware_list_form_link", "")
        )

        # Timeline date overrides
        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=15
        )
        row += 1
        ttk.Label(frame, text="Timeline Date Overrides", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )
        row += 1
        ttk.Label(
            frame,
            text="Dates are calculated from the Dates & Timeline tab. Use Date Override to change (shows original strikethrough).",
            foreground="#a6adc8",
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        row += 1
        ttk.Label(frame, text="Registration Opens (calculated):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.reg_open_date_label = ttk.Label(frame, text="(click 'Calculate Dates' in Dates tab)", foreground="#00bcd4")
        self.reg_open_date_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.reg_open_date_override_entry = self.create_labeled_entry(
            frame, "Date Override (e.g., March 10th):", row, reg.get("registration_open_date_override", "")
        )

        row += 1
        ttk.Label(frame, text="Registration Closes (calculated):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.reg_close_date_label = ttk.Label(frame, text="(click 'Calculate Dates' in Dates tab)", foreground="#00bcd4")
        self.reg_close_date_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.reg_close_date_override_entry = self.create_labeled_entry(
            frame, "Date Override (e.g., May 20th):", row, reg.get("registration_closes_date_override", "")
        )

        # Participants section
        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=15
        )
        row += 1
        ttk.Label(frame, text="Participants List", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )

        row += 1
        self.hide_participants_var = tk.BooleanVar(value=reg.get("hide_participants", False))
        ttk.Checkbutton(
            frame, text="Hide participants section on registration page", variable=self.hide_participants_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        row += 1
        participants_btn_frame = ttk.Frame(frame)
        participants_btn_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        ttk.Button(
            participants_btn_frame, text="Clear Participants", command=self.clear_participants
        ).pack(side=tk.LEFT, padx=5)

        # Sim Racing section
        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=15
        )
        row += 1
        ttk.Label(frame, text="Sim Racing League", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )

        sim = self.config.get("sim_racing", {})
        row += 1
        self.sim_enabled_var = tk.BooleanVar(value=sim.get("enabled", True))
        ttk.Checkbutton(
            frame, text="Enable Sim Racing Section", variable=self.sim_enabled_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.sim_edition_entry = self.create_labeled_entry(
            frame, "Edition (e.g., 3rd):", row, sim.get("edition", "")
        )
        row += 1
        self.sim_website_entry = self.create_labeled_entry(
            frame, "Website URL:", row, sim.get("website_url", "")
        )
        row += 1
        self.sim_registration_entry = self.create_labeled_entry(
            frame, "Registration URL:", row, sim.get("registration_url", "")
        )
        row += 1
        self.sim_timeline_entry = self.create_labeled_entry(
            frame, "Timeline URL:", row, sim.get("timeline_url", "")
        )

    def create_results_tab(self) -> None:
        """Create the Results/Stream tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Results & Stream")

        frame.columnconfigure(1, weight=1)

        results = self.config.get("results", {})

        # Stream section
        row = 0
        ttk.Label(frame, text="Live Stream", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )

        row += 1
        self.youtube_stream_entry = self.create_labeled_entry(
            frame, "YouTube Stream ID:", row, results.get("youtube_stream_id", "")
        )
        row += 1
        self.twitch_domains_entry = self.create_labeled_entry(
            frame,
            "Twitch Parent Domains (comma-separated):",
            row,
            ", ".join(results.get("twitch_parent_domains", [])),
        )

        row += 1
        self.show_stream_placeholder_var = tk.BooleanVar(value=results.get("show_stream_placeholder", True))
        ttk.Checkbutton(
            frame, text="Show placeholder text if stream not configured", variable=self.show_stream_placeholder_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.stream_placeholder_entry = self.create_labeled_entry(
            frame, "Stream Placeholder Text:", row, results.get("stream_placeholder_text", "Live stream will appear here during the event.")
        )

        # Results section
        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=15
        )
        row += 1
        ttk.Label(frame, text="Results", font=("Ubuntu", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10
        )

        row += 1
        self.time_trial_entry = self.create_labeled_entry(
            frame, "Time Trial Sheet Link:", row, results.get("time_trial_sheet_link", "")
        )
        row += 1
        ttk.Label(frame, text="", foreground="#a6adc8").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.hide_time_trial_info = ttk.Label(frame, text="(Leave empty to hide this section)", foreground="#a6adc8")
        self.hide_time_trial_info.grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        self.bracket_entry = self.create_labeled_entry(
            frame, "Head-to-Head Bracket Link:", row, results.get("bracket_link", "")
        )
        row += 1
        ttk.Label(frame, text="", foreground="#a6adc8").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.hide_bracket_info = ttk.Label(frame, text="(Leave empty to hide this section)", foreground="#a6adc8")
        self.hide_bracket_info.grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        self.bracket_embed_entry = self.create_labeled_entry(
            frame, "Bracket Embed URL (Challonge .../module):", row, results.get("bracket_embed_url", "")
        )
        row += 1
        ttk.Label(frame, text="", foreground="#a6adc8").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.hide_bracket_embed_info = ttk.Label(frame, text="(Leave empty to hide this section)", foreground="#a6adc8")
        self.hide_bracket_embed_info.grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        self.show_results_placeholder_var = tk.BooleanVar(value=results.get("show_results_placeholder", True))
        ttk.Checkbutton(
            frame, text="Show placeholder text for results section", variable=self.show_results_placeholder_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.results_placeholder_entry = self.create_labeled_entry(
            frame, "Results Placeholder Text:", row, results.get("results_placeholder_text", "Results will be posted after the competition.")
        )

    def create_organizers_tab(self) -> None:
        """Create the Organizers tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Organizers")

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Header label
        ttk.Label(
            frame,
            text="Manage event organizers (displayed on homepage):",
            font=("Ubuntu", 10),
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=(5, 10))

        # Treeview for organizers list
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("#", "Name", "Institution")
        self.organizers_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=12
        )
        self.organizers_tree.heading("#", text="#", anchor="w")
        self.organizers_tree.heading("Name", text="Name", anchor="w")
        self.organizers_tree.heading("Institution", text="Institution", anchor="w")
        self.organizers_tree.column("#", width=40, minwidth=30)
        self.organizers_tree.column("Name", width=200, minwidth=150)
        self.organizers_tree.column("Institution", width=300, minwidth=200)

        self.organizers_tree.grid(row=0, column=0, sticky=tk.NSEW)

        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.organizers_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.organizers_tree.configure(yscrollcommand=tree_scroll.set)

        # Double-click to edit
        self.organizers_tree.bind("<Double-1>", lambda e: self.edit_organizer())

        # Buttons frame
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, sticky=tk.W, padx=5, pady=10)

        ttk.Button(btn_frame, text="Add New", command=self.add_organizer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit Selected", command=self.edit_organizer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_organizer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Move Up", command=self.move_organizer_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Move Down", command=self.move_organizer_down).pack(side=tk.LEFT, padx=5)

        # Store organizers data
        self.organizers_data = self.config.get("organizers", []).copy()

        # Populate treeview
        self.refresh_organizers_tree()

    def refresh_organizers_tree(self) -> None:
        """Refresh the organizers treeview with current data."""
        self.organizers_tree.delete(*self.organizers_tree.get_children())
        for i, org in enumerate(self.organizers_data, 1):
            self.organizers_tree.insert("", tk.END, values=(i, org.get("name", ""), org.get("institution", "")))

    def add_organizer(self) -> None:
        """Open dialog to add a new organizer."""
        dialog = OrganizerEditDialog(self.root, "Add Organizer")
        if dialog.result:
            self.organizers_data.append(dialog.result)
            self.refresh_organizers_tree()

    def edit_organizer(self) -> None:
        """Open dialog to edit the selected organizer."""
        selection = self.organizers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an organizer to edit.")
            return

        item = selection[0]
        index = self.organizers_tree.index(item)
        organizer = self.organizers_data[index]

        dialog = OrganizerEditDialog(self.root, "Edit Organizer", organizer)
        if dialog.result:
            self.organizers_data[index] = dialog.result
            self.refresh_organizers_tree()

    def delete_organizer(self) -> None:
        """Delete the selected organizer."""
        selection = self.organizers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an organizer to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this organizer?"):
            item = selection[0]
            index = self.organizers_tree.index(item)
            del self.organizers_data[index]
            self.refresh_organizers_tree()

    def move_organizer_up(self) -> None:
        """Move the selected organizer up in the list."""
        selection = self.organizers_tree.selection()
        if not selection:
            return

        item = selection[0]
        index = self.organizers_tree.index(item)
        if index > 0:
            self.organizers_data[index], self.organizers_data[index - 1] = (
                self.organizers_data[index - 1],
                self.organizers_data[index],
            )
            self.refresh_organizers_tree()
            # Reselect the moved item
            children = self.organizers_tree.get_children()
            self.organizers_tree.selection_set(children[index - 1])

    def move_organizer_down(self) -> None:
        """Move the selected organizer down in the list."""
        selection = self.organizers_tree.selection()
        if not selection:
            return

        item = selection[0]
        index = self.organizers_tree.index(item)
        if index < len(self.organizers_data) - 1:
            self.organizers_data[index], self.organizers_data[index + 1] = (
                self.organizers_data[index + 1],
                self.organizers_data[index],
            )
            self.refresh_organizers_tree()
            # Reselect the moved item
            children = self.organizers_tree.get_children()
            self.organizers_tree.selection_set(children[index + 1])

    # ------------------------------------------------------------------
    # Certification tab
    # ------------------------------------------------------------------

    # Filename globs used to auto-locate the three Form CSV exports.
    CERT_FILE_GLOBS = {
        cert.FORM_REGISTRATION: "*Registration*Form Responses.csv",
        cert.FORM_VIDEO: "*VideoSubmission*Form Responses.csv",
        cert.FORM_HARDWARE: "*HardwareList*Form Responses.csv",
    }
    CERT_FORM_LABELS = {
        cert.FORM_REGISTRATION: "Registration CSV",
        cert.FORM_VIDEO: "Video Submission CSV",
        cert.FORM_HARDWARE: "Hardware List CSV",
    }
    CERT_BADGE_COLORS = {
        cert.LINK_OK: "#a6e3a1",
        cert.LINK_SUSPICIOUS: "#f9e2af",
        cert.LINK_BLOCKED: "#f38ba8",
        cert.LINK_NONE: "#a6adc8",
    }

    def _cert_default_path(self, form: str) -> str:
        """Return saved CSV path for a form, or auto-detect one in Utils/."""
        saved = self.certification_data.get("csv_paths", {}).get(form, "")
        if saved and Path(saved).exists():
            return saved
        matches = sorted(SCRIPT_DIR.glob(self.CERT_FILE_GLOBS[form]))
        return str(matches[0]) if matches else ""

    def create_registrants_tab(self) -> None:
        """Create the Certification tab (3-CSV matching + certification)."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Certification")

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=2)
        frame.rowconfigure(4, weight=1)

        # --- File pickers ---------------------------------------------
        files_frame = ttk.LabelFrame(frame, text="Form responses (CSV)", padding=8)
        files_frame.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=(0, 8))
        files_frame.columnconfigure(1, weight=1)

        self.cert_path_vars: dict[str, tk.StringVar] = {}
        for i, form in enumerate(
            (cert.FORM_REGISTRATION, cert.FORM_VIDEO, cert.FORM_HARDWARE)
        ):
            ttk.Label(files_frame, text=self.CERT_FORM_LABELS[form] + ":").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.StringVar(value=self._cert_default_path(form))
            self.cert_path_vars[form] = var
            ttk.Entry(files_frame, textvariable=var).grid(
                row=i, column=1, sticky=tk.EW, padx=5, pady=3
            )
            ttk.Button(
                files_frame,
                text="Browse",
                command=lambda f=form: self.browse_cert_file(f),
            ).grid(row=i, column=2, padx=5, pady=3)

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=1, column=0, sticky=tk.EW, padx=5, pady=(0, 6))
        ttk.Button(
            action_frame,
            text="Process / Reprocess",
            command=self.process_certification,
            style="Accent.TButton",
        ).pack(side=tk.LEFT)
        ttk.Button(
            action_frame, text="Add Manual Team", command=self.cert_add_manual_team
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            action_frame, text="Export Emails...", command=self.cert_export_emails
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            action_frame, text="Email Settings...", command=self.cert_email_settings
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.cert_status_label = ttk.Label(action_frame, text="Not processed yet.")
        self.cert_status_label.pack(side=tk.LEFT, padx=12)

        # --- Candidate teams tree -------------------------------------
        cand_frame = ttk.LabelFrame(
            frame, text="Candidate teams (submitted video AND hardware)", padding=4
        )
        cand_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=5, pady=4)
        cand_frame.columnconfigure(0, weight=1)
        cand_frame.rowconfigure(0, weight=1)

        cols = ("team", "affiliation", "reg", "video", "hardware", "certified")
        headers = {
            "team": "Team",
            "affiliation": "Affiliation",
            "reg": "Registered",
            "video": "Video",
            "hardware": "Hardware",
            "certified": "Certified",
        }
        widths = {
            "team": 180,
            "affiliation": 200,
            "reg": 80,
            "video": 110,
            "hardware": 110,
            "certified": 80,
        }
        self.cert_tree = ttk.Treeview(
            cand_frame, columns=cols, show="headings", height=9, selectmode="browse"
        )
        for c in cols:
            self.cert_tree.heading(c, text=headers[c])
            self.cert_tree.column(c, width=self.px(widths[c]), anchor=tk.W)
        self.cert_tree.tag_configure("unmatched", foreground="#f9e2af")
        self.cert_tree.tag_configure("certified", foreground="#a6e3a1")
        self.cert_tree.grid(row=0, column=0, sticky=tk.NSEW)
        cand_scroll = ttk.Scrollbar(cand_frame, command=self.cert_tree.yview)
        cand_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.cert_tree.config(yscrollcommand=cand_scroll.set)
        self.cert_tree.bind("<<TreeviewSelect>>", self.on_cert_tree_select)

        # --- Detail panel ---------------------------------------------
        detail = ttk.LabelFrame(frame, text="Selected team", padding=6)
        detail.grid(row=3, column=0, sticky=tk.EW, padx=5, pady=4)
        detail.columnconfigure(0, weight=1)
        detail.columnconfigure(1, weight=1)

        self.cert_team_label = ttk.Label(
            detail, text="Select a team above.", style="Header.TLabel"
        )
        self.cert_team_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

        self.cert_blocks: dict[str, dict] = {}
        self._build_submission_block(detail, cert.FORM_VIDEO, "Video Demo", col=0)
        self._build_submission_block(detail, cert.FORM_HARDWARE, "Hardware List", col=1)

        # Members + email actions (span both columns).
        extra = ttk.Frame(detail)
        extra.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))
        extra.columnconfigure(0, weight=1)
        extra.columnconfigure(1, weight=1)

        members_box = ttk.LabelFrame(extra, text="Team members", padding=6)
        members_box.grid(row=0, column=0, sticky=tk.NSEW, padx=4)
        members_box.columnconfigure(0, weight=1)
        self.cert_members_list = tk.Listbox(
            members_box, height=5, bg="#2a2a3c", fg="#cdd6f4",
            selectbackground="#89b4fa", selectforeground="#1e1e2e",
            relief=tk.FLAT, highlightthickness=1, highlightbackground="#45475a",
            font=("Ubuntu", 10),
        )
        self.cert_members_list.grid(row=0, column=0, sticky=tk.EW)
        ml_scroll = ttk.Scrollbar(members_box, command=self.cert_members_list.yview)
        ml_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.cert_members_list.config(yscrollcommand=ml_scroll.set)
        m_btns = ttk.Frame(members_box)
        m_btns.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))
        ttk.Button(m_btns, text="Add member", command=self.cert_add_member).pack(side=tk.LEFT)
        ttk.Button(m_btns, text="Remove member", command=self.cert_remove_member).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        email_box = ttk.LabelFrame(extra, text="Registration email to team leader", padding=6)
        email_box.grid(row=0, column=1, sticky=tk.NSEW, padx=4)
        email_box.columnconfigure(0, weight=1)
        self.cert_email_info = ttk.Label(
            email_box, text="", foreground="#a6adc8", wraplength=380, justify=tk.LEFT
        )
        self.cert_email_info.grid(row=0, column=0, sticky=tk.W)
        e_btns = ttk.Frame(email_box)
        e_btns.grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.cert_email_btn = ttk.Button(
            e_btns, text="Compose Email", command=self.cert_compose_email
        )
        self.cert_email_btn.pack(side=tk.LEFT)
        self.cert_remove_manual_btn = ttk.Button(
            e_btns, text="Remove Manual Team", command=self.cert_remove_manual_team,
            state="disabled",
        )
        self.cert_remove_manual_btn.pack(side=tk.LEFT, padx=(6, 0))

        # --- Not considered list --------------------------------------
        nc_frame = ttk.LabelFrame(
            frame, text="Not considered (missing video or hardware)", padding=4
        )
        nc_frame.grid(row=4, column=0, sticky=tk.NSEW, padx=5, pady=(4, 0))
        nc_frame.columnconfigure(0, weight=1)
        nc_frame.rowconfigure(0, weight=1)
        nc_cols = ("team", "reg", "video", "hardware")
        self.cert_nc_tree = ttk.Treeview(
            nc_frame, columns=nc_cols, show="headings", height=5
        )
        for c, h, w in (
            ("team", "Team", 220),
            ("reg", "Registered", 90),
            ("video", "Video", 90),
            ("hardware", "Hardware", 90),
        ):
            self.cert_nc_tree.heading(c, text=h)
            self.cert_nc_tree.column(c, width=self.px(w), anchor=tk.W)
        self.cert_nc_tree.grid(row=0, column=0, sticky=tk.NSEW)
        nc_scroll = ttk.Scrollbar(nc_frame, command=self.cert_nc_tree.yview)
        nc_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.cert_nc_tree.config(yscrollcommand=nc_scroll.set)
        self.cert_nc_tree.bind("<<TreeviewSelect>>", self.on_cert_nc_select)

        self.cert_selected_key: str | None = None

        # Auto-process if all three files are available.
        if all(self.cert_path_vars[f].get() for f in self.cert_path_vars):
            self.process_certification(silent=True)

    def _build_submission_block(
        self, parent: ttk.Frame, form: str, title: str, col: int
    ) -> None:
        """Build the per-form (video/hardware) detail widgets."""
        box = ttk.LabelFrame(parent, text=title, padding=6)
        box.grid(row=1, column=col, sticky=tk.NSEW, padx=4, pady=4)
        box.columnconfigure(0, weight=1)

        satisfied_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(
            box,
            text=f"{title} satisfied (hand-checked)",
            variable=satisfied_var,
            command=lambda f=form: self.cert_toggle_satisfied(f),
        )
        chk.grid(row=0, column=0, sticky=tk.W, pady=(0, 4))

        ttk.Label(box, text="Submission (latest first):").grid(
            row=1, column=0, sticky=tk.W
        )
        combo = ttk.Combobox(box, state="readonly", values=[])
        combo.grid(row=2, column=0, sticky=tk.EW, pady=2)
        combo.bind("<<ComboboxSelected>>", lambda e, f=form: self._refresh_block_link(f))

        info = ttk.Label(box, text="", foreground="#a6adc8")
        info.grid(row=3, column=0, sticky=tk.W, pady=2)

        ttk.Label(box, text="Submitted link (verify before opening):").grid(
            row=4, column=0, sticky=tk.W
        )
        url_entry = ttk.Entry(box)
        url_entry.grid(row=5, column=0, sticky=tk.EW, pady=2)

        badge = tk.Label(box, text="", anchor=tk.W, bg="#1e1e2e")
        badge.grid(row=6, column=0, sticky=tk.EW, pady=2)

        btns = ttk.Frame(box)
        btns.grid(row=7, column=0, sticky=tk.W, pady=2)
        open_btn = ttk.Button(
            btns, text="Open Link", command=lambda f=form: self.cert_open_link(f)
        )
        open_btn.pack(side=tk.LEFT, padx=(0, 4))
        mark_btn = ttk.Button(
            btns, text="Mark malicious", command=lambda f=form: self.cert_toggle_malicious(f)
        )
        mark_btn.pack(side=tk.LEFT, padx=4)
        ignore_btn = ttk.Button(
            btns, text="Ignore submission", command=lambda f=form: self.cert_ignore_submission(f)
        )
        ignore_btn.pack(side=tk.LEFT, padx=4)

        ttk.Label(box, text="Manually link this submission to registration:").grid(
            row=8, column=0, sticky=tk.W, pady=(6, 0)
        )
        link_combo = ttk.Combobox(box, state="readonly", values=[])
        link_combo.grid(row=9, column=0, sticky=tk.EW, pady=2)
        ttk.Button(
            box, text="Apply link", command=lambda f=form: self.cert_apply_manual_link(f)
        ).grid(row=10, column=0, sticky=tk.W, pady=2)

        self.cert_blocks[form] = {
            "satisfied_var": satisfied_var,
            "satisfied_chk": chk,
            "combo": combo,
            "info": info,
            "url_entry": url_entry,
            "badge": badge,
            "open_btn": open_btn,
            "mark_btn": mark_btn,
            "ignore_btn": ignore_btn,
            "link_combo": link_combo,
            "subs": [],  # submissions for the current team, latest first
        }

    # ---- Certification helpers ---------------------------------------

    def browse_cert_file(self, form: str) -> None:
        filename = filedialog.askopenfilename(
            title=f"Select {self.CERT_FORM_LABELS[form]}",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=SCRIPT_DIR,
        )
        if filename:
            self.cert_path_vars[form].set(filename)

    @property
    def _cert_overrides(self) -> dict:
        ov = self.certification_data.setdefault("overrides", {})
        ov.setdefault("submission_links", {})
        ov.setdefault("ignored_submissions", [])
        ov.setdefault("blocked_links", [])
        ov.setdefault("allowed_links", [])
        return ov

    def process_certification(self, silent: bool = False) -> None:
        """Load the three CSVs, run matching, and refresh the views."""
        paths = {f: self.cert_path_vars[f].get().strip() for f in self.cert_path_vars}
        missing = [self.CERT_FORM_LABELS[f] for f, p in paths.items() if not p or not Path(p).exists()]
        if missing:
            if not silent:
                messagebox.showwarning(
                    "Missing files",
                    "Select valid files for:\n- " + "\n- ".join(missing),
                )
            return
        try:
            regs = cert.load_registrations(paths[cert.FORM_REGISTRATION])
            videos = cert.load_video_submissions(paths[cert.FORM_VIDEO])
            hardware = cert.load_hardware_submissions(paths[cert.FORM_HARDWARE])
            self.cert_registrations = regs
            self.cert_teams = cert.build_teams(
                regs,
                videos,
                hardware,
                overrides=self._cert_overrides,
                ticks=self.certification_data.get("ticks", {}),
                member_overrides=self.certification_data.get("member_overrides", {}),
                manual_teams=self.certification_data.get("manual_teams", []),
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process CSVs: {e}")
            return

        # Persist the resolved paths.
        self.certification_data["csv_paths"] = paths
        self.refresh_cert_trees()
        n_cand = sum(1 for t in self.cert_teams if t.is_candidate)
        n_cert = sum(1 for t in self.cert_teams if t.certified)
        self.cert_status_label.config(
            text=f"{len(regs)} regs, {len(videos)} videos, {len(hardware)} hardware - "
            f"{n_cand} candidates, {n_cert} certified."
        )

    def _team_by_key(self, key: str):
        for t in self.cert_teams:
            if t.team_key == key:
                return t
        return None

    def refresh_cert_trees(self) -> None:
        prev = self.cert_tree.selection()
        prev_key = prev[0] if prev else None
        self.cert_tree.delete(*self.cert_tree.get_children())
        self.cert_nc_tree.delete(*self.cert_nc_tree.get_children())

        def yn(v: bool) -> str:
            return "Yes" if v else "No"

        for t in self.cert_teams:
            if t.is_candidate:
                tags = []
                if t.certified:
                    tags.append("certified")
                elif not t.registration_matched:
                    tags.append("unmatched")
                self.cert_tree.insert(
                    "", tk.END, iid=t.team_key,
                    values=(
                        t.display_name,
                        t.affiliation,
                        yn(t.registration_matched),
                        "satisfied" if t.video_satisfied else "submitted",
                        "satisfied" if t.hardware_satisfied else "submitted",
                        yn(t.certified),
                    ),
                    tags=tags,
                )
            else:
                self.cert_nc_tree.insert(
                    "", tk.END, iid=t.team_key,
                    values=(
                        t.display_name,
                        yn(t.registration_matched),
                        yn(t.has_video),
                        yn(t.has_hardware),
                    ),
                )

        key = self.cert_selected_key if hasattr(self, "cert_selected_key") else None
        if key and self.cert_tree.exists(key):
            self.cert_tree.selection_set(key)
        elif key and self.cert_nc_tree.exists(key):
            self.cert_nc_tree.selection_set(key)
        elif prev_key and self.cert_tree.exists(prev_key):
            self.cert_tree.selection_set(prev_key)
        else:
            self._clear_detail()

    def _clear_detail(self) -> None:
        self.cert_team_label.config(text="Select a team above.")
        for form in self.cert_blocks:
            b = self.cert_blocks[form]
            b["subs"] = []
            b["combo"]["values"] = []
            b["combo"].set("")
            b["link_combo"]["values"] = []
            b["link_combo"].set("")
            b["info"].config(text="")
            self._set_entry(b["url_entry"], "")
            b["badge"].config(text="", bg="#1e1e2e")
            b["satisfied_var"].set(False)
        if hasattr(self, "cert_members_list"):
            self.cert_members_list.delete(0, tk.END)
            self.cert_email_info.config(text="")
            self.cert_remove_manual_btn.config(state="disabled")

    @staticmethod
    def _set_entry(entry: ttk.Entry, text: str) -> None:
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, text)
        entry.config(state="readonly")

    def on_cert_tree_select(self, event=None) -> None:
        sel = self.cert_tree.selection()
        if not sel:
            return
        self.cert_nc_tree.selection_remove(self.cert_nc_tree.selection())
        self._select_team(sel[0])

    def on_cert_nc_select(self, event=None) -> None:
        sel = self.cert_nc_tree.selection()
        if not sel:
            return
        self.cert_tree.selection_remove(self.cert_tree.selection())
        self._select_team(sel[0])

    def _select_team(self, key: str) -> None:
        team = self._team_by_key(key)
        if not team:
            return
        self.cert_selected_key = key
        manual_tag = " [manual]" if team.manual else ""
        self.cert_team_label.config(
            text=f"{team.display_name}{manual_tag}   |   {team.affiliation or 'no affiliation'}   |   "
            f"{'registered' if team.registration_matched else 'NOT MATCHED to a registration'}"
        )
        reg_names = [r.display_name for r in getattr(self, "cert_registrations", [])]
        for form, subs in (
            (cert.FORM_VIDEO, team.all_video),
            (cert.FORM_HARDWARE, team.all_hardware),
        ):
            b = self.cert_blocks[form]
            ordered = sorted(
                subs, key=lambda s: (s.timestamp or datetime.min), reverse=True
            )
            b["subs"] = ordered
            b["combo"]["values"] = [self._sub_label(s) for s in ordered]
            if ordered:
                b["combo"].current(0)
            else:
                b["combo"].set("")
            b["link_combo"]["values"] = reg_names
            b["link_combo"].set("")
            satisfied = (
                team.video_satisfied if form == cert.FORM_VIDEO else team.hardware_satisfied
            )
            b["satisfied_var"].set(satisfied)
            # Only allow ticking when there is a submission to check (or manual team).
            has_sub = bool(ordered)
            b["satisfied_chk"].config(
                state=("normal" if (has_sub or team.manual) else "disabled")
            )
            self._refresh_block_link(form)
        self._refresh_members(team)
        self._refresh_email_info(team)

    def _refresh_members(self, team) -> None:
        self.cert_members_list.delete(0, tk.END)
        for name, email in team.members:
            label = name or "(no name)"
            if email:
                label += f"  <{email}>"
            self.cert_members_list.insert(tk.END, label)
        self.cert_remove_manual_btn.config(
            state=("normal" if team.manual else "disabled")
        )

    def _refresh_email_info(self, team) -> None:
        st = cert.requirement_status(team)
        kind = "CONFIRMATION" if all(v == cert.REQ_CONFIRMED for v in st.values()) else "REMINDER"
        to = team.leader_email or "(no leader email on file)"
        self.cert_email_info.config(
            text=f"To: {to}\nType: {kind}\n"
            f"registration={st['registration']}, video={st['video']}, hardware={st['hardware']}"
        )

    def _sub_label(self, sub) -> str:
        ts = sub.timestamp.strftime("%Y-%m-%d %H:%M") if sub.timestamp else "no date"
        return f"{ts} - {sub.submitter_name or sub.submitter_email or '?'}"

    def _selected_sub(self, form: str):
        b = self.cert_blocks[form]
        idx = b["combo"].current()
        if idx < 0 or idx >= len(b["subs"]):
            return None
        return b["subs"][idx]

    def _refresh_block_link(self, form: str) -> None:
        b = self.cert_blocks[form]
        sub = self._selected_sub(form)
        if not sub:
            b["info"].config(text="No submission.")
            self._set_entry(b["url_entry"], "")
            b["badge"].config(text="", bg="#1e1e2e")
            return
        b["info"].config(
            text=f"by {sub.submitter_name} <{sub.submitter_email}> - team as submitted: "
            f"\"{sub.team_name}\"  ({sub.match_reason})"
        )
        display = sub.primary_link or sub.raw_cell
        self._set_entry(b["url_entry"], display)
        ov = self._cert_overrides
        status, reasons = sub.link_status(
            set(ov["blocked_links"]), set(ov["allowed_links"])
        )
        color = self.CERT_BADGE_COLORS.get(status, "#a6adc8")
        b["badge"].config(text=f"  {status.upper()}: {'; '.join(reasons)}", fg="#11111b", bg=color)
        # Open disabled for blocked / no-link.
        b["open_btn"].config(
            state=("disabled" if status in (cert.LINK_BLOCKED, cert.LINK_NONE) else "normal")
        )
        marked = sub.primary_link in ov["blocked_links"]
        b["mark_btn"].config(text="Unmark malicious" if marked else "Mark malicious")

    def cert_open_link(self, form: str) -> None:
        sub = self._selected_sub(form)
        if not sub or not sub.primary_link:
            return
        url = sub.primary_link
        if messagebox.askyesno(
            "Open external link?",
            f"About to open this link in your browser:\n\n{url}\n\nProceed?",
        ):
            webbrowser.open(url)

    def cert_toggle_malicious(self, form: str) -> None:
        sub = self._selected_sub(form)
        if not sub or not sub.primary_link:
            return
        url = sub.primary_link
        blocked = self._cert_overrides["blocked_links"]
        if url in blocked:
            blocked.remove(url)
        else:
            blocked.append(url)
        self._refresh_block_link(form)

    def cert_ignore_submission(self, form: str) -> None:
        sub = self._selected_sub(form)
        if not sub:
            return
        if not messagebox.askyesno(
            "Ignore submission",
            "Mark this submission as redundant/ignored? It will be removed from "
            "consideration (the next-latest submission, if any, takes over).",
        ):
            return
        self._cert_overrides["ignored_submissions"].append(sub.submission_id)
        self.process_certification(silent=True)

    def _selected_team(self):
        return self._team_by_key(self.cert_selected_key) if self.cert_selected_key else None

    def cert_toggle_satisfied(self, form: str) -> None:
        team = self._selected_team()
        if not team:
            return
        ticks = self.certification_data.setdefault("ticks", {})
        entry = ticks.setdefault(
            team.team_key, {"video_satisfied": False, "hardware_satisfied": False}
        )
        val = self.cert_blocks[form]["satisfied_var"].get()
        key = "video_satisfied" if form == cert.FORM_VIDEO else "hardware_satisfied"
        entry[key] = val
        if form == cert.FORM_VIDEO:
            team.video_satisfied = val
        else:
            team.hardware_satisfied = val
        self.refresh_cert_trees()
        self._refresh_email_info(team)

    def cert_apply_manual_link(self, form: str) -> None:
        sub = self._selected_sub(form)
        if not sub:
            return
        choice = self.cert_blocks[form]["link_combo"].get()
        if not choice:
            messagebox.showinfo("Manual link", "Pick a registration first.")
            return
        reg = next(
            (r for r in getattr(self, "cert_registrations", []) if r.display_name == choice),
            None,
        )
        if not reg:
            return
        self._cert_overrides["submission_links"][sub.submission_id] = reg.team_key
        self.cert_selected_key = reg.team_key
        self.process_certification(silent=True)

    # ---- Team members --------------------------------------------------

    def cert_add_member(self) -> None:
        team = self._selected_team()
        if not team:
            messagebox.showinfo("Add member", "Select a team first.")
            return
        result = self._prompt_form(
            "Add team member",
            [("Name", "name", "", False), ("Email", "email", "", False)],
        )
        if not result:
            return
        name, email = result["name"].strip(), result["email"].strip()
        if not name and not email:
            return
        edits = self.certification_data.setdefault("member_overrides", {})
        entry = edits.setdefault(team.team_key, {"added": [], "removed": []})
        entry.setdefault("added", []).append([name, email])
        # In case this name/email was previously removed, un-remove it.
        rem = entry.setdefault("removed", [])
        for tok in (name.lower(), email.lower()):
            if tok and tok in rem:
                rem.remove(tok)
        self.process_certification(silent=True)

    def cert_remove_member(self) -> None:
        team = self._selected_team()
        if not team:
            return
        sel = self.cert_members_list.curselection()
        if not sel:
            messagebox.showinfo("Remove member", "Select a member in the list first.")
            return
        idx = sel[0]
        if idx >= len(team.members):
            return
        name, email = team.members[idx]
        edits = self.certification_data.setdefault("member_overrides", {})
        entry = edits.setdefault(team.team_key, {"added": [], "removed": []})
        added = entry.setdefault("added", [])
        # If this was a manually-added member, just drop it from "added".
        match_idx = next(
            (i for i, m in enumerate(added)
             if (m[0] or "").strip().lower() == name.strip().lower()
             and (m[1] if len(m) > 1 else "").strip().lower() == (email or "").strip().lower()),
            None,
        )
        if match_idx is not None:
            added.pop(match_idx)
        else:
            token = email.strip().lower() or name.strip().lower()
            if token:
                entry.setdefault("removed", []).append(token)
        self.process_certification(silent=True)

    # ---- Manual teams --------------------------------------------------

    def cert_add_manual_team(self) -> None:
        result = self._prompt_form(
            "Add manual team",
            [
                ("Team name", "name", "", False),
                ("Affiliation", "affiliation", "", False),
                ("Team leader email", "leader_email", "", False),
                ("Team leader name", "leader_name", "", False),
                ("Members (Name (email), one per line)", "members", "", True),
            ],
        )
        if not result:
            return
        name = result["name"].strip()
        if not name:
            messagebox.showwarning("Add manual team", "A team name is required.")
            return
        team_key = cert.normalize_team_name(name)
        members = cert.parse_member_lines(result["members"])
        # Always include the leader as a member if provided.
        leader_name = result["leader_name"].strip()
        leader_email = result["leader_email"].strip()
        if leader_name or leader_email:
            members = [(leader_name, leader_email)] + members
        manual = self.certification_data.setdefault("manual_teams", [])
        if any(m["team_key"] == team_key for m in manual):
            messagebox.showwarning(
                "Add manual team", f"A team with key '{team_key}' already exists."
            )
            return
        manual.append({
            "team_key": team_key,
            "display_name": name,
            "affiliation": result["affiliation"].strip(),
            "leader_name": leader_name,
            "leader_email": leader_email,
            "members": [list(m) for m in members],
        })
        # Manual teams default to certified (you are vouching for them).
        self.certification_data.setdefault("ticks", {})[team_key] = {
            "video_satisfied": True, "hardware_satisfied": True
        }
        self.cert_selected_key = team_key
        self.process_certification(silent=True)

    def cert_remove_manual_team(self) -> None:
        team = self._selected_team()
        if not team or not team.manual:
            return
        if not messagebox.askyesno(
            "Remove manual team", f"Remove manually-added team '{team.display_name}'?"
        ):
            return
        manual = self.certification_data.setdefault("manual_teams", [])
        self.certification_data["manual_teams"] = [
            m for m in manual if m["team_key"] != team.team_key
        ]
        self.certification_data.get("ticks", {}).pop(team.team_key, None)
        self.certification_data.get("member_overrides", {}).pop(team.team_key, None)
        self.cert_selected_key = None
        self.process_certification(silent=True)

    # ---- Emails --------------------------------------------------------

    def _email_context(self) -> dict:
        """Assemble the email template context from config + email settings."""
        cfg = self.collect_config()
        ev = cfg.get("event", {})
        reg = cfg.get("registration", {})
        em = self.certification_data.get("email", {})
        acronym = ev.get("conference_name", "").strip()
        year = ev.get("year", "").strip()
        conf_label = " ".join(p for p in (acronym, year) if p)
        event_name = " ".join(p for p in ("Roboracer", acronym, year) if p) or "Roboracer"
        competition = (f"{conf_label} RoboRacer Competition").strip() or "RoboRacer Competition"
        return {
            "event_name": event_name,
            "competition_name": competition,
            "conf_label": conf_label or "conference",
            "contact_email": ev.get("contact_email", ""),
            "signature": em.get("signature", "RoboRacer Organizing Team"),
            "conf_reg_url": em.get("conference_registration_url", ""),
            "conf_reg_note": em.get("conference_registration_note", ""),
            "confirmation_extra": em.get("confirmation_extra", ""),
            "reminder_extra": em.get("reminder_extra", ""),
            "video_form": reg.get("video_demo_form_link", ""),
            "hardware_form": reg.get("hardware_list_form_link", ""),
            "reg_form": reg.get("form_link", ""),
        }

    def cert_email_settings(self) -> None:
        """Edit the email template settings (signature, conf-reg link, extras)."""
        em = self.certification_data.setdefault("email", {})
        result = self._prompt_form(
            "Email settings",
            [
                ("Signature", "signature",
                 em.get("signature", "RoboRacer Organizing Team"), False),
                ("Conference registration URL", "conference_registration_url",
                 em.get("conference_registration_url", ""), False),
                ("Conference registration note (e.g. dedicated category text)",
                 "conference_registration_note",
                 em.get("conference_registration_note", ""), True),
                ("Confirmation email extra (prize pool, stipend, ...)",
                 "confirmation_extra", em.get("confirmation_extra", ""), True),
                ("Reminder email extra", "reminder_extra",
                 em.get("reminder_extra", ""), True),
            ],
        )
        if not result:
            return
        for key in (
            "signature", "conference_registration_url",
            "conference_registration_note", "confirmation_extra", "reminder_extra",
        ):
            em[key] = result[key]
        messagebox.showinfo("Email settings", "Email settings updated (remember to Save).")

    def cert_compose_email(self) -> None:
        team = self._selected_team()
        if not team:
            messagebox.showinfo("Compose email", "Select a team first.")
            return
        if not team.leader_email:
            messagebox.showwarning(
                "Compose email",
                "This team has no team-leader email on file (it isn't matched to a "
                "registration). Add a manual team or link it to a registration first.",
            )
            return
        ctx = self._email_context()
        email = cert.build_email(team, ctx)
        preview = (
            f"To: {email['to']}\nSubject: {email['subject']}\n\n{email['body']}\n\n"
            f"Open this in your email client now?"
        )
        if messagebox.askyesno(f"Send {email['kind']} email?", preview):
            webbrowser.open(
                cert.mailto_url(email["to"], email["subject"], email["body"])
            )

    def cert_export_emails(self) -> None:
        if not self.cert_teams:
            messagebox.showinfo("Export emails", "Process the CSVs first.")
            return
        targets = [
            t for t in self.cert_teams if t.registration_matched and t.leader_email
        ]
        if not targets:
            messagebox.showinfo("Export emails", "No teams with a leader email to write.")
            return
        directory = filedialog.askdirectory(
            title="Choose a folder to write .eml files into", initialdir=SCRIPT_DIR
        )
        if not directory:
            return
        ctx = self._email_context()
        sender = ctx["contact_email"] or "roboracer@example.com"
        n_confirm = n_remind = 0
        for team in targets:
            email = cert.build_email(team, ctx)
            safe = re.sub(r"[^a-z0-9]+", "_", team.team_key).strip("_") or "team"
            fname = f"{email['kind']}_{safe}.eml"
            with open(Path(directory) / fname, "w", encoding="utf-8") as f:
                f.write(cert.to_eml(email, sender))
            if email["kind"] == "confirm":
                n_confirm += 1
            else:
                n_remind += 1
        messagebox.showinfo(
            "Export emails",
            f"Wrote {len(targets)} .eml files to:\n{directory}\n\n"
            f"  {n_confirm} confirmation(s), {n_remind} reminder(s).\n\n"
            "Open them in your mail client to review and send.",
        )

    # ---- Generic modal form dialog ------------------------------------

    def _prompt_form(self, title: str, fields: list[tuple]) -> dict | None:
        """Show a modal form. fields: list of (label, key, default, kind).

        ``kind`` is False for a single-line entry, True for a multi-line text box,
        or a list of strings for an (editable) dropdown of choices.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg="#1e1e2e")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(1, weight=1)

        widgets: dict[str, tuple] = {}
        for i, (label, key, default, kind) in enumerate(fields):
            ttk.Label(dialog, text=label + ":").grid(
                row=i, column=0, sticky=tk.NW, padx=8, pady=6
            )
            if isinstance(kind, (list, tuple)):
                w = ttk.Combobox(dialog, values=list(kind), width=42)
                w.set(default)
                widgets[key] = (w, "combo")
            elif kind:
                w = tk.Text(dialog, width=44, height=5, bg="#2a2a3c", fg="#cdd6f4",
                            insertbackground="#cdd6f4", relief=tk.FLAT,
                            highlightthickness=1, highlightbackground="#45475a",
                            font=("Ubuntu", 10))
                w.insert("1.0", default)
                widgets[key] = (w, "text")
            else:
                w = tk.Entry(dialog, width=44, bg="#2a2a3c", fg="#cdd6f4",
                             insertbackground="#cdd6f4", relief=tk.FLAT,
                             highlightthickness=1, highlightbackground="#45475a",
                             font=("Ubuntu", 10))
                w.insert(0, default)
                widgets[key] = (w, "entry")
            w.grid(row=i, column=1, sticky=tk.EW, padx=8, pady=6)

        result: dict = {}

        def on_ok():
            for k, (w, kind) in widgets.items():
                result[k] = w.get("1.0", tk.END).rstrip("\n") if kind == "text" else w.get()
            result["_ok"] = True
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="OK", command=on_ok, style="Accent.TButton").pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=4)

        self._scale_widget_fonts(dialog)
        self.root.wait_window(dialog)
        return result if result.get("_ok") else None

    # ------------------------------------------------------------------
    # Schedule tab
    # ------------------------------------------------------------------

    def create_schedule_tab(self) -> None:
        """Create the Schedule tab (groups + CSV import + booking-grid export)."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Schedule")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)  # groups list
        frame.rowconfigure(6, weight=2)  # preview

        # --- Settings -------------------------------------------------
        settings = ttk.LabelFrame(frame, text="Schedule settings", padding=8)
        settings.grid(row=0, column=0, sticky=tk.EW, pady=(0, 6))
        ttk.Label(settings, text="Timezone label:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.sched_tz_var = tk.StringVar(value=self.schedule_data.get("timezone_label", "ET"))
        ttk.Entry(settings, textvariable=self.sched_tz_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(settings, text="Teams per group:").grid(row=0, column=2, sticky=tk.W, padx=(15, 5))
        self.sched_group_size_var = tk.StringVar(value=str(self.schedule_data.get("group_size", 4)))
        ttk.Entry(settings, textvariable=self.sched_group_size_var, width=5).grid(row=0, column=3, padx=5)
        ttk.Button(settings, text="Auto-assign groups", command=self.sched_auto_assign).grid(
            row=0, column=4, padx=(15, 5)
        )

        # --- Schedule CSV ---------------------------------------------
        csv_frame = ttk.LabelFrame(frame, text="Schedule sheet (CSV exported from Google Sheets)", padding=8)
        csv_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 6))
        csv_frame.columnconfigure(0, weight=1)
        self.sched_csv_var = tk.StringVar(value=self.schedule_data.get("csv_path", ""))
        ttk.Entry(csv_frame, textvariable=self.sched_csv_var).grid(row=0, column=0, sticky=tk.EW, padx=5)
        ttk.Button(csv_frame, text="Browse", command=self.sched_browse_csv).grid(row=0, column=1, padx=5)

        # --- Actions --------------------------------------------------
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, sticky=tk.EW, pady=(0, 6))
        ttk.Button(actions, text="Generate Preview", command=self.sched_preview,
                   style="Accent.TButton").pack(side=tk.LEFT)
        ttk.Button(actions, text="Import days from timeline", command=self.sched_import_days).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(actions, text="Generate booking grid...", command=self.sched_generate_grid).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(actions, text="Refresh teams", command=self._refresh_schedule_groups).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # --- Group assignment (scrollable list of certified teams) ----
        groups_box = ttk.LabelFrame(frame, text="Practice groups (certified teams)", padding=4)
        groups_box.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 6))
        groups_box.rowconfigure(0, weight=1)
        groups_box.columnconfigure(0, weight=1)
        gcanvas = tk.Canvas(groups_box, bg="#1e1e2e", highlightthickness=0, height=self.px(160))
        gscroll = ttk.Scrollbar(groups_box, orient="vertical", command=gcanvas.yview)
        self.sched_groups_inner = ttk.Frame(gcanvas)
        self.sched_groups_inner.bind(
            "<Configure>", lambda e: gcanvas.configure(scrollregion=gcanvas.bbox("all"))
        )
        gcanvas.create_window((0, 0), window=self.sched_groups_inner, anchor="nw")
        gcanvas.configure(yscrollcommand=gscroll.set)
        gcanvas.grid(row=0, column=0, sticky=tk.NSEW)
        gscroll.grid(row=0, column=1, sticky=tk.NS)
        self._bind_mousewheel(gcanvas)
        self.sched_group_vars: dict[str, tk.StringVar] = {}

        # --- Preview --------------------------------------------------
        ttk.Label(frame, text="Preview (rendered markdown):").grid(row=4, column=0, sticky=tk.W, pady=(6, 0))
        self.sched_preview_text = tk.Text(
            frame, height=14, bg="#2a2a3c", fg="#cdd6f4", font=("Ubuntu Mono", 10),
            relief=tk.FLAT, padx=10, pady=10, wrap=tk.NONE,
        )
        self.sched_preview_text.grid(row=5, column=0, sticky=tk.NSEW, pady=4)
        sp_scroll = ttk.Scrollbar(frame, command=self.sched_preview_text.yview)
        sp_scroll.grid(row=5, column=1, sticky=tk.NS)
        self.sched_preview_text.config(yscrollcommand=sp_scroll.set)

        self._refresh_schedule_groups()

    def _schedule_teams(self) -> list:
        """Certified teams for scheduling (fall back to candidates if none yet)."""
        try:
            teams = cert.teams_from_config(self.certification_data)
        except Exception:
            teams = []
        certified = [t for t in teams if t.certified]
        pool = certified if certified else [t for t in teams if t.is_candidate]
        return sorted(pool, key=lambda t: t.display_name.lower())

    def _refresh_schedule_groups(self) -> None:
        for child in self.sched_groups_inner.winfo_children():
            child.destroy()
        self.sched_group_vars = {}
        teams = self._schedule_teams()
        groups = self.schedule_data.setdefault("groups", {})
        if not teams:
            ttk.Label(
                self.sched_groups_inner,
                text="No certified teams yet — certify teams on the Certification tab first.",
                foreground="#a6adc8",
            ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            return
        for i, team in enumerate(teams):
            ttk.Label(self.sched_groups_inner, text=team.display_name).grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=2
            )
            var = tk.StringVar(value=groups.get(team.team_key, ""))
            self.sched_group_vars[team.team_key] = var
            combo = ttk.Combobox(
                self.sched_groups_inner, textvariable=var, width=6,
                values=[""] + [str(n) for n in range(1, 9)],
            )
            combo.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            var.trace_add("write", lambda *a, k=team.team_key, v=var: self._sched_set_group(k, v))

    def _sched_set_group(self, team_key: str, var: tk.StringVar) -> None:
        groups = self.schedule_data.setdefault("groups", {})
        val = var.get().strip()
        if val:
            groups[team_key] = val
        else:
            groups.pop(team_key, None)

    def sched_auto_assign(self) -> None:
        try:
            size = int(self.sched_group_size_var.get().strip())
        except ValueError:
            messagebox.showwarning("Auto-assign", "Teams per group must be a number.")
            return
        self.schedule_data["group_size"] = size
        keys = [t.team_key for t in self._schedule_teams()]
        if not keys:
            messagebox.showinfo("Auto-assign", "No certified teams to assign.")
            return
        self.schedule_data["groups"] = sched.auto_assign_groups(keys, size)
        self._refresh_schedule_groups()

    def sched_browse_csv(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select schedule CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=SCRIPT_DIR,
        )
        if filename:
            self.sched_csv_var.set(filename)
            self.schedule_data["csv_path"] = filename

    @staticmethod
    def _override_to_iso(text: str, year: str) -> str:
        """Best-effort parse a free-text date override (e.g. 'June 22nd') to ISO.

        Falls back to the original text if it can't be parsed.
        """
        t = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE).strip(" ,")
        candidates = [t]
        if year and year not in t:
            candidates.append(f"{t} {year}")
        formats = ("%Y-%m-%d", "%B %d %Y", "%b %d %Y", "%d %B %Y", "%m/%d/%Y", "%B %d", "%b %d")
        for cand in candidates:
            for fmt in formats:
                try:
                    dt = datetime.strptime(cand, fmt)
                    if dt.year == 1900 and year:  # format had no year
                        dt = dt.replace(year=int(year))
                    return dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue
        return text

    def _timeline_days(self) -> list[tuple[str, str]]:
        """Resolve enabled competition days to (label, ISO date) from the config."""
        cfg = self.collect_config()
        dcfg = cfg.get("dates", {})
        comp = cfg.get("competition_days", {})
        year = cfg.get("event", {}).get("year", "")
        try:
            calc = calculate_dates(dcfg.get("race_day", ""), dcfg.get("offsets", {}))
        except Exception:
            calc = {}
        defs = [
            ("track_setup", "Track Setup"),
            ("team_training", "Team Training"),
            ("qualification", "Qualification / Time Trials"),
            ("race", "Race Day"),
        ]
        out = []
        for key, label in defs:
            dc = comp.get(key, {})
            if not dc.get("enabled", False):
                continue
            override = (dc.get("date_override", "") or "").strip()
            if override:
                date_str = self._override_to_iso(override, year)
            else:
                dt = calc.get(key)
                date_str = dt.strftime("%Y-%m-%d") if dt else ""
            out.append((label, date_str))
        return out

    def sched_import_days(self) -> None:
        """Pull the competition days straight from the event manager (no file)."""
        days = self._timeline_days()
        if not days:
            messagebox.showinfo(
                "Import days from timeline",
                "No enabled competition days found. Configure them on the "
                "Competition Days tab first.",
            )
            return
        self.schedule_data["days"] = [
            {"label": label, "date": date} for label, date in days
        ]
        self.sched_preview()
        messagebox.showinfo(
            "Import days from timeline",
            "Imported these days from the event timeline:\n\n"
            + "\n".join(f"  - {label}: {date or '(no date set)'}" for label, date in days)
            + "\n\nThey now appear as day sections in the schedule.",
        )

    def sched_generate_grid(self) -> None:
        days = self._timeline_days()
        date_choices = [d for _, d in days if d]
        result = self._prompt_form(
            "Generate booking grid",
            [
                ("Session name", "session", "Regulated Practice", False),
                ("Date", "date", date_choices[0] if date_choices else "", date_choices or [""]),
                ("Start (HH:MM)", "start", "11:00", False),
                ("End (HH:MM, optional)", "end", "13:00", False),
                ("Slot minutes", "slot", "10", False),
                ("Slot count (optional)", "count", "", False),
                ("Switch buffer minutes", "switch", "0", False),
                ("Group (optional)", "group", "", False),
            ],
        )
        if not result:
            return
        try:
            slot = int(result["slot"])
            switch = int(result["switch"] or 0)
            count = int(result["count"]) if result["count"].strip() else None
            rows = sched.generate_slot_grid(
                result["date"], result["start"], result["end"], slot,
                result["session"], count=count, switch_minutes=switch,
                group=result["group"].strip(),
            )
        except Exception as e:
            messagebox.showerror("Generate booking grid", f"Could not generate grid: {e}")
            return
        if not rows:
            messagebox.showinfo("Generate booking grid", "No slots produced — check the times/count.")
            return
        path = filedialog.asksaveasfilename(
            title="Save booking grid CSV",
            defaultextension=".csv",
            initialfile="booking_grid.csv",
            initialdir=SCRIPT_DIR,
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(sched.rows_to_csv(rows))
        messagebox.showinfo(
            "Generate booking grid",
            f"Wrote {len(rows)} empty slot(s) to:\n{path}\n\n"
            "Paste these rows into your schedule sheet; teams fill the Team column.",
        )

    def sched_preview(self) -> None:
        self.schedule_data["timezone_label"] = self.sched_tz_var.get().strip() or "ET"
        self.schedule_data["csv_path"] = self.sched_csv_var.get().strip()
        teams = self._schedule_teams()
        display = {t.team_key: t.display_name for t in teams}
        groups_md = sched.render_groups_markdown(self.schedule_data.get("groups", {}), display)
        rows = []
        path = self.schedule_data["csv_path"]
        if path and Path(path).exists():
            try:
                rows = sched.load_schedule_csv(path)
            except Exception as e:
                messagebox.showerror("Preview", f"Could not parse schedule CSV: {e}")
                return
        schedule_md = sched.render_schedule_markdown(
            rows, self.schedule_data["timezone_label"], days=self.schedule_data.get("days", [])
        )
        body = "\n\n".join(p for p in (groups_md, schedule_md) if p)
        self.sched_preview_text.delete("1.0", tk.END)
        self.sched_preview_text.insert(
            "1.0",
            body or "(nothing to preview — assign groups, import days, and/or select a schedule CSV)",
        )

    def create_resources_tab(self) -> None:
        """Create the Resources tab for adding custom Markdown to race_resources.md."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Resources")

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        ttk.Label(
            frame,
            text="Extra resources (Markdown) — appended after orientation links in race_resources.md:",
            font=("", 10),
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=(10, 2))

        ttk.Label(
            frame,
            text="Example:  - [Track Map](https://example.com/track.pdf)",
            foreground="#a6adc8",
        ).grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5))

        self.extra_resources_text = tk.Text(
            frame,
            height=20,
            bg="#2a2a3c",
            fg="#cdd6f4",
            font=("Ubuntu Mono", 10),
            relief=tk.FLAT,
            padx=10,
            pady=10,
            insertbackground="#cdd6f4",
            wrap=tk.NONE,
        )
        self.extra_resources_text.grid(row=2, column=0, sticky=tk.NSEW, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(frame, command=self.extra_resources_text.yview)
        scrollbar_y.grid(row=2, column=1, sticky=tk.NS)
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.extra_resources_text.xview)
        scrollbar_x.grid(row=3, column=0, sticky=tk.EW)
        self.extra_resources_text.config(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        existing = self.config.get("extra_resources", "")
        if existing:
            self.extra_resources_text.insert("1.0", existing)

    def create_button_frame(self) -> None:
        """Create the bottom button frame."""
        frame = ttk.Frame(self.root)
        # side=BOTTOM so the row always keeps its space below the notebook.
        frame.pack(side=tk.BOTTOM, fill=tk.X, padx=self.px(10), pady=self.px(15))

        # Left side - main actions
        left_frame = tk.Frame(frame, bg="#1e1e2e")
        left_frame.pack(side=tk.LEFT)

        # Save Configuration - subtle teal
        tk.Button(
            left_frame,
            text="Save Configuration",
            command=self.save_config,
            bg="#2d4a4a",
            fg="#a6e3a1",
            activebackground="#3d5a5a",
            activeforeground="#a6e3a1",
            font=("Ubuntu", 10),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        # Apply to Repository - accent teal (matching selected tab)
        tk.Button(
            left_frame,
            text="Apply to Repository",
            command=self.apply_to_repo,
            bg="#00838f",
            fg="#e0f7fa",
            activebackground="#00acc1",
            activeforeground="#ffffff",
            font=("Ubuntu", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        # Reset to Defaults - muted red/rose
        tk.Button(
            left_frame,
            text="Reset to Defaults",
            command=self.reset_config,
            bg="#4a2d2d",
            fg="#f38ba8",
            activebackground="#5a3d3d",
            activeforeground="#f38ba8",
            font=("Ubuntu", 10),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        # Right side - exit (neutral)
        tk.Button(
            frame,
            text="Exit",
            command=self.on_close,
            bg="#2a2a3c",
            fg="#cdd6f4",
            activebackground="#3a3a4c",
            activeforeground="#cdd6f4",
            font=("Ubuntu", 10),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=5)

    def browse_conference_logo(self) -> None:
        """Open file picker to select conference logo image."""
        # Start in images directory
        initial_dir = PROJECT_ROOT / "images"
        if not initial_dir.exists():
            initial_dir = PROJECT_ROOT

        filepath = filedialog.askopenfilename(
            title="Select Conference Logo",
            initialdir=initial_dir,
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.gif"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("WebP files", "*.webp"),
                ("All files", "*.*"),
            ],
        )

        if filepath:
            # Convert to relative path from project root
            try:
                rel_path = Path(filepath).relative_to(PROJECT_ROOT)
                self.conference_logo_entry.delete(0, tk.END)
                self.conference_logo_entry.insert(0, str(rel_path))

                # Ask if user wants to regenerate the banner
                if messagebox.askyesno(
                    "Generate Banner",
                    "Would you like to regenerate BackGroundProject.png with this logo?"
                ):
                    self.generate_banner_image(str(rel_path))
            except ValueError:
                # File is outside project root - copy it to images folder
                messagebox.showwarning(
                    "File Location",
                    "Please select an image from within the project directory, "
                    "or copy the image to the 'images' folder first."
                )

    def generate_banner_image(self, logo_path: str) -> None:
        """Generate BackGroundProject.png with roboracer icon and conference logo on base image."""
        try:
            offset = 100
            svg_scale = 8  # Scale for roboracer icon

            # Load the base background image
            base_path = PROJECT_ROOT / "images" / "Main_Image_Backup.jpg"
            if not base_path.exists():
                messagebox.showerror(
                    "Error",
                    "Main_Image_Backup.jpg not found in images folder.\n"
                    "This file is required as the base background."
                )
                return

            banner = Image.open(base_path).convert("RGBA")
            banner_width, banner_height = banner.size

            # Load and render roboracer_icon.svg
            roboracer_icon = None
            roboracer_height = 50 * svg_scale  # Default height
            svg_path = PROJECT_ROOT / "images" / "roboracer_icon.svg"
            if svg_path.exists():
                # Render SVG to PNG at a larger size for the banner
                png_data = cairosvg.svg2png(
                    url=str(svg_path),
                    output_width=81 * svg_scale,
                    output_height=50 * svg_scale
                )
                roboracer_icon = Image.open(io.BytesIO(png_data)).convert("RGBA")
                roboracer_height = roboracer_icon.height

                # Position at top-right with offset
                icon_x = banner_width - roboracer_icon.width - offset
                icon_y = offset
                banner.paste(roboracer_icon, (icon_x, icon_y), roboracer_icon)

            # Ask user for scale factor
            scale_dialog = ScaleDialog(
                self.root,
                "Logo Scale",
                f"The Roboracer icon is {roboracer_height}px tall.\n\n"
                "Enter a scale factor for the conference logo:\n"
                "• 1.0 = same height as Roboracer icon\n"
                "• 0.5 = half the height\n"
                "• 2.0 = double the height",
                default_value=1.0
            )
            if scale_dialog.result is None:
                return  # User cancelled

            logo_scale = scale_dialog.result

            # Load conference logo
            conf_logo_path = PROJECT_ROOT / logo_path
            if conf_logo_path.exists():
                conf_logo = Image.open(conf_logo_path).convert("RGBA")

                # Scale conference logo based on user input (relative to roboracer height)
                target_height = int(roboracer_height * logo_scale)
                ratio = target_height / conf_logo.height
                new_width = int(conf_logo.width * ratio)
                conf_logo = conf_logo.resize((new_width, target_height), Image.Resampling.LANCZOS)

                # Position at top-left with offset
                banner.paste(conf_logo, (offset, offset), conf_logo)

            # Save the banner as PNG
            output_path = PROJECT_ROOT / "images" / "BackGroundProject.png"
            banner.save(output_path, "PNG")

            messagebox.showinfo(
                "Success",
                f"Banner image generated successfully!\n\n"
                f"Conference logo scaled to {logo_scale}x Roboracer icon height.\n"
                f"Saved to: {output_path}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate banner: {e}")

    def clear_participants(self) -> None:
        """Clear the participants table in registration.html."""
        if messagebox.askyesno(
            "Confirm Clear",
            "This will remove all participants from registration.html. Continue?"
        ):
            try:
                reg_path = PROJECT_ROOT / "registration.html"
                with open(reg_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Clear the tbody content using placeholder
                content = RepositoryUpdater.replace_placeholder(content, "PARTICIPANTS_TBODY", "")

                with open(reg_path, "w", encoding="utf-8") as f:
                    f.write(content)

                messagebox.showinfo("Success", "Participants list cleared!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear participants: {e}")

    def update_orientation_dates(self) -> None:
        """Update orientation and registration date labels based on calculated dates."""
        try:
            race_day = self.race_day_var.get().strip()
            if not race_day:
                return

            offsets = {}
            for name, entry in self.offset_entries.items():
                offsets[name] = int(entry.get().strip())

            dates = calculate_dates(race_day, offsets)

            if "orientation_1" in dates:
                self.o1_date_label.config(text=format_date_display(dates["orientation_1"]))
            if "orientation_2" in dates:
                self.o2_date_label.config(text=format_date_display(dates["orientation_2"]))
            if "registration_open" in dates:
                self.reg_open_date_label.config(text=format_date_display(dates["registration_open"]))
            if "registration_closes" in dates:
                self.reg_close_date_label.config(text=format_date_display(dates["registration_closes"]))
        except Exception:
            pass  # Silently ignore errors during initial load

    def open_calendar_dialog(self) -> None:
        """Open a calendar dialog to pick the race day."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Race Day")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#1e1e2e")

        # Parse current date or use today
        try:
            current_date = datetime.strptime(self.race_day_var.get(), "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()

        cal = Calendar(
            dialog,
            selectmode="day",
            year=current_date.year,
            month=current_date.month,
            day=current_date.day,
            date_pattern="yyyy-mm-dd",
            background="#1e1e2e",
            foreground="#cdd6f4",
            headersbackground="#2a2a3c",
            headersforeground="#89b4fa",
            selectbackground="#89b4fa",
            selectforeground="#1e1e2e",
            normalbackground="#2a2a3c",
            normalforeground="#cdd6f4",
            weekendbackground="#2a2a3c",
            weekendforeground="#f5c2e7",
            othermonthbackground="#1e1e2e",
            othermonthforeground="#45475a",
            othermonthwebackground="#1e1e2e",
            othermonthweforeground="#45475a",
            bordercolor="#45475a",
            font=("Ubuntu", 11),
        )
        cal.pack(padx=15, pady=15)

        def on_select():
            self.race_day_var.set(cal.get_date())
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg="#1e1e2e")
        btn_frame.pack(pady=15)

        select_btn = tk.Button(
            btn_frame,
            text="Select",
            command=on_select,
            bg="#89b4fa",
            fg="#1e1e2e",
            font=("Ubuntu", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
        )
        select_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            bg="#2a2a3c",
            fg="#cdd6f4",
            font=("Ubuntu", 10),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.wait_window()

    def preview_dates(self) -> None:
        """Preview calculated dates."""
        try:
            race_day = self.race_day_var.get().strip()
            offsets = {}
            for name, entry in self.offset_entries.items():
                offsets[name] = int(entry.get().strip())

            dates = calculate_dates(race_day, offsets)

            preview_text = "Calculated Timeline:\n" + "=" * 40 + "\n\n"
            preview_text += f"Registration Opens: {format_date_display(dates['registration_open'])}\n"
            preview_text += f"Orientation 1: {format_date_display(dates['orientation_1'])}\n"
            preview_text += f"Registration Closes: {format_date_display(dates['registration_closes'])}\n"
            preview_text += f"Orientation 2: {format_date_display(dates['orientation_2'])}\n"
            preview_text += f"Track Setup: {format_date_display(dates['track_setup'])}\n"
            preview_text += f"Team Training: {format_date_display(dates['team_training'])}\n"
            preview_text += f"Qualification: {format_date_display(dates['qualification'])}\n"
            preview_text += f"Race Day: {format_date_display(dates['race'])}\n"

            self.dates_preview.config(state=tk.NORMAL)
            self.dates_preview.delete("1.0", tk.END)
            self.dates_preview.insert("1.0", preview_text)
            self.dates_preview.config(state=tk.DISABLED)

            # Also update orientation and competition day date labels
            self.update_orientation_dates()
            self.update_competition_day_labels()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate dates: {e}")

    def collect_config(self) -> dict:
        """Collect all configuration from GUI fields."""
        # Parse twitch domains
        twitch_domains = [
            d.strip()
            for d in self.twitch_domains_entry.get().split(",")
            if d.strip()
        ]

        # Collect offsets
        offsets = {}
        for name, entry in self.offset_entries.items():
            try:
                offsets[name] = int(entry.get().strip())
            except ValueError:
                offsets[name] = 0

        return {
            "event": {
                "conference_name": self.conference_name_entry.get().strip(),
                "conference_full_name": self.conference_full_name_entry.get().strip(),
                "race_number": self.race_number_entry.get().strip(),
                "year": self.year_entry.get().strip(),
                "venue_name": self.venue_name_entry.get().strip(),
                "location": self.location_entry.get().strip(),
                "venue_url": self.venue_url_entry.get().strip(),
                "conference_url": self.conference_url_entry.get().strip(),
                "conference_logo": self.conference_logo_entry.get().strip(),
                "contact_email": self.contact_email_entry.get().strip(),
                "cname": self.cname_entry.get().strip(),
                "conference_dates_display": self.conference_dates_display_entry.get().strip(),
            },
            "dates": {
                "race_day": self.race_day_var.get().strip(),
                "offsets": offsets,
            },
            "orientation_1": {
                "time_display": self.o1_time_entry.get().strip(),
                "date_override": self.o1_date_override_entry.get().strip(),
                "zoom_link": self.o1_zoom_entry.get().strip(),
                "slides_link": self.o1_slides_entry.get().strip(),
                "video_link": self.o1_video_entry.get().strip(),
            },
            "orientation_2": {
                "time_display": self.o2_time_entry.get().strip(),
                "date_override": self.o2_date_override_entry.get().strip(),
                "zoom_link": self.o2_zoom_entry.get().strip(),
                "slides_link": self.o2_slides_entry.get().strip(),
                "video_link": self.o2_video_entry.get().strip(),
            },
            "registration": {
                "status": self.reg_status_var.get(),
                "form_link": self.reg_form_entry.get().strip(),
                "video_demo_form_link": self.video_demo_form_entry.get().strip(),
                "hardware_list_form_link": self.hardware_list_form_entry.get().strip(),
                "hide_participants": self.hide_participants_var.get(),
                "registration_open_date_override": self.reg_open_date_override_entry.get().strip(),
                "registration_closes_date_override": self.reg_close_date_override_entry.get().strip(),
            },
            "results": {
                "time_trial_sheet_link": self.time_trial_entry.get().strip(),
                "bracket_link": self.bracket_entry.get().strip(),
                "bracket_embed_url": self.bracket_embed_entry.get().strip(),
                "youtube_stream_id": self.youtube_stream_entry.get().strip(),
                "twitch_parent_domains": twitch_domains,
                "show_stream_placeholder": self.show_stream_placeholder_var.get(),
                "stream_placeholder_text": self.stream_placeholder_entry.get().strip(),
                "show_results_placeholder": self.show_results_placeholder_var.get(),
                "results_placeholder_text": self.results_placeholder_entry.get().strip(),
            },
            "sim_racing": {
                "enabled": self.sim_enabled_var.get(),
                "edition": self.sim_edition_entry.get().strip(),
                "website_url": self.sim_website_entry.get().strip(),
                "registration_url": self.sim_registration_entry.get().strip(),
                "timeline_url": self.sim_timeline_entry.get().strip(),
            },
            "competition_days": {
                day: {
                    "enabled": self.comp_days_enabled[day].get(),
                    "date_override": self.comp_days_date_override[day].get().strip(),
                    "time_display": self.comp_days_time[day].get().strip(),
                }
                for day in ["track_setup", "team_training", "qualification", "race"]
            },
            "organizers": self.organizers_data,
            "extra_resources": self.extra_resources_text.get("1.0", tk.END).rstrip("\n"),
            "certification": self.certification_data,
            "schedule": self.schedule_data,
            "ui_scale": self._ui_scale_setting,
        }

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            self.config = self.collect_config()
            save_config(self.config)
            messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        if messagebox.askyesno(
            "Confirm Reset", "Are you sure you want to reset to default configuration?"
        ):
            self.config = get_default_config()
            save_config(self.config)
            # Reload the application
            self.root.destroy()
            main()

    def apply_to_repo(self) -> None:
        """Apply configuration to all repository files."""
        try:
            self.config = self.collect_config()
            save_config(self.config)

            updater = RepositoryUpdater(self.config, PROJECT_ROOT)
            results = updater.update_all()

            # Show results
            result_text = "Repository Update Results:\n" + "=" * 40 + "\n\n"
            for filename, status in results.items():
                result_text += f"{filename}: {status}\n"

            messagebox.showinfo("Update Complete", result_text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply configuration: {e}")

    def on_close(self) -> None:
        """Handle window close event."""
        if messagebox.askyesno("Exit", "Do you want to save configuration before exiting?"):
            self.save_config()
        self.root.destroy()


class RepositoryUpdater:
    """Updates repository files with configuration values."""

    def __init__(self, config: dict, project_root: Path):
        self.config = config
        self.project_root = project_root
        self.event = config.get("event", {})
        self.dates_config = config.get("dates", {})
        self.o1 = config.get("orientation_1", {})
        self.o2 = config.get("orientation_2", {})
        self.reg = config.get("registration", {})
        self.results = config.get("results", {})
        self.sim = config.get("sim_racing", {})
        self.organizers = config.get("organizers", [])

        # Calculate dates
        self.dates = calculate_dates(
            self.dates_config.get("race_day", ""),
            self.dates_config.get("offsets", {}),
        )

        # Pre-compute combined names with year
        self.year = self.event.get("year", "")
        self.conf_acronym = self.event.get("conference_name", "")
        self.conf_full_base = self.event.get("conference_full_name", "")

    @staticmethod
    def replace_placeholder(content: str, name: str, value: str) -> str:
        """Replace content between <!-- NAME --> and <!-- /NAME --> markers."""
        pattern = rf'<!-- {name} -->.*?<!-- /{name} -->'
        replacement = f'<!-- {name} -->{value}<!-- /{name} -->'
        # Replace via a function so backslashes and \1 / \g<0> style sequences in
        # user-entered config values are emitted literally instead of being read
        # as re template escapes.
        return re.sub(pattern, lambda _match: replacement, content, flags=re.DOTALL)

    @staticmethod
    def _clean_html(html: str) -> str:
        """Strip leading whitespace from each line so tabs don't trigger Markdown code blocks."""
        return '\n'.join(line.lstrip() for line in html.strip().split('\n'))

    @property
    def conf_with_year(self) -> str:
        """Conference acronym with year (e.g., 'ICRA 2025')."""
        return f"{self.conf_acronym} {self.year}"

    @property
    def conf_full_with_year(self) -> str:
        """Full conference name with year (e.g., '2025 IEEE Conference on Robotics and Automation')."""
        return f"{self.year} {self.conf_full_base}"

    @property
    def conf_dates_with_year(self) -> str:
        """Conference dates with year (e.g., 'May 19th - 23rd 2025')."""
        return f"{self.event.get('conference_dates_display', '')} {self.year}"

    def update_all(self) -> dict[str, str]:
        """Update all repository files. Returns dict of filename -> status."""
        results = {}

        # Update CNAME
        results["CNAME"] = self.update_cname()

        # Update HTML files
        html_files = [
            "index.html",
            "timeline.md",
            "registration.md",
            "results.md",
            "roboracer_resources.md",
            "orientation_1.md",
            "orientation_2.md",
            "race_schedule.md",
            "_layouts/page.html",
        ]

        for filename in html_files:
            filepath = self.project_root / filename
            if filepath.exists():
                results[filename] = self.update_html_file(filepath)
            else:
                results[filename] = "File not found"

        # Update markdown files
        md_files = ["race_resources.md", "stream.md"]
        for filename in md_files:
            filepath = self.project_root / filename
            if filepath.exists():
                results[filename] = self.update_md_file(filepath)
            else:
                results[filename] = "File not found"

        return results

    def update_cname(self) -> str:
        """Update CNAME file."""
        try:
            cname_path = self.project_root / "CNAME"
            with open(cname_path, "w", encoding="utf-8") as f:
                f.write(self.event.get("cname", ""))
            return "Updated"
        except Exception as e:
            return f"Error: {e}"

    def update_html_file(self, filepath: Path) -> str:
        """Update an HTML file with configuration values."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Common placeholders for all HTML files
            # Page title - wrap entire element
            page_title = f"<title>Roboracer {self.conf_with_year}</title>"
            content = self.replace_placeholder(content, "PAGE_TITLE", page_title)
            content = self.replace_placeholder(content, "CONF_WITH_YEAR", self.conf_with_year)

            # Nav email link - wrap entire element
            contact_email = self.event.get("contact_email", "")
            nav_email_html = f'''<li><a href="mailto:{contact_email}" class="icon solid solo fa-envelope"><span
						class="label">Email</span></a></li>'''
            content = self.replace_placeholder(content, "NAV_EMAIL_LINK", nav_email_html)

            # File-specific updates
            if filepath.name == "index.html":
                content = self._update_index_html(content)
            elif filepath.name == "timeline.md":
                content = self._update_timeline_html(content)
            elif filepath.name == "registration.md":
                content = self._update_registration_html(content)
            elif filepath.name == "results.md":
                content = self._update_results_html(content)
            elif filepath.name == "roboracer_resources.md":
                content = self._update_roboracer_resources_html(content)
            elif filepath.name == "orientation_1.md":
                content = self._update_orientation1_html(content)
            elif filepath.name == "orientation_2.md":
                content = self._update_orientation2_html(content)
            elif filepath.name == "race_schedule.md":
                content = self._update_schedule_html(content)
            elif filepath.name == "page.html":
                content = self._update_page_layout_html(content)

            if content != original_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return "Updated"
            return "No changes needed"
        except Exception as e:
            return f"Error: {e}"

    def _generate_organizers_html(self) -> str:
        """Generate HTML for organizers grid from config data."""
        if not self.organizers:
            return ""

        html_parts = []
        # Process organizers in groups of 4 (one row)
        for i in range(0, len(self.organizers), 4):
            row_organizers = self.organizers[i:i + 4]

            # Images row
            images_html = '<div class="box alt">\n\t\t\t\t\t<div class="row gtr-50 gtr-uniform">\n'
            for org in row_organizers:
                image = org.get("image", "")
                images_html += f'\t\t\t\t\t\t<div class="col-2"><span class="image fit"><img src="{image}"\n\t\t\t\t\t\t\t\t\talt="" /></span></div>\n'
            images_html += '\t\t\t\t\t</div>\n\t\t\t\t</div>'
            html_parts.append(images_html)

            # Details row
            details_html = '<div class="box alt">\n\t\t\t\t\t<div class="row gtr-50 gtr-uniform">\n'
            for org in row_organizers:
                name = org.get("name", "")
                profile_url = org.get("profile_url", "")
                title = org.get("title", "")
                department = org.get("department", "")
                institution = org.get("institution", "")
                details_html += f'''\t\t\t\t\t\t<div class="col-2" , align="center">
							<b><a href="{profile_url}">{name}</a></b>
							<h6>{title}</h6>
							<h6>{department}</h6>
							<h6>{institution}</h6>
						</div>\n'''
            details_html += '\t\t\t\t\t</div>\n\t\t\t\t</div>'
            html_parts.append(details_html)

        return '\n\n\t\t\t\t'.join(html_parts)

    def _update_index_html(self, content: str) -> str:
        """Update index.html using placeholder markers."""
        race_num = self.event.get("race_number", "")
        venue = self.event.get("venue_name", "")
        location = self.event.get("location", "")
        venue_url = self.event.get("venue_url", "")
        conf_url = self.event.get("conference_url", "")
        conf_logo = self.event.get("conference_logo", "")

        # Update race number placeholder (replaces all occurrences)
        content = self.replace_placeholder(content, "RACE_NUMBER", race_num)

        # Update conference info (replaces all occurrences)
        content = self.replace_placeholder(content, "CONF_FULL_WITH_YEAR", self.conf_full_with_year)
        content = self.replace_placeholder(content, "CONF_DATES_WITH_YEAR", self.conf_dates_with_year)

        # Venue link - full element
        venue_link = f'<a href="{venue_url}" class="icon solid solo fa-globe-europe"><span class="label">Location</span></a> {venue}, {location}'
        content = self.replace_placeholder(content, "VENUE_LINK", venue_link)

        # Conference logo link - full element
        conf_logo_link = f'<a href="{conf_url}" class="image main"><img src="{conf_logo}" style="width: 30vw" alt="" /></a>'
        content = self.replace_placeholder(content, "CONF_LOGO_LINK", conf_logo_link)

        # Sim racing paragraph - full element
        if self.sim.get("enabled"):
            edition = self.sim.get("edition", "3rd")
            sim_url = self.sim.get("website_url", "")
            sim_paragraph = f'''<p>
							The {edition} Roboracer Sim Racing League is a virtual benchmark competition where teams can
							participate remotely. The teams will be provided with a simulator environment and a
							standardized car model. The teams will have to write software for their car to fulfill the
							objectives for the competition: Don't crash and minimize laptime. The teams will submit
							their
							software to the organizers, who will run the software on the simulator and evaluate the
							performance of the software. The teams will be ranked based on their performance in the
							simulator. The Sim Racing League is a great opportunity for teams to participate in the
							competition without the need to build a physical car and travel to the competition. For
							more information on the {edition} Roboracer Sim Racing League, please visit the <a
								href="{sim_url}">{edition}
								Sim Racing League website</a>.
						</p>'''
            content = self.replace_placeholder(content, "SIM_RACING_PARAGRAPH", sim_paragraph)
        else:
            content = self.replace_placeholder(content, "SIM_RACING_PARAGRAPH", "")

        # Update organizers grid
        organizers_html = self._generate_organizers_html()
        if organizers_html:
            content = self.replace_placeholder(content, "ORGANIZERS_GRID", organizers_html)

        return content

    def _update_timeline_html(self, content: str) -> str:
        """Update timeline.html using placeholder markers."""
        race_num = self.event.get("race_number", "")

        # Update race number placeholder
        content = self.replace_placeholder(content, "TL_RACE_NUMBER", race_num)

        # Update date cells with calculated dates
        if self.dates:
            # Registration Opens - link to registration form if available
            if "registration_open" in self.dates:
                reg_open_calc = format_date_display(self.dates["registration_open"])
                reg_open_override = self.reg.get("registration_open_date_override", "")
                if reg_open_override:
                    reg_open = f'<span style="text-decoration:line-through;color:#c00;">{reg_open_calc}</span><br><span>{reg_open_override}</span>'
                else:
                    reg_open = reg_open_calc
                content = self.replace_placeholder(content, "TL_REG_OPEN_DATE", reg_open)

            # Registration Opens row - make it a link if form_link is available
            reg_form_link = self.reg.get("form_link", "")
            if reg_form_link:
                reg_open_text = f'<a href="{reg_form_link}">Registration Opens</a>'
            else:
                reg_open_text = 'Registration Opens'
            content = self.replace_placeholder(content, "TL_REG_OPEN_TEXT", reg_open_text)

            # Orientation 1 row - full element
            o1_calc_date = format_date_display(self.dates.get("orientation_1", "")) if "orientation_1" in self.dates else ""
            o1_date_override = self.o1.get("date_override", "")
            o1_time = self.o1.get("time_display", "")
            o1_zoom = self.o1.get("zoom_link", "")
            o1_slides = self.o1.get("slides_link", "")
            o1_video = self.o1.get("video_link", "")

            # Build date display - show strikethrough if overridden
            if o1_date_override:
                o1_date_html = f'<span style="text-decoration:line-through;color:#c00;">{o1_calc_date}, {o1_time}</span><br><span>{o1_date_override}, {o1_time}</span>'
            else:
                o1_date_html = f'{o1_calc_date}, {o1_time}'

            # Build orientation title - only link if zoom_link is provided
            if o1_zoom:
                o1_title = f'<a href="{o1_zoom}"><span style="font-weight:inherit;font-style:inherit">Roboracer Orientation 1 ( Competition Rules overview )</span></a>'
            else:
                o1_title = '<span style="font-weight:inherit;font-style:inherit">Roboracer Orientation 1 ( Competition Rules overview )</span>'

            # Build slide/video links - only show as links if URLs are provided
            o1_resources = []
            if o1_slides:
                o1_resources.append(f'<a href="{o1_slides}">Slide</a>')
            else:
                o1_resources.append('Slide')
            if o1_video:
                o1_resources.append(f'<a href="{o1_video}">Video</a>')
            else:
                o1_resources.append('Video')
            o1_resources_html = ' '.join(o1_resources)

            o1_row = self._clean_html(f'''<tr>
							<td class="tg-1vzr"><span
									style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">{o1_date_html}</span>
							</td>
							<td class="tg-j1gp">{o1_title}<br>
								<span
									style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">
									{o1_resources_html}</span>
							</td>
						</tr>''')
            content = self.replace_placeholder(content, "TL_O1_ROW", o1_row)

            # Registration Closes and Video Demo row
            if "registration_closes" in self.dates:
                reg_close_calc = format_date_display(self.dates["registration_closes"])
                reg_close_override = self.reg.get("registration_closes_date_override", "")
                if reg_close_override:
                    reg_close = f'<span style="text-decoration:line-through;color:#c00;">{reg_close_calc}</span><br><span>{reg_close_override}</span>'
                else:
                    reg_close = reg_close_calc
                content = self.replace_placeholder(content, "TL_REG_CLOSE_DATE", reg_close)

            # Video Demo form link - make it a link if provided
            video_demo_form = self.reg.get("video_demo_form_link", "")
            if video_demo_form:
                video_demo_text = f'<a href="{video_demo_form}">Video Demonstration Due</a>'
            else:
                video_demo_text = 'Video Demonstration Due'
            content = self.replace_placeholder(content, "TL_VIDEO_DEMO_TEXT", video_demo_text)

            # Hardware list form link - make it a link if provided
            hardware_list_form = self.reg.get("hardware_list_form_link", "")
            if hardware_list_form:
                hardware_list_text = f'<a href="{hardware_list_form}">Hardware List Due</a>'
            else:
                hardware_list_text = 'Hardware List Due'
            content = self.replace_placeholder(content, "TL_HARDWARE_LIST_TEXT", hardware_list_text)

            # Orientation 2 row - full element
            o2_calc_date = format_date_display(self.dates.get("orientation_2", "")) if "orientation_2" in self.dates else ""
            o2_date_override = self.o2.get("date_override", "")
            o2_time = self.o2.get("time_display", "")
            o2_zoom = self.o2.get("zoom_link", "")
            o2_slides = self.o2.get("slides_link", "")
            o2_video = self.o2.get("video_link", "")

            # Build date display - show strikethrough if overridden
            if o2_date_override:
                o2_date_html = f'<span style="text-decoration:line-through;color:#c00;">{o2_calc_date}, {o2_time}</span><br><span>{o2_date_override}, {o2_time}</span>'
            else:
                o2_date_html = f'{o2_calc_date}, {o2_time}'

            # Build orientation title - only link if zoom_link is provided
            if o2_zoom:
                o2_title = f'<a href="{o2_zoom}"><span style="font-weight:400;font-style:normal">Roboracer Orientation 2 ( Track set up, Track overview for in-person competition, Teams Training )</span></a>'
            else:
                o2_title = '<span style="font-weight:400;font-style:normal">Roboracer Orientation 2 ( Track set up, Track overview for in-person competition, Teams Training )</span>'

            # Build slide/video links - only show as links if URLs are provided
            o2_resources = []
            if o2_slides:
                o2_resources.append(f'<a href="{o2_slides}">Slide</a>')
            else:
                o2_resources.append('Slide')
            if o2_video:
                o2_resources.append(f'<a href="{o2_video}">Video</a>')
            else:
                o2_resources.append('Video')
            o2_resources_html = ' '.join(o2_resources)

            o2_row = self._clean_html(f'''<tr>
							<td class="tg-tbri"><span
									style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">{o2_date_html}</span></td>
							<td class="tg-npj4">{o2_title}<br>
								<span
									style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">
									{o2_resources_html}</span>
							</td>
						</tr>''')
            content = self.replace_placeholder(content, "TL_O2_ROW", o2_row)

            # Track Setup
            if "track_setup" in self.dates:
                track_setup = format_date_display(self.dates["track_setup"])
                content = self.replace_placeholder(content, "TL_TRACK_SETUP_DATE", track_setup)

            # Team Training
            if "team_training" in self.dates:
                training = format_date_display(self.dates["team_training"])
                content = self.replace_placeholder(content, "TL_TRAINING_DATE", training)

            # Qualification
            if "qualification" in self.dates:
                qual = format_date_display(self.dates["qualification"])
                content = self.replace_placeholder(content, "TL_QUAL_DATE", qual)

            # Race Day (backwards-compat date-only replacement)
            if "race" in self.dates:
                race = format_date_display(self.dates["race"])
                content = self.replace_placeholder(content, "TL_RACE_DATE", race)

        # Competition days — ROW-level replacements (toggle / date override / time)
        comp_days = self.config.get("competition_days", {})
        comp_day_defs = [
            ("track_setup", "TL_TRACK_SETUP_ROW", "tg-1vzr", "tg-j1gp",
             "Teams on-site registration and training/practice sessions"),
            ("team_training", "TL_TRAINING_ROW", "tg-1vzr", "tg-j1gp",
             "Training/practice sessions"),
            ("qualification", "TL_QUAL_ROW", "tg-1vzr", "tg-j1gp",
             "Qualification Time Trials"),
            ("race", "TL_RACE_ROW", "tg-1vzr", "tg-j1gp",
             "Head-to-Head Tournament &amp; Award Ceremony"),
        ]
        for day_key, row_ph, td1, td2, description in comp_day_defs:
            day_cfg = comp_days.get(day_key, {"enabled": True, "date_override": "", "time_display": ""})
            if not day_cfg.get("enabled", True):
                content = self.replace_placeholder(content, row_ph, "")
                continue
            date_override = day_cfg.get("date_override", "")
            time_display = day_cfg.get("time_display", "")
            if date_override:
                date_str = date_override
            elif day_key in self.dates:
                date_str = format_date_display(self.dates[day_key])
            else:
                date_str = ""
            date_cell = f"{date_str}, {time_display}" if time_display else date_str
            row_html = self._clean_html(f'''<tr>
<td class="{td1}"><span style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">{date_cell}</span></td>
<td class="{td2}"><span style="font-weight:400;font-style:normal;text-decoration:none;color:#000;background-color:transparent">{description}</span>
</td>
</tr>''')
            content = self.replace_placeholder(content, row_ph, row_html)

        # Sim Racing timeline paragraph - only show if sim racing is enabled
        if self.sim.get("enabled", False):
            sim_timeline_url = self.sim.get("timeline_url", "")
            sim_paragraph = self._clean_html(f'''<p>For a detailed timeline of the virtual competition, please refer to the <a
					href="{sim_timeline_url}">virtual
					competition website</a>. </p>''')
        else:
            sim_paragraph = ""
        content = self.replace_placeholder(content, "TL_SIM_PARAGRAPH", sim_paragraph)

        return content

    def _certified_participant_rows(self) -> str:
        """Build participant <tr> rows for certified teams from certification config.

        Returns an empty string if nothing is configured so the participants
        table simply renders empty (unchanged behaviour).
        """
        try:
            teams = cert.teams_from_config(self.config.get("certification", {}))
            return cert.render_participant_rows(teams)
        except Exception:
            return ""

    def _update_schedule_html(self, content: str) -> str:
        """Fill the SCHEDULE placeholder with group rosters + the timetable."""
        certc = self.config.get("certification", {})
        sch_cfg = self.config.get("schedule", {})
        try:
            teams = cert.teams_from_config(certc)
            display = {t.team_key: t.display_name for t in teams}
            groups_md = sched.render_groups_markdown(
                sch_cfg.get("groups", {}), display
            )
            csv_path = sch_cfg.get("csv_path", "")
            rows = []
            if csv_path and Path(csv_path).exists():
                rows = sched.load_schedule_csv(csv_path)
            schedule_md = sched.render_schedule_markdown(
                rows, sch_cfg.get("timezone_label", "ET"), days=sch_cfg.get("days", [])
            )
            body = "\n\n".join(p for p in (groups_md, schedule_md) if p)
            block = f"\n{body}\n" if body else ""
            return self.replace_placeholder(content, "SCHEDULE", block)
        except Exception:
            return content

    def _update_registration_html(self, content: str) -> str:
        """Update registration.html using placeholder markers."""
        reg_status = self.reg.get("status", "closed")
        form_link = self.reg.get("form_link", "")
        hide_participants = self.reg.get("hide_participants", False)
        contact_email = self.event.get("contact_email", "")

        # Registration info paragraph - full element
        sim_edition = self.sim.get("edition", "3rd")
        sim_reg_url = self.sim.get("registration_url", "")
        reg_info = self._clean_html(f'''<p>This competition is open for everyone of all levels, everyone is welcome to participate in this
					competition.
					A team can consist of multiple teammates. Teams with only one person are also allowed.
					Teams that take part in the in-person competition need to provide and build an Roboracer car by
					themselves.
					To register in the {sim_edition} Roboracer Sim Racing League, please refer to the <a
						href="{sim_reg_url}">Sim
						Racing Registration page</a>.
					<br>
					The following Google form is only for preliminary registration and for orientation and information
					sessions. Registration to {self.conf_with_year} is expected for all competitors.
				</p>''')
        content = self.replace_placeholder(content, "REG_INFO_PARAGRAPH", reg_info)

        # Update registration button based on status
        if reg_status == "open" and form_link:
            button_html = f'<a href="{form_link}" class="button">Registration Open</a>'
        else:
            button_html = '<a class="button" style="pointer-events: none; opacity: 0.5;">Registration Closed</a>'
        content = self.replace_placeholder(content, "REG_BUTTON", button_html)

        # Handle hide participants section
        if hide_participants:
            # Replace participants section with hidden version
            hidden_section = self._clean_html('''
				<hr style="display:none;">
				<h3 id="participants" style="display:none;">Participants</h3>
				<p style="display:none;">
					If you have registered for participation but the list below is not updated, please contact us at
					<a href="mailto:''' + contact_email + '''"><span
							class="label">''' + contact_email + '''</span></a>. <br>
					Register the modified information under the same team name, and we will update it accordingly.
				</p>
				<table style="display:none;">
					<thead>
						<tr>
							<th style="text-align: left">TEAM NAME</th>
							<th style="text-align: left">AFFILIATION</th>
							<th style="text-align: left">TEAM MEMBERS</th>
						</tr>
					</thead>
					<tbody>
					</tbody>
				</table>
				''')
            content = self.replace_placeholder(content, "PARTICIPANTS_SECTION", hidden_section)
        else:
            # Show participants section, populated with certified teams.
            participant_rows = self._certified_participant_rows()
            visible_section = self._clean_html('''
				<hr>
				<h3 id="participants">Participants</h3>
				<p>
					If you have registered for participation but the list below is not updated, please contact us at
					<a href="mailto:''' + contact_email + '''"><span
							class="label">''' + contact_email + '''</span></a>. <br>
					Register the modified information under the same team name, and we will update it accordingly.
				</p>
				<table>
					<thead>
						<tr>
							<th style="text-align: left">TEAM NAME</th>
							<th style="text-align: left">AFFILIATION</th>
							<th style="text-align: left">TEAM MEMBERS</th>
						</tr>
					</thead>
					<tbody>
''' + participant_rows + '''
					</tbody>
				</table>
				''')
            content = self.replace_placeholder(content, "PARTICIPANTS_SECTION", visible_section)

        return content

    def _update_results_html(self, content: str) -> str:
        """Update results.html using placeholder markers."""
        # Update Twitch parent domains
        domains = self.results.get("twitch_parent_domains", [])
        if domains:
            domains_str = json.dumps(domains)
            content = self.replace_placeholder(content, "TWITCH_PARENTS", domains_str)

        # Get placeholder settings
        show_stream_placeholder = self.results.get("show_stream_placeholder", True)
        stream_placeholder_text = self.results.get("stream_placeholder_text", "Live stream will appear here during the event.")
        show_results_placeholder = self.results.get("show_results_placeholder", True)
        results_placeholder_text = self.results.get("results_placeholder_text", "Results will be posted after the competition.")

        # Update stream placeholder
        if show_stream_placeholder:
            stream_html = f'<p style="color: #888; font-style: italic;">{stream_placeholder_text}</p>'
        else:
            stream_html = ''
        content = self.replace_placeholder(content, "STREAM_PLACEHOLDER", stream_html)

        # Update results placeholder
        if show_results_placeholder:
            results_html = f'<p style="color: #888; font-style: italic;">{results_placeholder_text}</p>'
        else:
            results_html = ''
        content = self.replace_placeholder(content, "RESULTS_PLACEHOLDER", results_html)

        # Update time trial section - hide if no link
        tt_link = self.results.get("time_trial_sheet_link", "")
        if tt_link:
            tt_section = self._clean_html(f'''<br>
						<h3 style="text-align: left;">TIME TRIAL</h3>
						<a href="{tt_link}" class="button">Mapping Schedule, Qualification</a>''')
        else:
            tt_section = ''  # Hide entire section
        content = self.replace_placeholder(content, "TIME_TRIAL_SECTION", tt_section)

        # Update bracket section - hide if no link
        bracket_link = self.results.get("bracket_link", "")
        if bracket_link:
            bracket_section = self._clean_html(f'''<br>
						<br>
						<h3 style="text-align: left;">HEAD TO HEAD RACE BRACKET</h3>
						<a href="{bracket_link}" class="button">TOURNAMENT</a>''')
        else:
            bracket_section = ''  # Hide entire section
        content = self.replace_placeholder(content, "BRACKET_SECTION", bracket_section)

        # Update bracket embed (e.g. Challonge ".../module" widget) - hide if no URL
        bracket_embed_url = self.results.get("bracket_embed_url", "")
        if bracket_embed_url:
            bracket_embed = f'<iframe src="{bracket_embed_url}" width="100%" height="500" frameborder="0" scrolling="auto" allowtransparency="true"></iframe>'
        else:
            bracket_embed = ''  # Hide entire section
        content = self.replace_placeholder(content, "BRACKET_EMBED", bracket_embed)

        return content

    def _update_roboracer_resources_html(self, content: str) -> str:
        """Update roboracer_resources.md using placeholder markers."""
        # AutoDRIVE Simulator sentence - only mention the Sim Racing League when
        # there is one to link to. Both variants end with "...racing algorithms"
        # so the trailing clause outside the marker still reads correctly.
        sim_url = self.sim.get("website_url", "")
        if self.sim.get("enabled", False) and sim_url:
            sim_sentence = (
                f'This simulator will be used for the <a href="{sim_url}">Roboracer '
                f'Sim Racing League</a>, but you can also use it to prototype your '
                f'autonomous racing algorithms'
            )
        else:
            sim_sentence = "This simulator can be used to prototype your autonomous racing algorithms"
        content = self.replace_placeholder(content, "SIM_LEAGUE_SENTENCE", sim_sentence)

        return content

    def _update_orientation1_html(self, content: str) -> str:
        """Update orientation_1.html using placeholder markers."""
        slides_link = self.o1.get("slides_link", "")
        video_link = self.o1.get("video_link", "")

        # Generate full content block
        o1_content = self._clean_html(f'''<h3> Orientation 1 Slides </h3>
						<iframe src="{slides_link}" frameborder="0" width="960" height="569" allowfullscreen="true" mozallowfullscreen="true"
							webkitallowfullscreen="true"></iframe>

						<h3> Orientation 1 Video Recording</h3>
						<iframe src="{video_link}" width="640" height="480" allow="autoplay"></iframe>''')
        content = self.replace_placeholder(content, "O1_CONTENT", o1_content)

        return content

    def _update_orientation2_html(self, content: str) -> str:
        """Update orientation_2.html using placeholder markers."""
        # The CONF_WITH_YEAR placeholder is already handled in the common section
        # O2_CONTENT can be updated when slides/video are available
        return content

    def _update_page_layout_html(self, content: str) -> str:
        """Update _layouts/page.html using placeholder markers."""
        # The markers must stay OUTSIDE <title>: it is an RCDATA element, so a
        # comment written inside it renders as literal text in the browser tab.
        # The Liquid suffix is part of the emitted value, hence the plain (non-f)
        # second string so the {{ }} braces are not read as f-string fields.
        page_title = (
            f'<title>Roboracer {self.conf_with_year} | '
            '{{ page.short_title | default: page.title | escape }}</title>'
        )
        content = self.replace_placeholder(content, "LAYOUT_PAGE_TITLE", page_title)

        return content

    def update_md_file(self, filepath: Path) -> str:
        """Update a markdown file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Update title in YAML front matter (simple text replacement)
            content = re.sub(
                r"title: Roboracer \w+ \d+ Race Resources",
                f"title: Roboracer {self.conf_with_year} Race Resources",
                content,
            )

            # Build orientation links - only include links that have URLs
            orientation_lines = []
            o1_slides = self.o1.get("slides_link", "")
            o1_video = self.o1.get("video_link", "")
            o2_slides = self.o2.get("slides_link", "")
            o2_video = self.o2.get("video_link", "")

            if o1_slides:
                orientation_lines.append(f"\n- [Orientation 1 Meeting Slides]({o1_slides})")
            if o1_video:
                orientation_lines.append(f"- [Orientation 1 Recording]({o1_video})")
            if o2_slides:
                orientation_lines.append(f"- [Orientation 2 Meeting Slides]({o2_slides})")
            if o2_video:
                orientation_lines.append(f"- [Orientation 2 Recording]({o2_video})")

            orientation_content = "\n".join(orientation_lines)
            content = self.replace_placeholder(content, "ORIENTATION_LINKS", orientation_content)

            extra = self.config.get("extra_resources", "").strip()
            extra_content = f"\n{extra}\n" if extra else ""
            content = self.replace_placeholder(content, "EXTRA_RESOURCES", extra_content)

            if content != original_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return "Updated"
            return "No changes needed"
        except Exception as e:
            return f"Error: {e}"


def main():
    """Main entry point."""
    # Use regular Tk with custom dark styling
    root = tk.Tk()
    app = EventManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

