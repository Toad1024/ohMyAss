"""字体注册、思源黑体安装与字体检测。"""


import os
import re
import ctypes
import shutil
import tempfile
from functools import lru_cache

try:
    import winreg
except ImportError:
    winreg = None

from config_store import log_exception
from download_utils import download_file


# ===================== 思源黑体 Medium（字幕默认字体） =====================

SOURCE_HAN_FONT_FILE = 'SourceHanSansSC-Medium.otf'
SOURCE_HAN_FONT_LABEL = '思源黑体 Medium'
SOURCE_HAN_FONT_URLS = (
    'https://cdn.jsdelivr.net/gh/adobe-fonts/source-han-sans@release/OTF/SimplifiedChinese/'
    'SourceHanSansSC-Medium.otf',
    'https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/OTF/'
    'SimplifiedChinese/SourceHanSansSC-Medium.otf',
)
SOURCE_HAN_FONT_KEYS = ('思源黑体 medium', '思源黑體 medium', 'source han sans sc medium')
USER_FONT_DIR = os.path.join(
    os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
    'Microsoft', 'Windows', 'Fonts',
)


def font_registry_entries():
    """读取已注册字体：[(显示名, 路径或文件名), ...]。"""
    if winreg is None:
        return []
    entries = []
    targets = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        targets.append((hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'))
        targets.append((hive, r'SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Fonts'))
    for hive, sub in targets:
        try:
            with winreg.OpenKey(hive, sub) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1
                    entries.append((str(name), str(value)))
        except OSError:
            continue
    return entries


def source_han_medium_installed() -> bool:
    """系统中是否已安装思源黑体 Medium。"""
    for name, value in font_registry_entries():
        if not any(key in name.lower() for key in SOURCE_HAN_FONT_KEYS):
            continue
        if not value:
            return True
        if os.path.isabs(value):
            if os.path.isfile(value):
                return True
            continue
        for folder in (os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'), USER_FONT_DIR):
            if os.path.isfile(os.path.join(folder, value)):
                return True
    return False


FONT_WEIGHT_ALIASES = {
    'thin': 'thin', 'hairline': 'thin',
    'extralight': 'extralight', 'ultralight': 'extralight',
    'light': 'light',
    'regular': 'regular', 'normal': 'regular', 'book': 'regular',
    'medium': 'medium',
    'semibold': 'semibold', 'demibold': 'semibold',
    'bold': 'bold',
    'extrabold': 'extrabold', 'ultrabold': 'extrabold',
    'black': 'black',
    'heavy': 'heavy',
    'italic': 'italic', 'oblique': 'oblique',
}


def _font_key(name: str) -> str:
    """把字体名归一化成小写紧凑串，便于精确比较。"""
    text = re.sub(r'\([^)]*\)', '', str(name or ''))
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]+', '', text.lower())


def _font_aliases(name: str) -> list:
    """拆分「Microsoft YaHei & Microsoft YaHei UI」这类共用注册项。"""
    text = re.sub(r'\([^)]*\)', ' ', str(name or ''))
    parts = re.split(r'(?i)\s*(?:&|\band\b)\s*', text)
    return [part.strip() for part in parts if part.strip()]


def _font_tokens(name: str):
    """返回 (基础名, 字重集合)。字重必须显式匹配，不做模糊兜底。"""
    text = re.sub(r'\([^)]*\)', ' ', str(name or ''))
    weight_words = []
    weights = set()
    for word in re.findall(r'[A-Za-z]+', text):
        alias = FONT_WEIGHT_ALIASES.get(word.lower())
        if alias:
            weights.add(alias)
            weight_words.append(word)
    base_text = text
    for word in sorted(set(weight_words), key=len, reverse=True):
        base_text = re.sub(r'(?i)\b' + re.escape(word) + r'\b', ' ', base_text)
    return _font_key(base_text), frozenset(weights or {'regular'})


def _resolve_font_file(value: str) -> str:
    """把注册表里的字体值解析成实际文件路径。"""
    value = str(value or '').strip()
    if not value:
        return ''
    if os.path.isabs(value):
        return value if os.path.isfile(value) else ''
    for folder in (os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
                   USER_FONT_DIR):
        path = os.path.join(folder, value)
        if os.path.isfile(path):
            return path
    return ''


@lru_cache(maxsize=1)
def installed_font_records():
    """已安装字体记录：((基础名, 字重集合, 文件路径), ...)。"""
    records = []
    seen = set()

    def add(base, weights, path):
        if not base:
            return
        item = (base, weights, path)
        if item not in seen:
            seen.add(item)
            records.append(item)

    for name, value in font_registry_entries():
        path = _resolve_font_file(value)
        for alias in _font_aliases(name):
            base, weights = _font_tokens(alias)
            add(base, weights, path)
    for folder in (os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
                   USER_FONT_DIR):
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        for entry in entries:
            path = os.path.join(folder, entry)
            if not os.path.isfile(path):
                continue
            base, weights = _font_tokens(os.path.splitext(entry)[0])
            add(base, weights, path)
    return tuple(records)


def font_name_installed(name: str, records=None) -> bool:
    """严格判断字体名是否已安装：基础名相同且字重完全对应。"""
    base, weights = _font_tokens(name)
    if not base:
        return True
    records = installed_font_records() if records is None else records
    for record_base, record_weights, _ in records:
        if record_base == base and weights <= record_weights:
            return True
    return False


def preview_font_path(name: str) -> str:
    """给样式预览挑一个可用的字体文件（字重优先精确匹配）。"""
    base, weights = _font_tokens(name)
    fallback = ''
    for record_base, record_weights, path in installed_font_records():
        if record_base != base or not path or not os.path.isfile(path):
            continue
        if weights <= record_weights:
            return path
        fallback = fallback or path
    return fallback


def _broadcast_font_change():
    """通知其他窗口字体已变化（带超时，避免被无响应窗口卡住）。"""
    try:
        installed_font_records.cache_clear()
    except AttributeError:
        pass
    try:
        send_timeout = ctypes.windll.user32.SendMessageTimeoutW
        send_timeout.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t,
            ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_size_t),
        ]
        send_timeout.restype = ctypes.c_size_t
        result = ctypes.c_size_t()
        send_timeout(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, ctypes.byref(result))
    except (OSError, AttributeError, ValueError) as exc:
        # 广播失败只影响其他窗口的字体刷新，不应打断安装
        log_exception('广播字体变化', exc)


def install_source_han_medium(font_path: str, log=None) -> str:
    """把字体安装到当前用户（无需管理员权限），返回安装后的路径。"""
    if winreg is None or os.name != 'nt':
        raise OSError('仅支持 Windows 系统')
    os.makedirs(USER_FONT_DIR, exist_ok=True)
    target = os.path.join(USER_FONT_DIR, SOURCE_HAN_FONT_FILE)
    try:
        shutil.copy2(font_path, target)
    except OSError:
        if not os.path.isfile(target):
            raise
    try:
        add_font = ctypes.windll.gdi32.AddFontResourceW
        add_font.argtypes = [ctypes.c_wchar_p]
        add_font.restype = ctypes.c_int
        add_font(target)
    except (OSError, AttributeError) as exc:
        # 注册失败时字体文件已就位，重启后仍会生效
        log_exception('注册字体', exc)
    with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows NT\CurrentVersion\Fonts',
            0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, f'{SOURCE_HAN_FONT_LABEL} (TrueType)', 0, winreg.REG_SZ, target)
    _broadcast_font_change()
    if log:
        log('字体文件已写入，正在刷新字体缓存…')
    return target


def ensure_source_han_font(log=None):
    """检查思源黑体 Medium；缺失时下载并安装。"""
    if source_han_medium_installed():
        return True, f'{SOURCE_HAN_FONT_LABEL} 已安装'
    if winreg is None or os.name != 'nt':
        return False, '仅支持 Windows 系统'

    temp_dir = tempfile.mkdtemp(prefix='ohmyass_font_')
    dest = os.path.join(temp_dir, SOURCE_HAN_FONT_FILE)
    last_error = ''
    try:
        downloaded = False
        for url in SOURCE_HAN_FONT_URLS:
            try:
                if log:
                    log(f'正在下载 {SOURCE_HAN_FONT_LABEL}…')
                download_file(url, dest, log=log, timeout=180)
                if os.path.isfile(dest) and os.path.getsize(dest) > 1024 * 1024:
                    with open(dest, 'rb') as handle:
                        head = handle.read(4)
                    if head in (b'OTTO', b'\x00\x01\x00\x00', b'true', b'ttcf'):
                        downloaded = True
                        break
                    last_error = '字体文件格式异常（下载内容可能不是字体）'
                else:
                    last_error = '下载文件不完整'
            except Exception as exc:
                last_error = str(exc)
        if not downloaded:
            return False, f'下载失败：{last_error or "未知错误"}'
        if log:
            log('正在安装字体…')
        install_source_han_medium(dest, log)
    except Exception as exc:
        return False, f'安装失败：{exc}'
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if source_han_medium_installed():
        return True, f'{SOURCE_HAN_FONT_LABEL} 安装完成'
    return False, '安装完成但未检测到字体，请重启软件后再试'
