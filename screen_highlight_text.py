"""Screen highlight text overlay for Windows 11.

This tool shows a draggable, always-on-top highlight label on the screen.
It uses only Python's standard tkinter library, so it can run on a normal
Windows 11 Python installation without extra packages.
"""

from __future__ import annotations

import argparse
import platform
import sys
from typing import Any


TRANSPARENT_COLOR = "#010203"
DEFAULT_TEXT = "重點提示文字"
DEFAULT_FONT = "Microsoft JhengHei UI"
DEFAULT_HIGHLIGHT = "#fff176"
DEFAULT_TEXT_COLOR = "#111111"

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
messagebox: Any = None
tkfont: Any = None


def load_tkinter() -> None:
    """Load tkinter only when the GUI is actually launched."""

    global colorchooser, messagebox, tk, tkfont, ttk

    try:
        import tkinter as tk_module
        import tkinter.font as tkfont_module
        from tkinter import colorchooser as colorchooser_module
        from tkinter import messagebox as messagebox_module
        from tkinter import ttk as ttk_module
    except ImportError as exc:
        raise RuntimeError(
            "找不到 tkinter。請安裝包含 Tcl/Tk 的 Python，或重新安裝 Python "
            "並確認已啟用 tkinter。"
        ) from exc

    tk = tk_module
    ttk = ttk_module
    colorchooser = colorchooser_module
    messagebox = messagebox_module
    tkfont = tkfont_module


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

        self.text_var = tk.StringVar(value=text)
        self.font_family = font_family
        self.font_size = font_size
        self.bold = bold
        self.opacity = opacity
        self.highlight_color = highlight_color
        self.text_color = text_color
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.label = tk.Label(
            self.window,
            textvariable=self.text_var,
            bg=self.highlight_color,
            fg=self.text_color,
            font=self._font_tuple(),
            padx=24,
            pady=12,
            bd=0,
            relief="flat",
        )
        self.label.pack()
        self.label.bind("<ButtonPress-1>", self._start_drag)
        self.label.bind("<B1-Motion>", self._drag)

        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda _event: self.root.quit())

    def _font_tuple(self) -> tuple[str, int] | tuple[str, int, str]:
        if self.bold:
            return (self.font_family, self.font_size, "bold")
        return (self.font_family, self.font_size)

    def _apply_font(self) -> None:
        self.label.configure(font=self._font_tuple())
        self.window.update_idletasks()

    def set_text(self, value: str) -> None:
        self.text_var.set(value or " ")
        self.window.update_idletasks()

    def set_font_family(self, value: str) -> None:
        self.font_family = value
        self._apply_font()

    def set_font_size(self, value: int) -> None:
        self.font_size = value
        self._apply_font()

    def set_bold(self, value: bool) -> None:
        self.bold = value
        self._apply_font()

    def set_opacity(self, value: float) -> None:
        self.opacity = value
        self.window.attributes("-alpha", value)

    def set_highlight_color(self, value: str) -> None:
        self.highlight_color = value
        self.label.configure(bg=value)

    def set_text_color(self, value: str) -> None:
        self.text_color = value
        self.label.configure(fg=value)

    def toggle_visibility(self, visible: bool) -> None:
        if visible:
            self.window.deiconify()
            self.window.attributes("-topmost", True)
        else:
            self.window.withdraw()

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _drag(self, event: tk.Event) -> None:
        x = self.window.winfo_x() + event.x - self.drag_start_x
        y = self.window.winfo_y() + event.y - self.drag_start_y
        self.window.geometry(f"+{x}+{y}")


class ControlPanel:
    """Control panel for changing text, font, colors, opacity, and size."""

    def __init__(self, root: tk.Tk, overlay: HighlightOverlay) -> None:
        self.root = root
        self.overlay = overlay
        self.visible_var = tk.BooleanVar(value=True)
        self.text_var = tk.StringVar(value=overlay.text_var.get())
        self.font_var = tk.StringVar(value=overlay.font_family)
        self.size_var = tk.IntVar(value=overlay.font_size)
        self.bold_var = tk.BooleanVar(value=overlay.bold)
        self.opacity_var = tk.IntVar(value=round(overlay.opacity * 100))

        self.root.title("螢幕 Highlight 文字控制台")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)
        self.root.bind("<Escape>", lambda _event: self.root.quit())

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="顯示文字").grid(row=0, column=0, sticky="w")
        text_entry = ttk.Entry(frame, textvariable=self.text_var, width=42)
        text_entry.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        text_entry.bind("<KeyRelease>", self._update_text)

        ttk.Label(frame, text="字型").grid(row=2, column=0, sticky="w")
        font_combo = ttk.Combobox(
            frame,
            textvariable=self.font_var,
            values=list_available_fonts(overlay.font_family),
            width=28,
            state="readonly",
        )
        font_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        font_combo.bind("<<ComboboxSelected>>", self._update_font)

        ttk.Checkbutton(
            frame,
            text="粗體",
            variable=self.bold_var,
            command=self._update_bold,
        ).grid(row=3, column=2, sticky="w", padx=(8, 0), pady=(4, 12))

        ttk.Label(frame, text="字體大小").grid(row=4, column=0, sticky="w")
        size_spinbox = ttk.Spinbox(
            frame,
            from_=12,
            to=120,
            textvariable=self.size_var,
            width=8,
            command=self._update_size,
        )
        size_spinbox.grid(row=5, column=0, sticky="w", pady=(4, 12))
        size_spinbox.bind("<KeyRelease>", self._update_size)

        ttk.Label(frame, text="透明度").grid(row=4, column=1, sticky="w")
        opacity_scale = ttk.Scale(
            frame,
            from_=20,
            to=100,
            orient="horizontal",
            variable=self.opacity_var,
            command=self._update_opacity,
            length=150,
        )
        opacity_scale.grid(row=5, column=1, columnspan=2, sticky="ew", pady=(4, 12))

        ttk.Button(frame, text="選擇高亮色", command=self._choose_highlight).grid(
            row=6, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(frame, text="選擇文字色", command=self._choose_text).grid(
            row=6, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Checkbutton(
            frame,
            text="顯示高亮文字",
            variable=self.visible_var,
            command=self._toggle_visibility,
        ).grid(row=6, column=2, sticky="w")

        tips = (
            "操作提示：\n"
            "1. 拖曳高亮文字可移動位置。\n"
            "2. 可用下拉選單切換系統字型，並開關粗體。\n"
            "3. 按 Esc 或關閉控制台可結束程式。\n"
            "4. 若在簡報或會議中使用，請先測試是否會被分享軟體擷取。"
        )
        ttk.Label(frame, text=tips, justify="left").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(14, 0)
        )

    def _update_text(self, _event: tk.Event | None = None) -> None:
        self.overlay.set_text(self.text_var.get())

    def _update_font(self, _event: tk.Event | None = None) -> None:
        font_name = self.font_var.get().strip()
        if font_name:
            self.overlay.set_font_family(font_name)

    def _update_bold(self) -> None:
        self.overlay.set_bold(self.bold_var.get())

    def _update_size(self, _event: tk.Event | None = None) -> None:
        try:
            size = int(self.size_var.get())
        except tk.TclError:
            return

        if 12 <= size <= 120:
            self.overlay.set_font_size(size)

    def _update_opacity(self, _value: str | None = None) -> None:
        opacity = max(20, min(100, self.opacity_var.get())) / 100
        self.overlay.set_opacity(opacity)

    def _choose_highlight(self) -> None:
        color = colorchooser.askcolor(
            title="選擇高亮顏色", initialcolor=self.overlay.highlight_color
        )[1]
        if color:
            self.overlay.set_highlight_color(color)

    def _choose_text(self) -> None:
        color = colorchooser.askcolor(
            title="選擇文字顏色", initialcolor=self.overlay.text_color
        )[1]
        if color:
            self.overlay.set_text_color(color)

    def _toggle_visibility(self) -> None:
        self.overlay.toggle_visibility(self.visible_var.get())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="在 Windows 11 螢幕上顯示可拖曳的高亮文字。"
    )
    parser.add_argument("--text", default=DEFAULT_TEXT, help="啟動時顯示的文字")
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
        "--opacity",
        type=float,
        default=0.85,
        help="透明度，範圍 0.2 到 1.0，預設 0.85",
    )
    parser.add_argument("--x", type=int, default=120, help="高亮文字初始 X 座標")
    parser.add_argument("--y", type=int, default=120, help="高亮文字初始 Y 座標")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    opacity = max(0.2, min(1.0, args.opacity))
    font_size = max(12, min(120, args.font_size))

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
        text=args.text,
        font_family=font_family,
        font_size=font_size,
        bold=args.bold,
        highlight_color=args.highlight_color,
        text_color=args.text_color,
        opacity=opacity,
        x=args.x,
        y=args.y,
    )

    root.deiconify()
    ControlPanel(root, overlay)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
