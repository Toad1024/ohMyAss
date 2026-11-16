"""本地配置文件、错误日志、路径与文本写入。"""

import json
import os
import shutil
import sys
import tempfile
import time
import traceback

INVALID_FOLDER_CHARS = {
    '\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？',
    '"': '＂', '<': '＜', '>': '＞', '|': '｜',
}
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}
MAX_FOLDER_NAME_LENGTH = 120

CONFIG_PATH = os.path.join(os.path.expanduser('~'), 'ohMyAssNoto.json')
ERROR_LOG_PATH = os.path.join(os.path.expanduser('~'), 'ohMyAssNoto_error.log')
MAX_LOG_BYTES = 1024 * 1024


def log_exception(context: str, exc=None):
    """把被忽略的异常追加到用户目录日志，超过 1MB 时轮转一次。"""
    try:
        if os.path.isfile(ERROR_LOG_PATH) and os.path.getsize(ERROR_LOG_PATH) > MAX_LOG_BYTES:
            os.replace(ERROR_LOG_PATH, ERROR_LOG_PATH + '.1')
    except OSError:
        pass
    try:
        with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as handle:
            handle.write(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {context}\n')
            if exc is not None:
                handle.write(f'{type(exc).__name__}: {exc}\n')
                traceback.print_exc(file=handle)
            handle.write('\n')
    except OSError:
        pass


def normalize_display_path(value: str) -> str:
    """地址栏统一显示 Windows 反斜杠。"""
    text = str(value or '').strip()
    return text.replace('/', '\\') if text else text


def sanitize_folder_name(name: str) -> str:
    name = str(name or '').strip()
    for old, new in INVALID_FOLDER_CHARS.items():
        name = name.replace(old, new)
    # Windows 不允许文件夹名以空格或点结尾
    name = name.rstrip(' .')
    # Windows 保留设备名不能直接作为文件夹名
    if name.upper() in WINDOWS_RESERVED_NAMES:
        name += '_'
    # 过长的文件夹名会超出路径长度限制
    if len(name) > MAX_FOLDER_NAME_LENGTH:
        name = name[:MAX_FOLDER_NAME_LENGTH].rstrip(' .')
    return name


def get_output_dir(source_file: str, title: str, output_root: str = ''):
    folder_name = sanitize_folder_name(title)
    if not folder_name:
        return None
    base = str(output_root or '').strip()
    if not base:
        base = os.path.dirname(os.path.abspath(source_file))
    return os.path.join(base, folder_name)


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError) as exc:
        # 配置损坏时按默认配置启动，同时留下记录
        log_exception('读取配置', exc)
        return {}


def save_config(data: dict):
    """先写临时文件再替换，避免中途失败把配置写坏。"""
    temp_path = CONFIG_PATH + '.tmp'
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, CONFIG_PATH)
    except (OSError, TypeError, ValueError) as exc:
        log_exception('保存配置', exc)
        try:
            os.remove(temp_path)
        except OSError:
            pass


def cleanup_stale_temp_folders(max_age_seconds: int = 7 * 86400, base: str = None):
    """清理一周前的 PyInstaller 解压目录与更新临时目录。

    先改名再删除：仍在运行的 _MEI 目录通常无法改名，可避免误删。
    """
    root = base or tempfile.gettempdir()
    current = ''
    meipass = getattr(sys, '_MEIPASS', '')
    if meipass:
        current = os.path.abspath(meipass).lower()
    now = time.time()
    try:
        entries = os.listdir(root)
    except OSError:
        return
    for name in entries:
        if not (name.startswith('_MEI') or name.startswith('oma_update_')):
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if current and os.path.abspath(path).lower() == current:
            continue
        try:
            if now - os.path.getmtime(path) < max_age_seconds:
                continue
        except OSError:
            continue
        stale = path + '.stale'
        try:
            if os.path.exists(stale):
                shutil.rmtree(stale, ignore_errors=True)
            os.rename(path, stale)
        except OSError:
            # 仍被占用，跳过
            continue
        shutil.rmtree(stale, ignore_errors=True)


def write_text_with_fallback(path: str, content: str) -> str:
    """写入文本；若文件被占用，则改用 name_1.ext 等文件名。"""
    base, ext = os.path.splitext(path)
    candidate = path
    counter = 0
    while True:
        try:
            with open(candidate, 'w', encoding='utf-8-sig') as f:
                f.write(content)
            return candidate
        except OSError:
            counter += 1
            if counter > 99:
                raise
            candidate = f'{base}_{counter}{ext}'
