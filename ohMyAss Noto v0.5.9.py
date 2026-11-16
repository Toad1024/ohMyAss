"""程序入口。"""

import ctypes
import os
import sys
import tkinter as tk
from tkinter import messagebox

from app_ui import App, create_root
from config_store import log_exception
from theme_ui import UI_SCALE

SINGLE_INSTANCE_HANDLE = None


def acquire_single_instance(name: str = 'Local\\ohMyAssNoto_SingleInstance') -> bool:
    """Windows 命名互斥体，防止两个实例同时写配置。"""
    global SINGLE_INSTANCE_HANDLE
    if os.name != 'nt':
        return True
    try:
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            return True
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return False
        SINGLE_INSTANCE_HANDLE = handle
        return True
    except Exception as exc:
        # 单实例检查失败不应阻止程序启动，但要留下记录
        log_exception('单实例检查', exc)
        return True


if __name__ == '__main__':
    if not acquire_single_instance():
        messagebox.showinfo('ohMyAss Noto', '软件已经在运行，请使用已打开的窗口。')
        sys.exit(0)
    root = create_root()
    try:
        root.tk.call('tk', 'scaling', UI_SCALE * 96.0 / 72.0)
    except tk.TclError:
        pass
    app = App(root)
    root.mainloop()
