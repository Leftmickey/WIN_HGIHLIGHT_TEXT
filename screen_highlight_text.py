"""Screen highlight text overlay for Windows 11.

This tool shows a draggable, always-on-top highlight label on the screen.
It uses only Python's standard tkinter library, so it can run on a normal
Windows 11 Python installation without extra packages.
"""

from __future__ import annotations

import argparse
import colorsys
import platform
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


TRANSPARENT_COLOR = "#010203"
DEFAULT_TEXT = "重點提示文字"
DEFAULT_FONT = "Microsoft JhengHei UI"
DEFAULT_HIGHLIGHT = "#fff176"
DEFAULT_TEXT_COLOR = "#111111"
DEFAULT_MARQUEE_WIDTH = 720
DEFAULT_MARQUEE_SPEED = 4
DEFAULT_MARQUEE_DIRECTION = "left"
DEFAULT_COLOR_CYCLE_SPEED = 3
MAX_MARQUEE_WIDTH = 4096
MARQUEE_TICK_MS = 30
COLOR_CYCLE_TICK_MS = 50
TEXT_FILE_ENCODINGS = ("utf-8-sig", "utf-8", "cp950", "big5", "gb18030")

# Common Windows fonts shown first when available.
PREFERRED_FONTS = (
    "Microsoft JhengHei UI",
    "Microsoft JhengHei",
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "Segoe UI",
    "Arial",
    "Calibri",
    "Consolas",
    "Courier New",
    "Tahoma",
    "Verdana",
)

tk: Any = None
ttk: Any = None
colorchooser: Any = None
filedialog: Any = None
messagebox: Any = None
scrolledtext: Any = None
tkfont: Any = None


def load_tkinter() -> None:
    """Load tkinter only when the GUI is actually launched."""

    global colorchooser, filedialog, messagebox, scrolledtext, tk, tkfont, ttk

    try:
        import tkinter as tk_module
        import tkinter.font as tkfont_module
        from tkinter import colorchooser as colorchooser_module
        from tkinter import filedialog as filedialog_module
        from tkinter import messagebox as messagebox_module
        from tkinter import scrolledtext as scrolledtext_module
        from tkinter import ttk as ttk_module
    except ImportError as exc:
        raise RuntimeError(
            "找不到 tkinter。請安裝包含 Tcl/Tk 的 Python，或重新安裝 Python "
            "並確認已啟用 tkinter。"
        ) from exc

    tk = tk_module
    ttk = ttk_module
    colorchooser = colorchooser_module
    filedialog = filedialog_module
    messagebox = messagebox_module
    scrolledtext = scrolledtext_module
    tkfont = tkfont_module


def normalize_display_text(value: str) -> str:
    """Normalize newlines and keep blank placeholder text usable."""

    text = value.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return text if text.strip() else " "


def read_text_file(path: str | Path) -> str:
    """Read a text file with common Windows/Chinese encodings."""

    data = Path(path).read_bytes()
    for encoding in TEXT_FILE_ENCODINGS:
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")

    return normalize_display_text(text)


def parse_hex_color(color: str) -> tuple[float, float, float]:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid color: {color}")
    return (
        int(value[0:2], 16) / 255.0,
        int(value[2:4], 16) / 255.0,
        int(value[4:6], 16) / 255.0,
    )


def to_hex_color(red: float, green: float, blue: float) -> str:
    return (
        f"#{max(0, min(255, int(round(red * 255)))):02x}"
        f"{max(0, min(255, int(round(green * 255)))):02x}"
        f"{max(0, min(255, int(round(blue * 255)))):02x}"
    )


def shift_hue(color: str, delta: float) -> str:
    """Shift a color's hue so automatic color cycling is visible."""

    try:
        red, green, blue = parse_hex_color(color)
    except ValueError:
        red, green, blue = parse_hex_color(DEFAULT_HIGHLIGHT)

    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    if saturation < 0.18:
        saturation = 0.78
        value = max(value, 0.55)
    hue = (hue + delta) % 1.0
    next_color = to_hex_color(*colorsys.hsv_to_rgb(hue, saturation, value))
    if next_color.lower() == TRANSPARENT_COLOR.lower():
        next_color = to_hex_color(
            *colorsys.hsv_to_rgb((hue + 0.08) % 1.0, saturation, value)
        )
    return next_color


def clamp_marquee_width(width: int) -> int:
    return max(0, min(MAX_MARQUEE_WIDTH, width))


def list_available_fonts(preferred: str | None = None) -> list[str]:
    """Return system fonts with preferred Chinese/Windows fonts listed first."""

    available = {name for name in tkfont.families() if name.strip()}
    ordered: list[str] = []

    for name in PREFERRED_FONTS:
        if name in available and name not in ordered:
            ordered.append(name)

    if preferred and preferred in available and preferred not in ordered:
        ordered.insert(0, preferred)

    ordered.extend(sorted(name for name in available if name not in ordered))
    return ordered


def resolve_font_family(requested: str) -> str:
    """Pick a usable font family, falling back when the requested font is missing."""

    available = list_available_fonts(requested)
    if requested in available:
        return requested

    for candidate in PREFERRED_FONTS:
        if candidate in available:
            return candidate

    return available[0] if available else requested


class HighlightOverlay:
    """Owns the borderless on-screen highlight window."""

    def __init__(
        self,
        root: tk.Tk,
        text: str,
        font_family: str,
        font_size: int,
        bold: bool,
        highlight_color: str,
        text_color: str,
        opacity: float,
        x: int,
        y: int,
        marquee: bool = False,
        marquee_speed: int = DEFAULT_MARQUEE_SPEED,
        marquee_width: int = DEFAULT_MARQUEE_WIDTH,
        marquee_direction: str = DEFAULT_MARQUEE_DIRECTION,
        highlight_cycle: bool = False,
        text_cycle: bool = False,
        color_cycle_speed: int = DEFAULT_COLOR_CYCLE_SPEED,
    ) -> None:
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.title("Screen Highlight Text")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", opacity)

        # Windows supports a transparent color key. This keeps only the label
        # visible instead of drawing a full rectangular application window.
        if platform.system() == "Windows":
            self.window.configure(bg=TRANSPARENT_COLOR)
            self.window.attributes("-transparentcolor", TRANSPARENT_COLOR)
        else:
            self.window.configure(bg=highlight_color)

        self.source_text = normalize_display_text(text)
        self.font_family = font_family
        self.font_size = font_size
        self.bold = bold
        self.opacity = opacity
        self.highlight_color = highlight_color
        self.text_color = text_color
        self.display_highlight_color = highlight_color
        self.display_text_color = text_color
        self.marquee_enabled = marquee
        self.marquee_speed = max(1, min(20, marquee_speed))
        self.marquee_width = clamp_marquee_width(marquee_width)
        self.marquee_direction = (
            "right" if marquee_direction == "right" else "left"
        )
        self.highlight_cycle = highlight_cycle
        self.text_cycle = text_cycle
        self.color_cycle_speed = max(1, min(20, color_cycle_speed))
        self.on_colors_changed: Callable[[str, str], None] | None = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self._marquee_job: str | None = None
        self._color_job: str | None = None
        self._text_x = 0.0
        self._text_width = 0
        self._content_height = 0
        self._viewport_width = 1

        self.content = tk.Frame(self.window, bg=self.display_highlight_color, bd=0)
        self.content.pack()

        self.label = tk.Label(
            self.content,
            text=self.source_text,
            bg=self.display_highlight_color,
            fg=self.display_text_color,
            font=self._font_tuple(),
            justify="left",
            anchor="w",
            padx=24,
            pady=12,
            bd=0,
            relief="flat",
        )
        self.canvas = tk.Canvas(
            self.content,
            bg=self.display_highlight_color,
            highlightthickness=0,
            bd=0,
        )
        self.text_id: int | None = None

        for widget in (self.window, self.content, self.label, self.canvas):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)

        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda _event: self.root.quit())
        self.window.bind("<Destroy>", self._on_destroy)

        self._rebuild_view(reset_position=True)
        self._sync_color_cycle()

    def _font_tuple(self) -> tuple[str, int] | tuple[str, int, str]:
        if self.bold:
            return (self.font_family, self.font_size, "bold")
        return (self.font_family, self.font_size)

    def _measure_text(self) -> tuple[int, int]:
        font = tkfont.Font(font=self._font_tuple())
        lines = self.source_text.split("\n") or [" "]
        width = max((font.measure(line) for line in lines), default=1)
        line_height = max(font.metrics("linespace"), self.font_size)
        height = line_height * max(len(lines), 1) + 24
        return max(width, 1), height

    def _effective_viewport_width(self) -> int:
        if self.marquee_width <= 0:
            return max(self._text_width + 48, 1)
        return self.marquee_width

    def _stop_marquee(self) -> None:
        if self._marquee_job is not None:
            try:
                self.window.after_cancel(self._marquee_job)
            except tk.TclError:
                pass
            self._marquee_job = None

    def _stop_color_cycle(self) -> None:
        if self._color_job is not None:
            try:
                self.window.after_cancel(self._color_job)
            except tk.TclError:
                pass
            self._color_job = None

    def _on_destroy(self, _event: tk.Event | None = None) -> None:
        self._stop_marquee()
        self._stop_color_cycle()

    def _notify_colors_changed(self) -> None:
        if self.on_colors_changed is not None:
            self.on_colors_changed(
                self.display_highlight_color, self.display_text_color
            )

    def _apply_display_colors(self) -> None:
        self.content.configure(bg=self.display_highlight_color)
        self.label.configure(
            bg=self.display_highlight_color, fg=self.display_text_color
        )
        self.canvas.configure(bg=self.display_highlight_color)
        if self.text_id is not None:
            self.canvas.itemconfigure(self.text_id, fill=self.display_text_color)
        self._notify_colors_changed()

    def _rebuild_view(self, reset_position: bool = False) -> None:
        self._stop_marquee()
        self.label.pack_forget()
        self.canvas.pack_forget()

        text_width, content_height = self._measure_text()
        self._text_width = text_width
        self._content_height = content_height
        self._viewport_width = self._effective_viewport_width()

        if self.marquee_enabled:
            self.canvas.configure(
                width=self._viewport_width,
                height=content_height,
                bg=self.display_highlight_color,
            )
            self.canvas.delete("all")
            if reset_position:
                if self.marquee_direction == "right":
                    self._text_x = float(-self._text_width)
                else:
                    self._text_x = float(self._viewport_width)
            self.text_id = self.canvas.create_text(
                self._text_x,
                content_height / 2,
                text=self.source_text,
                anchor="w",
                justify="left",
                fill=self.display_text_color,
                font=self._font_tuple(),
            )
            self.canvas.pack()
            self._tick_marquee()
        else:
            self.text_id = None
            self.label.configure(
                text=self.source_text,
                bg=self.display_highlight_color,
                fg=self.display_text_color,
                font=self._font_tuple(),
                justify="left",
                anchor="w",
            )
            self.label.pack()

        self.content.configure(bg=self.display_highlight_color)
        self.window.update_idletasks()

    def _tick_marquee(self) -> None:
        if not self.marquee_enabled or self.text_id is None:
            return

        if self.marquee_direction == "right":
            self._text_x += self.marquee_speed
            if self._text_x > self._viewport_width:
                self._text_x = float(-self._text_width)
        else:
            self._text_x -= self.marquee_speed
            if self._text_x + self._text_width < 0:
                self._text_x = float(self._viewport_width)

        self.canvas.coords(self.text_id, self._text_x, self._content_height / 2)
        self._marquee_job = self.window.after(MARQUEE_TICK_MS, self._tick_marquee)

    def _sync_color_cycle(self) -> None:
        self._stop_color_cycle()
        if self.highlight_cycle or self.text_cycle:
            self._tick_color_cycle()
        else:
            self.display_highlight_color = self.highlight_color
            self.display_text_color = self.text_color
            self._apply_display_colors()

    def _tick_color_cycle(self) -> None:
        if not (self.highlight_cycle or self.text_cycle):
            return

        hue_step = 0.004 * self.color_cycle_speed
        if self.highlight_cycle:
            self.display_highlight_color = shift_hue(
                self.display_highlight_color, hue_step
            )
        else:
            self.display_highlight_color = self.highlight_color

        if self.text_cycle:
            self.display_text_color = shift_hue(self.display_text_color, hue_step)
        else:
            self.display_text_color = self.text_color

        self._apply_display_colors()
        self._color_job = self.window.after(COLOR_CYCLE_TICK_MS, self._tick_color_cycle)

    def set_text(self, value: str) -> None:
        self.source_text = normalize_display_text(value)
        self._rebuild_view(reset_position=False)

    def set_font_family(self, value: str) -> None:
        self.font_family = value
        self._rebuild_view(reset_position=False)

    def set_font_size(self, value: int) -> None:
        self.font_size = value
        self._rebuild_view(reset_position=False)

    def set_bold(self, value: bool) -> None:
        self.bold = value
        self._rebuild_view(reset_position=False)

    def set_opacity(self, value: float) -> None:
        self.opacity = value
        self.window.attributes("-alpha", value)

    def set_highlight_color(self, value: str) -> None:
        self.highlight_color = value
        if not self.highlight_cycle:
            self.display_highlight_color = value
            self._apply_display_colors()
        else:
            self.display_highlight_color = value

    def set_text_color(self, value: str) -> None:
        self.text_color = value
        if not self.text_cycle:
            self.display_text_color = value
            self._apply_display_colors()
        else:
            self.display_text_color = value

    def set_highlight_cycle(self, enabled: bool) -> None:
        self.highlight_cycle = enabled
        if not enabled:
            self.display_highlight_color = self.highlight_color
        self._sync_color_cycle()

    def set_text_cycle(self, enabled: bool) -> None:
        self.text_cycle = enabled
        if not enabled:
            self.display_text_color = self.text_color
        self._sync_color_cycle()

    def set_color_cycle_speed(self, speed: int) -> None:
        self.color_cycle_speed = max(1, min(20, speed))

    def set_marquee_enabled(self, enabled: bool) -> None:
        if self.marquee_enabled == enabled:
            return
        self.marquee_enabled = enabled
        self._rebuild_view(reset_position=True)

    def set_marquee_speed(self, speed: int) -> None:
        self.marquee_speed = max(1, min(20, speed))

    def set_marquee_width(self, width: int) -> None:
        self.marquee_width = clamp_marquee_width(width)
        if self.marquee_enabled:
            self._rebuild_view(reset_position=False)

    def set_marquee_direction(self, direction: str) -> None:
        next_direction = "right" if direction == "right" else "left"
        if self.marquee_direction == next_direction:
            return
        self.marquee_direction = next_direction
        if self.marquee_enabled:
            self._rebuild_view(reset_position=True)

    def toggle_visibility(self, visible: bool) -> None:
        if visible:
            self.window.deiconify()
            self.window.attributes("-topmost", True)
            if self.marquee_enabled and self._marquee_job is None:
                self._tick_marquee()
            self._sync_color_cycle()
        else:
            self._stop_marquee()
            self._stop_color_cycle()
            self.window.withdraw()

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_start_x = event.x_root - self.window.winfo_x()
        self.drag_start_y = event.y_root - self.window.winfo_y()

    def _drag(self, event: tk.Event) -> None:
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.window.geometry(f"+{x}+{y}")


class ControlPanel:
    """Control panel for editing highlight text appearance."""

    def __init__(self, root: tk.Tk, overlay: HighlightOverlay) -> None:
        self.root = root
        self.overlay = overlay
        self.visible_var = tk.BooleanVar(value=True)
        self.font_var = tk.StringVar(value=overlay.font_family)
        self.size_var = tk.IntVar(value=overlay.font_size)
        self.size_label_var = tk.StringVar(value=f"{overlay.font_size} px")
        self.bold_var = tk.BooleanVar(value=overlay.bold)
        self.opacity_var = tk.IntVar(value=round(overlay.opacity * 100))
        self.opacity_label_var = tk.StringVar(
            value=f"{round(overlay.opacity * 100)}%"
        )
        self.highlight_color_var = tk.StringVar(value=overlay.display_highlight_color)
        self.text_color_var = tk.StringVar(value=overlay.display_text_color)
        self.highlight_cycle_var = tk.BooleanVar(value=overlay.highlight_cycle)
        self.text_cycle_var = tk.BooleanVar(value=overlay.text_cycle)
        self.color_speed_var = tk.IntVar(value=overlay.color_cycle_speed)
        self.color_speed_label_var = tk.StringVar(
            value=str(overlay.color_cycle_speed)
        )
        self.marquee_var = tk.BooleanVar(value=overlay.marquee_enabled)
        self.direction_var = tk.StringVar(value=overlay.marquee_direction)
        self.speed_var = tk.IntVar(value=overlay.marquee_speed)
        self.speed_label_var = tk.StringVar(value=f"{overlay.marquee_speed}")
        self.width_var = tk.IntVar(value=overlay.marquee_width)
        self.width_label_var = tk.StringVar(self._format_width(overlay.marquee_width))
        self.file_path_var = tk.StringVar(value="")
        self._text_update_job: str | None = None

        self.root.title("螢幕 Highlight 文字控制台")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)
        self.root.bind("<Escape>", lambda _event: self.root.quit())
        self.root.bind("<Control-o>", self._load_text_file)
        self.root.bind("<Control-O>", self._load_text_file)
        self.overlay.on_colors_changed = self._on_overlay_colors_changed

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        row = 0

        # 1. 修改文字（可多行 / 讀取 TXT）
        header = ttk.Frame(frame)
        header.grid(row=row, column=0, columnspan=3, sticky="ew")
        ttk.Label(header, text="1. 修改文字（可多行）").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="載入 TXT", command=self._load_text_file).grid(
            row=0, column=1, sticky="e", padx=(12, 0)
        )
        header.columnconfigure(0, weight=1)
        row += 1

        self.text_box = scrolledtext.ScrolledText(
            frame,
            width=46,
            height=6,
            wrap="word",
            font=("Microsoft JhengHei UI", 11),
        )
        self.text_box.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 4))
        self.text_box.insert("1.0", overlay.source_text)
        self.text_box.bind("<KeyRelease>", self._schedule_text_update)
        row += 1

        ttk.Label(frame, textvariable=self.file_path_var, foreground="#555555").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )
        row += 1

        # 2. 選字型
        ttk.Label(frame, text="2. 選字型").grid(row=row, column=0, sticky="w")
        row += 1
        font_row = ttk.Frame(frame)
        font_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        font_row.columnconfigure(0, weight=1)
        font_combo = ttk.Combobox(
            font_row,
            textvariable=self.font_var,
            values=list_available_fonts(overlay.font_family),
            width=34,
            state="readonly",
        )
        font_combo.grid(row=0, column=0, sticky="ew")
        font_combo.bind("<<ComboboxSelected>>", self._update_font)
        ttk.Checkbutton(
            font_row,
            text="粗體",
            variable=self.bold_var,
            command=self._update_bold,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))
        row += 1

        # 3. 調整字體大小
        ttk.Label(frame, text="3. 調整字體大小").grid(row=row, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.size_label_var).grid(
            row=row, column=2, sticky="e"
        )
        row += 1
        size_row = ttk.Frame(frame)
        size_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        size_row.columnconfigure(0, weight=1)
        size_scale = ttk.Scale(
            size_row,
            from_=12,
            to=120,
            orient="horizontal",
            variable=self.size_var,
            command=self._update_size_from_scale,
        )
        size_scale.grid(row=0, column=0, sticky="ew")
        size_spinbox = ttk.Spinbox(
            size_row,
            from_=12,
            to=120,
            textvariable=self.size_var,
            width=6,
            command=self._update_size,
        )
        size_spinbox.grid(row=0, column=1, sticky="e", padx=(10, 0))
        size_spinbox.bind("<KeyRelease>", self._update_size)
        size_spinbox.bind("<FocusOut>", self._update_size)
        row += 1

        # 4. 調整透明度
        ttk.Label(frame, text="4. 調整透明度").grid(row=row, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.opacity_label_var).grid(
            row=row, column=2, sticky="e"
        )
        row += 1
        opacity_scale = ttk.Scale(
            frame,
            from_=20,
            to=100,
            orient="horizontal",
            variable=self.opacity_var,
            command=self._update_opacity,
        )
        opacity_scale.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        row += 1

        # 5. 更換高亮底色
        ttk.Label(frame, text="5. 更換高亮底色").grid(row=row, column=0, sticky="w")
        row += 1
        highlight_row = ttk.Frame(frame)
        highlight_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        ttk.Button(
            highlight_row, text="選擇高亮底色", command=self._choose_highlight
        ).grid(row=0, column=0, sticky="w")
        self.highlight_swatch = tk.Label(
            highlight_row,
            text="  ",
            width=4,
            relief="solid",
            bd=1,
            bg=overlay.display_highlight_color,
        )
        self.highlight_swatch.grid(row=0, column=1, sticky="w", padx=(10, 6))
        ttk.Label(highlight_row, textvariable=self.highlight_color_var).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Checkbutton(
            highlight_row,
            text="自動變色",
            variable=self.highlight_cycle_var,
            command=self._toggle_highlight_cycle,
        ).grid(row=0, column=3, sticky="w", padx=(12, 0))
        row += 1

        # 6. 更換文字顏色
        ttk.Label(frame, text="6. 更換文字顏色").grid(row=row, column=0, sticky="w")
        row += 1
        text_color_row = ttk.Frame(frame)
        text_color_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        ttk.Button(
            text_color_row, text="選擇文字顏色", command=self._choose_text
        ).grid(row=0, column=0, sticky="w")
        self.text_swatch = tk.Label(
            text_color_row,
            text="  ",
            width=4,
            relief="solid",
            bd=1,
            bg=overlay.display_text_color,
        )
        self.text_swatch.grid(row=0, column=1, sticky="w", padx=(10, 6))
        ttk.Label(text_color_row, textvariable=self.text_color_var).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Checkbutton(
            text_color_row,
            text="自動變色",
            variable=self.text_cycle_var,
            command=self._toggle_text_cycle,
        ).grid(row=0, column=3, sticky="w", padx=(12, 0))
        row += 1

        ttk.Label(frame, text="變色速度").grid(row=row, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.color_speed_label_var).grid(
            row=row, column=2, sticky="e"
        )
        row += 1
        color_speed_scale = ttk.Scale(
            frame,
            from_=1,
            to=20,
            orient="horizontal",
            variable=self.color_speed_var,
            command=self._update_color_speed,
        )
        color_speed_scale.grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12)
        )
        row += 1

        # 7. 走馬燈模式
        ttk.Label(frame, text="7. 走馬燈模式").grid(row=row, column=0, sticky="w")
        row += 1
        marquee_row = ttk.Frame(frame)
        marquee_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        ttk.Checkbutton(
            marquee_row,
            text="啟用走馬燈",
            variable=self.marquee_var,
            command=self._toggle_marquee,
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            marquee_row,
            text="顯示高亮文字",
            variable=self.visible_var,
            command=self._toggle_visibility,
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))
        row += 1

        ttk.Label(frame, text="走馬燈方向").grid(row=row, column=0, sticky="w")
        row += 1
        direction_row = ttk.Frame(frame)
        direction_row.grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 12))
        ttk.Radiobutton(
            direction_row,
            text="向左",
            value="left",
            variable=self.direction_var,
            command=self._update_direction,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            direction_row,
            text="向右",
            value="right",
            variable=self.direction_var,
            command=self._update_direction,
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))
        row += 1

        ttk.Label(frame, text="走馬燈速度").grid(row=row, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.speed_label_var).grid(
            row=row, column=2, sticky="e"
        )
        row += 1
        speed_scale = ttk.Scale(
            frame,
            from_=1,
            to=20,
            orient="horizontal",
            variable=self.speed_var,
            command=self._update_speed,
        )
        speed_scale.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        row += 1

        ttk.Label(frame, text="走馬燈寬度（0=自動，最大 4096）").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(frame, textvariable=self.width_label_var).grid(
            row=row, column=2, sticky="e"
        )
        row += 1
        width_row = ttk.Frame(frame)
        width_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        width_row.columnconfigure(0, weight=1)
        width_scale = ttk.Scale(
            width_row,
            from_=0,
            to=MAX_MARQUEE_WIDTH,
            orient="horizontal",
            variable=self.width_var,
            command=self._update_width_from_scale,
        )
        width_scale.grid(row=0, column=0, sticky="ew")
        width_spinbox = ttk.Spinbox(
            width_row,
            from_=0,
            to=MAX_MARQUEE_WIDTH,
            textvariable=self.width_var,
            width=7,
            command=self._update_width,
        )
        width_spinbox.grid(row=0, column=1, sticky="e", padx=(10, 0))
        width_spinbox.bind("<KeyRelease>", self._update_width)
        width_spinbox.bind("<FocusOut>", self._update_width)
        row += 1

        tips = (
            "操作提示：\n"
            "1. 文字框可輸入多行；也可按「載入 TXT」或 Ctrl+O。\n"
            "2. 底色／文字可開啟自動變色；走馬燈可選向左或向右。\n"
            "3. 走馬燈寬度可設 0~4096，0 代表依文字自動寬度。\n"
            "4. 按 Esc 或關閉控制台可結束程式。"
        )
        ttk.Label(frame, text=tips, justify="left").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

    @staticmethod
    def _format_width(width: int) -> str:
        if width <= 0:
            return "自動"
        return f"{width} px"

    def _on_overlay_colors_changed(
        self, highlight_color: str, text_color: str
    ) -> None:
        self.highlight_color_var.set(highlight_color)
        self.text_color_var.set(text_color)
        self.highlight_swatch.configure(bg=highlight_color)
        self.text_swatch.configure(bg=text_color)

    def _schedule_text_update(self, _event: tk.Event | None = None) -> None:
        if self._text_update_job is not None:
            try:
                self.root.after_cancel(self._text_update_job)
            except tk.TclError:
                pass
        self._text_update_job = self.root.after(120, self._update_text)

    def _update_text(self, _event: tk.Event | None = None) -> None:
        self._text_update_job = None
        text = self.text_box.get("1.0", "end-1c")
        self.overlay.set_text(text)

    def _load_text_file(self, _event: tk.Event | None = None) -> str | None:
        path = filedialog.askopenfilename(
            title="選擇文字檔",
            filetypes=[
                ("文字檔", "*.txt"),
                ("所有檔案", "*.*"),
            ],
        )
        if not path:
            return "break"

        try:
            content = read_text_file(path)
        except OSError as exc:
            messagebox.showerror("讀取失敗", f"無法讀取檔案：\n{path}\n\n{exc}")
            return "break"

        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content)
        self.file_path_var.set(f"已載入：{path}")
        self.overlay.set_text(content)
        return "break"

    def _update_font(self, _event: tk.Event | None = None) -> None:
        font_name = self.font_var.get().strip()
        if font_name:
            self.overlay.set_font_family(font_name)

    def _update_bold(self) -> None:
        self.overlay.set_bold(self.bold_var.get())

    def _update_size_from_scale(self, _value: str | None = None) -> None:
        size = int(round(float(self.size_var.get())))
        self.size_var.set(size)
        self._apply_size(size)

    def _update_size(self, _event: tk.Event | None = None) -> None:
        try:
            size = int(self.size_var.get())
        except (tk.TclError, ValueError, TypeError):
            return
        self._apply_size(size)

    def _apply_size(self, size: int) -> None:
        if 12 <= size <= 120:
            self.size_label_var.set(f"{size} px")
            self.overlay.set_font_size(size)

    def _update_opacity(self, _value: str | None = None) -> None:
        opacity_percent = int(round(float(self.opacity_var.get())))
        opacity_percent = max(20, min(100, opacity_percent))
        self.opacity_var.set(opacity_percent)
        self.opacity_label_var.set(f"{opacity_percent}%")
        self.overlay.set_opacity(opacity_percent / 100)

    def _choose_highlight(self) -> None:
        color = colorchooser.askcolor(
            title="選擇高亮底色", initialcolor=self.overlay.highlight_color
        )[1]
        if color:
            self.overlay.set_highlight_color(color)
            self.highlight_color_var.set(color)
            self.highlight_swatch.configure(bg=color)

    def _choose_text(self) -> None:
        color = colorchooser.askcolor(
            title="選擇文字顏色", initialcolor=self.overlay.text_color
        )[1]
        if color:
            self.overlay.set_text_color(color)
            self.text_color_var.set(color)
            self.text_swatch.configure(bg=color)

    def _toggle_highlight_cycle(self) -> None:
        self.overlay.set_highlight_cycle(self.highlight_cycle_var.get())

    def _toggle_text_cycle(self) -> None:
        self.overlay.set_text_cycle(self.text_cycle_var.get())

    def _update_color_speed(self, _value: str | None = None) -> None:
        speed = int(round(float(self.color_speed_var.get())))
        speed = max(1, min(20, speed))
        self.color_speed_var.set(speed)
        self.color_speed_label_var.set(str(speed))
        self.overlay.set_color_cycle_speed(speed)

    def _toggle_marquee(self) -> None:
        self.overlay.set_marquee_enabled(self.marquee_var.get())

    def _update_direction(self) -> None:
        self.overlay.set_marquee_direction(self.direction_var.get())

    def _update_speed(self, _value: str | None = None) -> None:
        speed = int(round(float(self.speed_var.get())))
        speed = max(1, min(20, speed))
        self.speed_var.set(speed)
        self.speed_label_var.set(str(speed))
        self.overlay.set_marquee_speed(speed)

    def _update_width_from_scale(self, _value: str | None = None) -> None:
        width = int(round(float(self.width_var.get())))
        self.width_var.set(width)
        self._apply_width(width)

    def _update_width(self, _event: tk.Event | None = None) -> None:
        try:
            width = int(self.width_var.get())
        except (tk.TclError, ValueError, TypeError):
            return
        self._apply_width(width)

    def _apply_width(self, width: int) -> None:
        width = clamp_marquee_width(width)
        self.width_var.set(width)
        self.width_label_var.set(self._format_width(width))
        self.overlay.set_marquee_width(width)

    def _toggle_visibility(self) -> None:
        self.overlay.toggle_visibility(self.visible_var.get())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="在 Windows 11 螢幕上顯示可拖曳的高亮文字。"
    )
    parser.add_argument("--text", default=DEFAULT_TEXT, help="啟動時顯示的文字")
    parser.add_argument(
        "--file",
        dest="text_file",
        help="從外部 .txt 檔讀取顯示文字（優先於 --text）",
    )
    parser.add_argument(
        "--font",
        default=DEFAULT_FONT,
        help=f"啟動時的字型名稱，預設 {DEFAULT_FONT}",
    )
    parser.add_argument(
        "--font-size", type=int, default=40, help="啟動時的文字大小，預設 40"
    )
    parser.add_argument(
        "--bold",
        dest="bold",
        action="store_true",
        default=True,
        help="使用粗體（預設開啟）",
    )
    parser.add_argument(
        "--no-bold",
        dest="bold",
        action="store_false",
        help="關閉粗體",
    )
    parser.add_argument(
        "--highlight-color",
        default=DEFAULT_HIGHLIGHT,
        help="高亮底色，例如 #fff176",
    )
    parser.add_argument(
        "--text-color", default=DEFAULT_TEXT_COLOR, help="文字顏色，例如 #111111"
    )
    parser.add_argument(
        "--highlight-cycle",
        action="store_true",
        help="啟動時啟用高亮底色自動變色",
    )
    parser.add_argument(
        "--text-cycle",
        action="store_true",
        help="啟動時啟用文字顏色自動變色",
    )
    parser.add_argument(
        "--color-cycle-speed",
        type=int,
        default=DEFAULT_COLOR_CYCLE_SPEED,
        help="變色速度，範圍 1 到 20，預設 3",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.85,
        help="透明度，範圍 0.2 到 1.0，預設 0.85",
    )
    parser.add_argument(
        "--marquee",
        action="store_true",
        help="啟動時啟用走馬燈模式",
    )
    parser.add_argument(
        "--marquee-direction",
        choices=("left", "right"),
        default=DEFAULT_MARQUEE_DIRECTION,
        help="走馬燈方向：left 或 right，預設 left",
    )
    parser.add_argument(
        "--marquee-speed",
        type=int,
        default=DEFAULT_MARQUEE_SPEED,
        help="走馬燈速度，範圍 1 到 20，預設 4",
    )
    parser.add_argument(
        "--marquee-width",
        type=int,
        default=DEFAULT_MARQUEE_WIDTH,
        help="走馬燈高亮條寬度，範圍 0 到 4096，0=自動，預設 720",
    )
    parser.add_argument("--x", type=int, default=120, help="高亮文字初始 X 座標")
    parser.add_argument("--y", type=int, default=120, help="高亮文字初始 Y 座標")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    opacity = max(0.2, min(1.0, args.opacity))
    font_size = max(12, min(120, args.font_size))
    marquee_speed = max(1, min(20, args.marquee_speed))
    marquee_width = clamp_marquee_width(args.marquee_width)
    color_cycle_speed = max(1, min(20, args.color_cycle_speed))

    if args.text_file:
        try:
            startup_text = read_text_file(args.text_file)
        except OSError as exc:
            raise RuntimeError(f"無法讀取文字檔：{args.text_file}\n{exc}") from exc
    else:
        startup_text = normalize_display_text(args.text)

    load_tkinter()

    root = tk.Tk()
    root.withdraw()

    if platform.system() != "Windows":
        messagebox.showwarning(
            "非 Windows 系統",
            "此工具主要針對 Windows 11 設計；目前系統仍可嘗試執行，"
            "但透明背景效果可能不同。",
        )

    font_family = resolve_font_family(args.font)

    overlay = HighlightOverlay(
        root=root,
        text=startup_text,
        font_family=font_family,
        font_size=font_size,
        bold=args.bold,
        highlight_color=args.highlight_color,
        text_color=args.text_color,
        opacity=opacity,
        x=args.x,
        y=args.y,
        marquee=args.marquee,
        marquee_speed=marquee_speed,
        marquee_width=marquee_width,
        marquee_direction=args.marquee_direction,
        highlight_cycle=args.highlight_cycle,
        text_cycle=args.text_cycle,
        color_cycle_speed=color_cycle_speed,
    )

    root.deiconify()
    panel = ControlPanel(root, overlay)
    if args.text_file:
        panel.file_path_var.set(f"已載入：{args.text_file}")
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
