"""拖放、占位输入框等通用控件。"""


import tkinter as tk
from tkinter import ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    TkinterDnD = None
    DND_AVAILABLE = False

import theme_ui
from theme_ui import UI_FIELD, UI_FONT, UI_MUTED, UI_SMALL_SIZE

theme_ui.register_theme_namespace(globals())


def enable_file_drop(widget, callback):
    """给控件注册文件拖放（tkinterdnd2 缺失时静默跳过）。"""
    if not DND_AVAILABLE:
        return False
    try:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>', callback)
        return True
    except (tk.TclError, AttributeError):
        return False


def split_dropped_paths(widget, data: str):
    """把拖放事件里的路径拆成列表（兼容带空格的路径）。"""
    try:
        return [path for path in widget.tk.splitlist(data) if path]
    except tk.TclError:
        return [data] if data else []


def attach_entry_placeholder(entry, variable, text):
    """给普通 Entry 叠加灰色占位说明，输入内容后自动隐藏。"""
    label = tk.Label(
        entry, text=text, bg=UI_FIELD, fg=UI_MUTED,
        font=(UI_FONT, UI_SMALL_SIZE), anchor='w')
    label.bind('<Button-1>', lambda event: entry.focus_set())

    def sync(*args):
        if variable.get().strip():
            label.place_forget()
        else:
            label.place(x=8, rely=0.5, anchor='w')

    variable.trace_add('write', sync)
    entry.bind('<Configure>', lambda event: sync(), add='+')
    sync()
    return label


class PlaceholderEntry(ttk.Entry):
    """带占位提示的输入框，样式与其它控件统一高度。"""

    def __init__(self, master, placeholder='选填', **kwargs):
        self._var = tk.StringVar()
        kwargs.setdefault('textvariable', self._var)
        kwargs.setdefault('style', 'Placeholder.TEntry')
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self._showing_placeholder = False
        self.bind('<FocusIn>', self._focus_in)
        self.bind('<FocusOut>', self._focus_out)
        self._show_placeholder()

    def _show_placeholder(self):
        if not self._var.get().strip():
            self._showing_placeholder = True
            self._var.set(self.placeholder)
            self.configure(style='Placeholder.TEntry')

    def _focus_in(self, event):
        if self._showing_placeholder:
            self._var.set('')
            self._showing_placeholder = False
            self.configure(style='TEntry')

    def _focus_out(self, event):
        if not self._var.get().strip():
            self._show_placeholder()

    def get_value(self):
        if self._showing_placeholder:
            return ''
        return self._var.get().strip()

    def set_value(self, value):
        value = str(value or '').strip()
        self._showing_placeholder = False
        self._var.set(value)
        if value:
            self.configure(style='TEntry')
        else:
            self._show_placeholder()
