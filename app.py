from __future__ import annotations

import ctypes
import json
import locale
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse


APP_NAME = "yt-dlp Desktop"
APP_DIR = Path(__file__).resolve().parent
ICON_PNG = APP_DIR / "assets" / "desktop.png"
ICON_ICO = APP_DIR / "assets" / "desktop.ico"
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_YTDLP = APP_DIR / ".venv" / "Scripts" / "yt-dlp.exe"
REQUIREMENTS = APP_DIR / "requirements.txt"
PLUGIN_DIR = APP_DIR / "plugins"

COLOR_BACKGROUND = "#18191B"
COLOR_SURFACE = "#222326"
COLOR_SURFACE_HOVER = "#303135"
COLOR_BORDER = "#3B3D42"
COLOR_RED = "#C82E37"
COLOR_RED_HOVER = "#B9252E"
COLOR_FOCUS = "#F18388"
COLOR_WHITE = "#F4F4F5"
COLOR_MUTED = "#ACADB4"

COMPATIBLE_MP4 = "MP4 (H.264 / AAC)"

FORMAT_OPTIONS: dict[str, list[str]] = {
    COMPATIBLE_MP4: [
        "-f", "bv*+ba/bv*",
        "-S", "res,fps,vcodec:h264,acodec:aac",
        "--merge-output-format", "mkv",
        "--use-postprocessor", "DesktopCompatible:when=post_process",
    ],
    "Video (original codecs)": ["-f", "bv*+ba/b"],
    "MP3 audio only": ["-x", "--audio-format", "mp3", "--audio-quality", "0"],
    "M4A audio only": ["-x", "--audio-format", "m4a", "--audio-quality", "0"],
}
BEST_RESOLUTION = "Best available"


def available_resolutions(info: dict, format_name: str) -> list[int]:
    """List video heights across codecs, including VP9 and AV1 above 1080p."""
    if "-f" not in FORMAT_OPTIONS[format_name]:
        return []
    heights: set[int] = set()
    for item in info.get("formats") or []:
        height = item.get("height")
        if (
            not isinstance(height, (int, float)) or height <= 0
            or item.get("vcodec") in {"none", "images"}
            or item.get("has_drm")
        ):
            continue
        heights.add(int(height))
    return sorted(heights, reverse=True)


def build_metadata_command(executable: str, url: str) -> list[str]:
    return [
        executable, "--ignore-config", "--plugin-dirs", str(PLUGIN_DIR),
        "--dump-single-json", "--skip-download", "--no-playlist",
        "--playlist-items", "1", "--no-warnings", "--no-colors",
        "--encoding", "utf-8", "--socket-timeout", "15", "--retries", "1",
        "--", url,
    ]


def locate_yt_dlp() -> str | None:
    """Find yt-dlp only inside this project's isolated environment."""
    return str(VENV_YTDLP.resolve()) if VENV_YTDLP.is_file() else None


def build_update_command() -> list[str]:
    """Update only the yt-dlp package installed in this project's .venv."""
    return [
        str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check",
        "--upgrade", "-r", str(REQUIREMENTS),
    ]


def probe_yt_dlp(executable: str) -> str:
    """Confirm that the selected program is the yt-dlp command-line tool."""
    result = subprocess.run(
        [executable, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=10,
        check=False,
    )
    version = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if result.returncode != 0 or not re.match(r"^\d{4}\.\d{2}\.\d{2}", version):
        raise RuntimeError("The selected program is not the yt-dlp command-line tool.")
    return version


def is_valid_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def build_command(
    executable: str,
    url: str,
    destination: str,
    format_name: str,
    download_playlist: bool,
    resolution: int | None = None,
) -> list[str]:
    output_name = "%(title).180B [%(id)s]"
    if format_name == COMPATIBLE_MP4:
        output_name += "%(height& {}p|)s (H264)"
    command = [
        executable, "--ignore-config", "--plugin-dirs", str(PLUGIN_DIR),
        "--encoding", "utf-8",
        "--no-quiet",
        "--progress",
        "--newline",
        "--progress-delta", "0.2",
        "--no-colors",
        "--windows-filenames",
        "--progress-template",
        "download:PROGRESS:[%(info.format_id|null)j,%(progress.{status,downloaded_bytes,total_bytes,total_bytes_estimate,fragment_index,fragment_count,_speed_str,_eta_str})j]",
        "--print", "before_dl:TRANSFER:[%(playlist_autonumber|null)s,%(n_entries|null)s,%(requested_formats.:.{format_id,filesize,filesize_approx}|null)j]",
        "--print", "after_move:FILE:%(filepath)j",
        "-P", destination,
        "-o", output_name + ".%(ext)s",
    ]
    if format_name == COMPATIBLE_MP4:
        command.extend(["-P", f"temp:{Path(destination) / '.yt-dlp-desktop'}"])
    command.append("--yes-playlist" if download_playlist else "--no-playlist")
    format_options = FORMAT_OPTIONS[format_name].copy()
    if resolution is not None and "-f" in format_options:
        # A playlist can contain videos smaller than the requested quality.
        height_filter = f"[height{'<=' if download_playlist else '='}{resolution}]"
        format_options[1] = re.sub(
            r"\bbv?\*?(?=\[|[+/]|$)",
            lambda match: match[0] + height_filter, format_options[1],
        )
    command.extend(format_options)
    command.extend(["--", url])
    return command


def style_title_bar(root: tk.Tk) -> None:
    if os.name != "nt":
        return
    hwnd = ctypes.windll.user32.GetAncestor
    hwnd.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    hwnd.restype = ctypes.c_void_p
    window = hwnd(root.winfo_id(), 2)
    set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    set_attribute.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint)
    dark = ctypes.c_int(1)
    if set_attribute(window, 20, ctypes.byref(dark), ctypes.sizeof(dark)) != 0:
        set_attribute(window, 19, ctypes.byref(dark), ctypes.sizeof(dark))
    # Windows 11 can match the client colors. Windows 10 uses the dark native caption.
    for attribute, color in ((34, COLOR_BORDER), (35, COLOR_BACKGROUND), (36, COLOR_WHITE)):
        rgb = bytes.fromhex(color[1:])
        colorref = ctypes.c_uint(int.from_bytes(rgb, "little"))
        set_attribute(window, attribute, ctypes.byref(colorref), ctypes.sizeof(colorref))


class TransferProgress:
    def __init__(self, formats: list[dict]) -> None:
        sizes = {item["format_id"]: item.get("filesize") or item.get("filesize_approx") for item in formats}
        self.weights = sizes if sizes and all(sizes.values()) else dict.fromkeys(sizes, 1)
        self.fractions: dict[str | None, float] = {}

    def update(self, format_id: str | None, data: dict) -> float | None:
        if self.weights and format_id not in self.weights:
            return None
        downloaded = data.get("downloaded_bytes")
        total = data.get("total_bytes")
        estimate = data.get("total_bytes_estimate")
        fragments = data.get("fragment_count")
        if data.get("status") == "finished":
            fraction = 1.0
        elif total and downloaded is not None:
            fraction = downloaded / total
        elif fragments:
            # Early HLS/DASH byte estimates can be as small as the first packet.
            index = data.get("fragment_index") or 0
            fraction = index / fragments
            if downloaded is not None and estimate and downloaded < estimate:
                fraction = max(fraction, min((index + 1) / fragments, downloaded / estimate))
        elif downloaded is not None and estimate and downloaded < estimate:
            fraction = downloaded / estimate
        else:
            return None
        if data.get("status") != "finished":
            fraction = min(0.99, fraction)
        self.fractions[format_id] = max(fraction, self.fractions.get(format_id, 0))
        if not self.weights:
            return 100 * self.fractions[format_id]
        return 100 * sum(
            self.fractions.get(key, 0) * weight for key, weight in self.weights.items()
        ) / sum(self.weights.values())


class YtDlpApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        try:
            if ICON_ICO.is_file():
                self.root.iconbitmap(str(ICON_ICO))
            else:
                self.root.iconphoto(True, tk.PhotoImage(file=str(ICON_PNG)))
        except tk.TclError:
            pass
        self.root.configure(background=COLOR_BACKGROUND)

        self.messages: queue.Queue[tuple] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.active_operation: str | None = None
        self.cancel_requested = False
        self.close_when_done = False
        self.downloaded_files: list[str] = []
        self.details_visible = False
        self.metadata_after: str | None = None
        self.metadata_revision = 0
        self.metadata_loading = False
        self.metadata_url: str | None = None
        self.metadata_info: dict = {}
        self.metadata_error = False

        self.url_var = tk.StringVar()
        default_downloads = Path.home() / "Downloads"
        self.destination_var = tk.StringVar(value=str(default_downloads))
        self.format_var = tk.StringVar(value=COMPATIBLE_MP4)
        self.resolution_var = tk.StringVar(value=BEST_RESOLUTION)
        self.resolution_hint = tk.StringVar(value="Paste a URL to check available resolutions.")
        self.playlist_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.detail_var = tk.StringVar()
        self.progress_var = tk.DoubleVar(value=0)

        self._configure_style()
        self._build_ui()
        self.url_var.trace_add("write", self._url_changed)
        self.format_var.trace_add("write", lambda *_args: self._refresh_resolutions())
        self.playlist_var.trace_add("write", lambda *_args: self._refresh_resolutions())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_messages)
        self.url_entry.focus_set()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=COLOR_BACKGROUND, foreground=COLOR_WHITE)
        style.configure("Heading.TLabel", font=("Segoe UI Semibold", 17))
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 10))
        style.configure("Muted.TLabel", foreground=COLOR_MUTED)
        style.configure("Rule.TFrame", background=COLOR_BORDER)

        for widget in ("TEntry", "TCombobox"):
            style.configure(
                widget, fieldbackground=COLOR_SURFACE, foreground=COLOR_WHITE,
                background=COLOR_SURFACE, insertcolor=COLOR_WHITE, arrowcolor=COLOR_MUTED,
                bordercolor=COLOR_BORDER, lightcolor=COLOR_SURFACE, darkcolor=COLOR_SURFACE,
                padding=(8, 6),
            )
            style.map(
                widget, fieldbackground=[("disabled", COLOR_BACKGROUND), ("readonly", COLOR_SURFACE)],
                foreground=[("disabled", COLOR_MUTED), ("readonly", COLOR_WHITE)],
                selectbackground=[("readonly", COLOR_SURFACE)],
                selectforeground=[("readonly", COLOR_WHITE)],
                bordercolor=[("focus", COLOR_FOCUS)],
            )
        self.root.option_add("*TCombobox*Listbox.background", COLOR_SURFACE)
        self.root.option_add("*TCombobox*Listbox.foreground", COLOR_WHITE)
        self.root.option_add("*TCombobox*Listbox.selectBackground", COLOR_RED)
        self.root.option_add("*TCombobox*Listbox.selectForeground", COLOR_WHITE)

        style.configure(
            "TCheckbutton", indicatorbackground=COLOR_SURFACE, indicatorforeground=COLOR_WHITE,
            bordercolor=COLOR_BORDER, focuscolor=COLOR_FOCUS,
        )
        style.map(
            "TCheckbutton", background=[("active", COLOR_BACKGROUND)],
            foreground=[("disabled", COLOR_MUTED)],
            indicatorbackground=[("selected", COLOR_RED), ("active", COLOR_SURFACE_HOVER)],
        )

        for widget in ("TButton", "TMenubutton", "Primary.TButton"):
            primary = widget == "Primary.TButton"
            background = COLOR_RED if primary else COLOR_BACKGROUND
            hover = COLOR_RED_HOVER if primary else COLOR_SURFACE_HOVER
            style.configure(
                widget, padding=(12, 6), background=background, foreground=COLOR_WHITE,
                bordercolor=COLOR_RED if primary else COLOR_BORDER,
                lightcolor=background, darkcolor=background, focuscolor=COLOR_FOCUS,
            )
            style.map(
                widget, background=[("disabled", COLOR_SURFACE), ("pressed", hover), ("active", hover)],
                bordercolor=[("focus", COLOR_FOCUS), ("disabled", COLOR_BORDER)],
                foreground=[("disabled", COLOR_MUTED)],
            )
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(16, 7))
        style.configure("TMenubutton", arrowcolor=COLOR_MUTED)
        style.configure(
            "Red.Horizontal.TProgressbar", troughcolor=COLOR_SURFACE, background=COLOR_RED,
            bordercolor=COLOR_BORDER, lightcolor=COLOR_RED, darkcolor=COLOR_RED, thickness=7,
        )
        style.configure(
            "Details.Vertical.TScrollbar", background=COLOR_SURFACE_HOVER, troughcolor=COLOR_SURFACE,
            bordercolor=COLOR_BORDER, lightcolor=COLOR_SURFACE_HOVER, darkcolor=COLOR_SURFACE_HOVER,
            arrowcolor=COLOR_MUTED, relief="flat", borderwidth=0, arrowsize=12,
        )

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=(24, 16, 24, 16))
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(11, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Download media", style="Heading.TLabel").pack(side="left")
        tools = ttk.Menubutton(header, text="Tools", width=7, takefocus=True)
        tools.pack(side="right")
        self.tools_menu = tk.Menu(
            tools, tearoff=False, background=COLOR_SURFACE, foreground=COLOR_WHITE,
            activebackground=COLOR_SURFACE_HOVER, activeforeground=COLOR_WHITE,
        )
        self.tools_menu.add_command(label="Update yt-dlp", command=self.start_update)
        tools.configure(menu=self.tools_menu)
        ttk.Frame(container, height=1, style="Rule.TFrame").grid(row=1, column=0, sticky="ew", pady=(0, 15))

        ttk.Label(container, text="Video or playlist URL", style="Section.TLabel").grid(row=2, column=0, sticky="w")
        url_row = ttk.Frame(container)
        url_row.grid(row=3, column=0, sticky="ew", pady=(5, 14))
        url_row.columnconfigure(0, weight=1)
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda _event: self.start_download())
        self.paste_button = ttk.Button(url_row, text="Paste", command=self._paste_url)
        self.paste_button.grid(row=0, column=1, padx=(8, 0), sticky="ns")

        options = ttk.Frame(container)
        options.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        options.columnconfigure(0, weight=3)
        options.columnconfigure(1, weight=2)
        ttk.Label(options, text="Format", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.format_box = ttk.Combobox(
            options, textvariable=self.format_var, values=list(FORMAT_OPTIONS),
            state="readonly", width=24, font=("Segoe UI", 10),
        )
        self.format_box.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        ttk.Label(options, text="Resolution", style="Section.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.resolution_box = ttk.Combobox(
            options, textvariable=self.resolution_var, values=[BEST_RESOLUTION],
            state="disabled", width=18, font=("Segoe UI", 10),
        )
        self.resolution_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(5, 0))
        ttk.Label(options, textvariable=self.resolution_hint, style="Muted.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(5, 0)
        )
        self.playlist_check = ttk.Checkbutton(options, text="Download entire playlist", variable=self.playlist_var)
        self.playlist_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(container, text="Save to", style="Section.TLabel").grid(row=5, column=0, sticky="w")
        folder_row = ttk.Frame(container)
        folder_row.grid(row=6, column=0, sticky="ew", pady=(5, 16))
        folder_row.columnconfigure(0, weight=1)
        self.destination_entry = ttk.Entry(folder_row, textvariable=self.destination_var, font=("Segoe UI", 10))
        self.destination_entry.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(folder_row, text="Browse…", command=self._choose_folder)
        self.browse_button.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        ttk.Button(folder_row, text="Open folder", command=self._open_folder).grid(
            row=0, column=2, sticky="ns", padx=(8, 0)
        )

        ttk.Frame(container, height=1, style="Rule.TFrame").grid(row=7, column=0, sticky="ew")
        progress_frame = ttk.Frame(container)
        progress_frame.grid(row=8, column=0, sticky="ew", pady=(13, 11))
        progress_frame.columnconfigure(0, weight=1)
        ttk.Label(progress_frame, textvariable=self.status_var, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(progress_frame, textvariable=self.detail_var, style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        self.progress = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100,
            mode="determinate", style="Red.Horizontal.TProgressbar",
        )
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0))

        actions = ttk.Frame(container)
        actions.grid(row=9, column=0, sticky="ew")
        actions.columnconfigure(1, weight=1)
        self.details_button = ttk.Button(actions, text="Show details", command=self._toggle_details)
        self.details_button.grid(row=0, column=0)
        self.download_button = ttk.Button(
            actions, text="Download", command=self.start_download, style="Primary.TButton", width=13,
        )
        self.download_button.grid(row=0, column=3)
        self.cancel_button = ttk.Button(actions, text="Cancel", command=self.cancel_download)
        self.cancel_button.grid(row=0, column=2, padx=(0, 8))
        self.cancel_button.grid_remove()

        self.log_frame = ttk.Frame(container)
        self.log_frame.grid(row=11, column=0, sticky="nsew", pady=(12, 0))
        self.log_frame.rowconfigure(0, weight=1)
        self.log_frame.columnconfigure(0, weight=1)
        self.log = tk.Text(
            self.log_frame, height=5, wrap="word", state="disabled", font=("Consolas", 9),
            bg=COLOR_SURFACE, fg=COLOR_WHITE, selectbackground=COLOR_RED, selectforeground=COLOR_WHITE,
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=COLOR_BORDER, highlightcolor=COLOR_FOCUS, padx=8, pady=7,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log_scrollbar = ttk.Scrollbar(
            self.log_frame, orient="vertical", command=self.log.yview, style="Details.Vertical.TScrollbar",
        )
        self.log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_scrollbar.grid_remove()
        self.log.configure(yscrollcommand=self._update_log_scrollbar)
        self.log_frame.grid_remove()

        self.root.update_idletasks()
        self.compact_height = container.winfo_reqheight()
        self.root.minsize(575, self.compact_height)
        self.root.geometry(f"705x{self.compact_height}")
        style_title_bar(self.root)

    def _toggle_details(self) -> None:
        self._show_details(not self.details_visible)

    def _show_details(self, visible: bool = True) -> None:
        if visible == self.details_visible:
            return
        self.details_visible = visible
        self.details_button.configure(text="Hide details" if visible else "Show details")
        if visible:
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()
        height = self.compact_height + (125 if visible else 0)
        self.root.minsize(575, height)
        if self.root.state() == "normal" and (visible or self.root.winfo_height() <= height + 125):
            self.root.geometry(f"{self.root.winfo_width()}x{max(height, self.root.winfo_height()) if visible else height}")

    def _paste_url(self) -> None:
        try:
            value = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        if value:
            self.url_var.set(value)
            self.url_entry.focus_set()
            self.url_entry.icursor("end")


    def _update_log_scrollbar(self, first: str, last: str) -> None:
        self.log_scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.log_scrollbar.grid_remove()
        else:
            self.log_scrollbar.grid()

    def _url_changed(self, *_args: str) -> None:
        self.metadata_revision += 1
        self.metadata_url = None
        self.metadata_info = {}
        self.metadata_error = False
        self.resolution_var.set(BEST_RESOLUTION)
        if self.metadata_after is not None:
            self.root.after_cancel(self.metadata_after)
        self.metadata_after = None
        self._refresh_resolutions()
        if is_valid_url(self.url_var.get()):
            self.metadata_after = self.root.after(700, self._start_metadata)

    def _refresh_resolutions(self) -> None:
        is_video = "-f" in FORMAT_OPTIONS[self.format_var.get()]
        heights = available_resolutions(self.metadata_info, self.format_var.get()) if is_video else []
        choices = [BEST_RESOLUTION] + [f"{height}p" for height in heights]
        if self.resolution_var.get() not in choices:
            self.resolution_var.set(BEST_RESOLUTION)
        self.resolution_box.configure(
            values=choices,
            state="readonly" if is_video and heights and not self.active_operation else "disabled",
        )
        if not is_video:
            hint = "Audio only."
        elif not is_valid_url(self.url_var.get()):
            hint = "Paste a URL to check available resolutions."
        elif self.metadata_url != self.url_var.get().strip():
            hint = "Checking available resolutions…"
        elif self.metadata_error:
            hint = "Could not detect resolutions; you can try the best available quality."
        elif not heights:
            hint = "No video resolutions found for this format."
        elif self.playlist_var.get():
            hint = "For playlists, the selected resolution is the maximum quality."
        else:
            hint = "Converts when needed for video editors." if self.format_var.get() == COMPATIBLE_MP4 else "Keeps the source codecs."
        self.resolution_hint.set(hint)

    def _start_metadata(self) -> None:
        self.metadata_after = None
        url = self.url_var.get().strip()
        if self.active_operation or self.metadata_loading or not is_valid_url(url):
            return
        executable = locate_yt_dlp()
        if not executable:
            self.metadata_url = url
            self.metadata_error = True
            self._refresh_resolutions()
            return
        self.metadata_loading = True
        threading.Thread(
            target=self._metadata_worker,
            args=(executable, url, self.metadata_revision), daemon=True,
        ).start()

    def _metadata_worker(self, executable: str, url: str, revision: int) -> None:
        try:
            result = subprocess.run(
                build_metadata_command(executable, url), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=60, check=False,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "Could not retrieve available resolutions.")
            info = json.loads(result.stdout)
            if not isinstance(info, dict):
                raise ValueError("Invalid video metadata.")
            if info.get("entries") is not None:
                info = next((entry for entry in info["entries"] if entry), {})
            self.messages.put(("metadata", revision, url, info, ""))
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
            self.messages.put(("metadata", revision, url, {}, str(exc)))

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Choose a download folder",
            initialdir=self.destination_var.get() or str(Path.home()),
        )
        if selected:
            self.destination_var.set(selected)

    def _open_folder(self) -> None:
        folder = self._destination()
        if folder is None:
            return
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not open the folder.\n{exc}", parent=self.root)

    def _destination(self) -> Path | None:
        value = self.destination_var.get().strip()
        if value:
            return Path(value).expanduser().absolute()
        self.detail_var.set("Choose a download folder.")
        self.destination_entry.focus_set()
        return None

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _set_running(self, running: bool, cancellable: bool = True) -> None:
        state = "disabled" if running else "normal"
        for widget in (self.download_button, self.url_entry, self.paste_button,
                       self.destination_entry, self.browse_button, self.playlist_check):
            widget.configure(state=state)
        self.tools_menu.entryconfigure(0, state=state)
        if running and cancellable:
            self.cancel_button.configure(state="normal")
            self.cancel_button.grid()
        else:
            self.cancel_button.grid_remove()
        self.format_box.configure(state="disabled" if running else "readonly")
        self._refresh_resolutions()

    def _show_progress(self, percentage: float | None) -> None:
        mode = str(self.progress.cget("mode"))
        if percentage is None:
            if mode != "indeterminate":
                self.progress_var.set(0)
                self.progress.configure(mode="indeterminate")
                self.progress.start(15)
        else:
            if mode != "determinate":
                self.progress.stop()
                self.progress.configure(mode="determinate")
            self.progress_var.set(percentage)

    def start_download(self) -> None:
        if self.active_operation:
            return

        url = self.url_var.get().strip()
        if not is_valid_url(url):
            self.detail_var.set("Enter an HTTP or HTTPS URL.")
            self.url_entry.focus_set()
            return

        executable = locate_yt_dlp()
        if not executable:
            messagebox.showerror(APP_NAME, "yt-dlp was not found. Run the installer again.", parent=self.root)
            return

        destination = self._destination()
        if destination is None:
            return
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"The selected folder is not accessible.\n{exc}", parent=self.root)
            return

        command = build_command(
            executable, url, str(destination), self.format_var.get(), self.playlist_var.get(),
            None if self.resolution_var.get() == BEST_RESOLUTION else int(self.resolution_var.get()[:-1]),
        )
        self.cancel_requested = False
        self.downloaded_files = []
        self._clear_log()
        self._show_progress(None)
        self.status_var.set("Preparing download…")
        self.detail_var.set("")
        self.active_operation = "download"
        self._set_running(True)

        threading.Thread(target=self._download_worker, args=(command,), daemon=True).start()

    def _download_worker(self, command: list[str]) -> None:
        try:
            with subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ) as process:
                self.process = process
                if self.cancel_requested:
                    self._stop_process_tree(process)
                transfer = TransferProgress([])
                item = ""
                for raw_line in process.stdout:
                    line = raw_line.rstrip("\r\n")
                    if line.startswith("TRANSFER:"):
                        index, count, formats = json.loads(line.removeprefix("TRANSFER:"))
                        item = f"Item {index} of {count} · " if index and count else f"Item {index} · " if index else ""
                        transfer = TransferProgress(formats or [])
                        self.messages.put(("phase", item + "Starting download…", ""))
                    elif line.startswith("PROGRESS:"):
                        format_id, data = json.loads(line.removeprefix("PROGRESS:"))
                        percentage = transfer.update(format_id, data)
                        if percentage == 100:
                            self.messages.put(("phase", item + "Finishing file…", ""))
                            continue
                        speed = data.get("_speed_str", "").strip()
                        eta = data.get("_eta_str", "").strip()
                        detail = "  ·  ".join(filter(None, (
                            speed if not speed.startswith("Unknown") else "",
                            f"{eta} left" if re.fullmatch(r"\d+(?::\d+)+", eta) else "",
                        )))
                        status = item + (f"Downloading {int(percentage)}%" if percentage is not None else "Downloading…")
                        self.messages.put(("progress", percentage, status, detail))
                    elif line.startswith("FILE:"):
                        self.messages.put(("file", json.loads(line.removeprefix("FILE:"))))
                    elif line.startswith(("[Merger]", "[ExtractAudio]", "[DesktopCompatible]")):
                        step = line.split("]", 1)[1].strip()
                        status = "Converting video…" if step.startswith("Converting to") else "Finishing file…"
                        self.messages.put(("phase", item + status, ""))
                    elif line.startswith(("ERROR:", "WARNING:")):
                        self.messages.put(("log", line))
                return_code = process.wait()
            self.process = None
            self.messages.put(("done", return_code, self.cancel_requested))
        except (OSError, ValueError) as exc:
            self.process = None
            self.messages.put(("error", "download", str(exc)))

    def start_update(self) -> None:
        if self.active_operation:
            return
        executable = locate_yt_dlp()
        if not executable:
            messagebox.showerror(APP_NAME, "yt-dlp was not found. Run the installer again.", parent=self.root)
            return
        self._clear_log()
        self.status_var.set("Checking for yt-dlp updates…")
        self.detail_var.set("")
        self._show_progress(None)
        self.active_operation = "update"
        self._set_running(True, cancellable=False)
        threading.Thread(target=self._update_worker, args=(executable,), daemon=True).start()

    def _update_worker(self, executable: str) -> None:
        try:
            previous_version = probe_yt_dlp(executable)
            with subprocess.Popen(
                build_update_command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding=locale.getpreferredencoding(False), errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ) as process:
                self.process = process
                diagnostics = [line.rstrip() for line in process.stdout if line.startswith(("ERROR:", "WARNING:"))]
                return_code = process.wait()
            updated_version = probe_yt_dlp(executable) if return_code == 0 else previous_version
            self.process = None
            for line in diagnostics:
                self.messages.put(("log", line))
            self.messages.put(("update_done", return_code, previous_version, updated_version))
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            self.process = None
            self.messages.put(("error", "update", str(exc)))

    def _drain_messages(self) -> None:
        try:
            while True:
                kind, *data = self.messages.get_nowait()
                if self.close_when_done and kind in {"done", "update_done", "error"}:
                    self.root.destroy()
                    return
                if kind == "metadata":
                    revision, url, info, error = data
                    self.metadata_loading = False
                    if revision != self.metadata_revision:
                        if self.metadata_after is None:
                            self._start_metadata()
                        continue
                    self.metadata_url = url
                    self.metadata_info = info
                    self.metadata_error = bool(error)
                    self._refresh_resolutions()
                elif kind in {"phase", "progress"} and not self.cancel_requested:
                    percentage, status, detail = data if kind == "progress" else (None, *data)
                    self._show_progress(percentage)
                    self.status_var.set(status)
                    self.detail_var.set(detail)
                elif kind == "file":
                    path = data[0]
                    if path not in self.downloaded_files and Path(path).is_file():
                        self.downloaded_files.append(path)
                        self._append_log(f"Saved: {path}")
                elif kind == "log":
                    self._append_log(data[0])
                elif kind == "done":
                    self._handle_done(*data)
                elif kind == "update_done":
                    self._handle_update_done(*data)
                elif kind == "error":
                    operation, error = data
                    self._finish_operation(
                        "Update failed" if operation == "update" else "Download failed",
                        "See details", 0,
                    )
                    self._append_log(error)
                    self._show_details()
        except queue.Empty:
            pass
        self.root.after(100, self._drain_messages)

    def _finish_operation(self, status: str, detail: str, progress: float) -> None:
        self.cancel_requested = False
        self.active_operation = None
        self._show_progress(progress)
        self.status_var.set(status)
        self.detail_var.set(detail)
        self._set_running(False)
        if self.metadata_url != self.url_var.get().strip() and self.metadata_after is None:
            self._start_metadata()

    def _handle_done(self, return_code: int, was_cancelled: bool) -> None:
        count = len(self.downloaded_files)
        saved = "1 file saved" if count == 1 else f"{count} files saved" if count else ""
        if was_cancelled:
            self._finish_operation("Download canceled", saved, 0)
        elif return_code == 0 and count:
            self._finish_operation("Download complete", saved, 100)
        else:
            self._finish_operation("Download incomplete" if count else "Download failed", saved or "See details", 0)
            if return_code:
                self._append_log(f"yt-dlp exited with code {return_code}.")
            else:
                self._append_log("yt-dlp did not report a saved file.")
            self._show_details()

    def _handle_update_done(self, return_code: int, previous_version: str, updated_version: str) -> None:
        if return_code:
            self._finish_operation("Update failed", "See details", 0)
            self._append_log(f"The updater exited with code {return_code}.")
            self._show_details()
        elif updated_version == previous_version:
            self._finish_operation("yt-dlp is up to date", updated_version, 0)
        else:
            self._finish_operation("yt-dlp updated", updated_version, 0)

    @staticmethod
    def _stop_process_tree(process: subprocess.Popen[str]) -> None:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
        )

    def cancel_download(self) -> None:
        if self.active_operation != "download" or self.cancel_requested:
            return
        process = self.process
        if process and process.poll() is not None:
            return
        self.cancel_requested = True
        self.status_var.set("Canceling download…")
        self.detail_var.set("")
        self.cancel_button.configure(state="disabled")
        if process:
            threading.Thread(target=self._stop_process_tree, args=(process,), daemon=True).start()

    def _on_close(self) -> None:
        if self.close_when_done:
            return
        if not self.active_operation:
            self.root.destroy()
            return
        prompt = "Stop downloading and close?" if self.active_operation == "download" else "Close when the update finishes?"
        if messagebox.askyesno(APP_NAME, prompt, parent=self.root):
            self.close_when_done = True
            if self.active_operation == "download":
                self.cancel_download()



def main() -> None:
    root = tk.Tk()
    YtDlpApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
