import re, os
import statistics
import ctypes
import math
from collections import Counter
from functools import lru_cache
import difflib
import html
import json
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import zhconv
from enum import Enum
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import winreg
except ImportError:  # 非 Windows 平台
    winreg = None

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageTk
except ImportError:
    Image = None
    ImageChops = None
    ImageDraw = None
    ImageFilter = None
    ImageFont = None
    ImageTk = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

match_paragraph_script_info = re.compile(r'\[Script Info\]', re.I)
match_paragraph_styles = re.compile(r'\[V4\+ Styles\]', re.I)
match_paragraph_events = re.compile(r'\[Events\]', re.I)
match_paragraph_aegisub = re.compile(r'\[Aegisub Project Garbage\]', re.I)
match_script_info_play_x = re.compile(r'PlayResX: *(\d+)', re.I)
match_script_info_play_y = re.compile(r'PlayResY: *(\d+)', re.I)

match_events_dialogue = re.compile(r'Dialogue', re.I)
match_events_newline = re.compile(r'\\N')
match_events_fs = re.compile(r'\\fs(\d+)', re.I)

match_events_override_block = re.compile(r'\{[^}]*\}')
match_override_split = re.compile(r'(\{[^}]*\})')
match_events_special_effect = re.compile(
    r'\\move\(|\\pos\(|\\org\(|\\i?clip\(|\\fad\(|\\t\(|'
    r'\\[kK]|\\fsc[xy]?|\\fsp|\\fr[xyz]?|\\be|\\bord|\\shad|'
    r'\\alpha|\\[1-4]a|\\a\d+|\\h(?![A-Za-z])|\\q\d|\\p\d',
    re.I,
)
match_events_move = re.compile(r'\\move\(([\d.]+),([\d.]+),([\d.]+),([\d.]+)', re.I)
match_events_pos = re.compile(r'\\pos\(([\d.]+),([\d.]+)', re.I)
match_events_org = re.compile(r'\\org\(([\d.]+),([\d.]+)', re.I)
match_events_iclip = re.compile(r'\\iclip\(([\d.]+),([\d.]+),([\d.]+),([\d.]+)', re.I)
match_events_clip = re.compile(r'\\clip\(([\d.]+),([\d.]+),([\d.]+),([\d.]+)', re.I)

def has_special_effect(text: str) -> bool:
    for block in match_events_override_block.findall(text):
        if match_events_special_effect.search(block):
            return True
    return False


match_cjk = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
match_latin = re.compile(r'[A-Za-z]')
match_override_tag = re.compile(r'{.*?}')
match_font_tag = re.compile(r'\\fn[^\\}]*')
match_reset_tag = re.compile(r'\\r[^\\}]*')
match_font_size_tag = re.compile(r'\\fs\d+')
match_colour_tag = re.compile(r'\\[1-4]?[ac]&H[0-9A-Fa-f]+&?')
match_blur3_tag = re.compile(r'\\blur3(?![0-9])')
match_blur_tag = re.compile(r'\\blur\d*')
match_fsvp_tag = re.compile(r'\\fsvp\d+')
match_bold_tag = re.compile(r'\\b(?:[1-9]\d*|0)?(?![A-Za-z])', re.I)
match_italic_tag = re.compile(r'\\i[01]?(?![A-Za-z])', re.I)
match_underline_tag = re.compile(r'\\u[01]?(?![A-Za-z])', re.I)
match_strike_tag = re.compile(r'\\s[01]?(?![A-Za-z])', re.I)
match_encoding_tag = re.compile(r'\\fe[^\\}]*', re.I)
match_empty_tag = re.compile(r'\{\s*\}')

OUT_BILINGUAL = '简英双语'
OUT_CHS = '简体中文'
OUT_CHT = '繁体中文'
OUT_ENG = '英文'

APP_NAME = 'ohMyAss Noto'
APP_VERSION = 'v0.5.5'

# WinUI / FlowEncode 主题令牌（Light）
UI_BG = '#eef1f6'
UI_CARD = '#ffffff'
UI_BORDER = '#e3e3e3'
UI_TEXT = '#202938'
UI_MUTED = '#586477'
UI_ACCENT = '#2563eb'
UI_ACCENT_DARK = '#1d4ed8'
UI_ACCENT_SOFT = '#e7edfb'
UI_FIELD_BORDER = '#c9cfda'
UI_FONT = 'Microsoft YaHei UI'
UI_DISPLAY_FONT = 'Microsoft YaHei UI'
UI_ICON_FONT = 'Segoe MDL2 Assets'
UI_TITLE_SIZE = 20
UI_BODY_SIZE = 10
UI_SMALL_SIZE = 9
UI_BUTTON_SIZE = 10
UI_CARD_TITLE_SIZE = 10
UI_MODULE_TITLE_SIZE = 12
UI_ICON_NAV_SIZE = 16
UI_ICON_CARD_SIZE = 20
UI_ARROW_SIZE = 10
UI_TITLE_FONT = (UI_DISPLAY_FONT, UI_TITLE_SIZE, 'bold')

ICON_HOME = '\uE80F'
ICON_PENCIL = '\uE70F'
ICON_VIDEO = '\uE714'
ICON_FIX = '\uE90F'
ICON_SETTINGS = '\uE713'


def register_bundled_fonts():
    """与 v0.2.13 一致：不内置字体，直接使用系统字体。"""
    return


def pick_ui_fonts():
    """与 v0.2.13 一致：使用系统 Microsoft YaHei UI。"""
    global UI_FONT, UI_DISPLAY_FONT, UI_TITLE_FONT, UI_ICON_FONT
    try:
        from tkinter import font as tkfont
        families = set(tkfont.families())
    except Exception:
        families = set()

    def first(candidates, fallback):
        for name in candidates:
            if name in families:
                return name
        return fallback

    UI_FONT = first(['Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI'],
                    'Microsoft YaHei UI')
    UI_DISPLAY_FONT = UI_FONT
    UI_ICON_FONT = first(['Segoe Fluent Icons', 'Segoe MDL2 Assets'], 'Segoe MDL2 Assets')
    UI_TITLE_FONT = (UI_DISPLAY_FONT, UI_TITLE_SIZE, 'bold')


def center_window(window, parent):
    """把对话框居中到主窗口位置。"""
    try:
        window.update_idletasks()
        parent = parent.winfo_toplevel()
        parent.update_idletasks()
        width = max(window.winfo_width(), window.winfo_reqwidth())
        height = max(window.winfo_height(), window.winfo_reqheight())
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        window.geometry(f'+{max(0, x)}+{max(0, y)}')
    except tk.TclError:
        pass


class RoundedFrame(tk.Frame):
    """Canvas 绘制的圆角容器，内容放在 .body 中。"""

    def __init__(self, parent, radius=8, bg=UI_BG, fill=UI_CARD,
                 border=UI_BORDER, inset=4):
        super().__init__(parent, bg=bg)
        self.radius = radius
        self.fill = fill
        self.border = border
        self.inset = inset
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill='both', expand=True)
        self.body = tk.Frame(self.canvas, bg=fill)
        self._window = self.canvas.create_window(inset, inset, anchor='nw', window=self.body)
        self._resize_pending = False
        self.body.bind('<Configure>', self._on_body_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.after_idle(self._sync_height)

    def _on_body_configure(self, event=None):
        if self._resize_pending:
            return
        self._resize_pending = True
        self.after_idle(self._sync_height)

    def _sync_height(self):
        self._resize_pending = False
        try:
            height = self.body.winfo_reqheight() + self.inset * 2
        except tk.TclError:
            return
        if height > 0 and abs(self.canvas.winfo_reqheight() - height) > 1:
            self.canvas.configure(height=height)

    def _on_canvas_configure(self, event):
        width = max(1, event.width)
        height = max(1, event.height)
        self.canvas.coords(self._window, self.inset, self.inset)
        self.canvas.itemconfigure(
            self._window,
            width=max(1, width - self.inset * 2),
            height=max(1, height - self.inset * 2),
        )
        self._draw(width, height)

    def _draw(self, width, height):
        self.canvas.delete('frame_shape')
        radius = min(self.radius, max(1, width // 2), max(1, height // 2))
        x1, y1 = 0, 0
        x2, y2 = width - 1, height - 1
        fill, border = self.fill, self.border

        self.canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2,
                                     fill=fill, outline='', tags='frame_shape')
        self.canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius,
                                     fill=fill, outline='', tags='frame_shape')
        self.canvas.create_arc(x1, y1, x1 + 2 * radius, y1 + 2 * radius,
                               start=90, extent=90, style='pieslice',
                               fill=fill, outline='', tags='frame_shape')
        self.canvas.create_arc(x2 - 2 * radius, y1, x2, y1 + 2 * radius,
                               start=0, extent=90, style='pieslice',
                               fill=fill, outline='', tags='frame_shape')
        self.canvas.create_arc(x1, y2 - 2 * radius, x1 + 2 * radius, y2,
                               start=180, extent=90, style='pieslice',
                               fill=fill, outline='', tags='frame_shape')
        self.canvas.create_arc(x2 - 2 * radius, y2 - 2 * radius, x2, y2,
                               start=270, extent=90, style='pieslice',
                               fill=fill, outline='', tags='frame_shape')

        self.canvas.create_line(x1 + radius, y1, x2 - radius, y1,
                                fill=border, tags='frame_shape')
        self.canvas.create_line(x2, y1 + radius, x2, y2 - radius,
                                fill=border, tags='frame_shape')
        self.canvas.create_line(x1 + radius, y2, x2 - radius, y2,
                                fill=border, tags='frame_shape')
        self.canvas.create_line(x1, y1 + radius, x1, y2 - radius,
                                fill=border, tags='frame_shape')
        for box, start in (
            ((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 90),
            ((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 0),
            ((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 180),
            ((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 270),
        ):
            self.canvas.create_arc(*box, start=start, extent=90, style='arc',
                                   outline=border, tags='frame_shape')
        self.canvas.tag_lower('frame_shape')


def load_app_icon(size: int = 72):
    try:
        image = tk.PhotoImage(file=resource_path('ohMyAss Noto.png'))
        factor = max(1, image.width() // size)
        if factor > 1:
            image = image.subsample(factor, factor)
        return image
    except Exception:
        return None


def _rounded_rect(canvas, x1, y1, x2, y2, radius, color, tag=''):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1,
        x2, y1 + radius, x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2, x1, y2,
        x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    canvas.create_polygon(points, smooth=True, splinesteps=24, fill=color, outline='', tags=tag)


def _normalize_icon(image, size: int, margin: float = 0.04, stretch: bool = False):
    """把图标裁到内容边界后居中放入同尺寸正方形画布。"""
    if image is None:
        return None
    bbox = image.getbbox()
    if not bbox:
        return image.resize((size, size), Image.LANCZOS)
    content = image.crop(bbox)
    target = max(1, round(size * (1 - margin * 2)))
    if stretch:
        new_size = (target, target)
    else:
        side = max(content.size)
        scale = target / side
        new_size = (
            max(1, round(content.width * scale)),
            max(1, round(content.height * scale)),
        )
    content = content.resize(new_size, Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(content, ((size - new_size[0]) // 2, (size - new_size[1]) // 2), content)
    return canvas


def render_camera_icon(size: int = 34, color=(32, 41, 56), weight: float = 1.0):
    """用 PIL 生成抗锯齿的简笔画照相机图标。"""
    if Image is None or ImageDraw is None:
        return None
    scale = 4
    canvas = size * scale
    unit = canvas / 40.0
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    line_color = color + (255,)
    width = max(2, round(2.05 * unit * weight))

    def point(x, y):
        return (x * unit, y * unit)

    def arc(cx, cy, radius, start, end, steps=8):
        values = []
        for index in range(steps + 1):
            angle = math.radians(start + (end - start) * index / steps)
            values.append(point(cx + radius * math.cos(angle),
                                cy + radius * math.sin(angle)))
        return values

    radius = 4
    outline = [point(5, 17)]
    outline += [point(5, 29)]
    outline += arc(9, 29, radius, 180, 90)
    outline += [point(31, 33)]
    outline += arc(31, 29, radius, 90, 0)
    outline += [point(35, 17)]
    outline += arc(31, 17, radius, 0, -90)
    outline += [point(25, 13)]
    outline += [point(25, 11)]
    outline += arc(22.5, 11, 2.5, 0, -90)
    outline += [point(17.5, 8.5)]
    outline += arc(17.5, 11, 2.5, -90, -180)
    outline += [point(15, 13)]
    outline += [point(9, 13)]
    outline += arc(9, 17, radius, -90, -180)
    outline.append(outline[0])
    draw.line(outline, fill=line_color, width=width, joint='curve')

    lens = 6.5
    left, top = point(20 - lens, 23.5 - lens)
    right, bottom = point(20 + lens, 23.5 + lens)
    draw.ellipse((left, top, right, bottom), outline=line_color, width=width)

    return _normalize_icon(image, size)


def render_gear_icon(size: int = 34, color=(32, 41, 56), weight: float = 1.0):
    """用 PIL 生成抗锯齿的简笔画齿轮图标。"""
    if Image is None or ImageDraw is None:
        return None
    scale = 5
    canvas = size * scale
    unit = canvas / 40.0
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    line_color = color + (255,)
    width = max(2, round(2.0 * unit * weight))

    center = 20.0
    teeth = 6
    root_radius = 10.4
    tip_radius = 14.6
    step = 360 / teeth
    base = []
    for index in range(teeth):
        angle = -90 + index * step
        for offset, radius in (
            (angle - 19, root_radius),
            (angle - 11, tip_radius),
            (angle + 11, tip_radius),
            (angle + 19, root_radius),
        ):
            radians = math.radians(offset)
            base.append((
                center + radius * math.cos(radians),
                center + radius * math.sin(radians),
            ))

    def round_path(points, radius, steps=6):
        result = []
        count = len(points)
        for index in range(count):
            previous = points[index - 1]
            point = points[index]
            following = points[(index + 1) % count]
            v1 = (previous[0] - point[0], previous[1] - point[1])
            v2 = (following[0] - point[0], following[1] - point[1])
            l1 = math.hypot(*v1) or 1
            l2 = math.hypot(*v2) or 1
            r = min(radius, l1 / 2, l2 / 2)
            start = (point[0] + v1[0] / l1 * r, point[1] + v1[1] / l1 * r)
            end = (point[0] + v2[0] / l2 * r, point[1] + v2[1] / l2 * r)
            for step_index in range(steps + 1):
                t = step_index / steps
                result.append((
                    (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * point[0] + t ** 2 * end[0],
                    (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * point[1] + t ** 2 * end[1],
                ))
        return result

    outline = round_path(base, 0.8)
    outline.append(outline[0])
    scaled = [(x * unit, y * unit) for x, y in outline]
    draw.line(scaled, fill=line_color, width=width, joint='curve')
    cap = width / 2
    for x, y in scaled:
        draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=line_color)

    inner = 5.0
    draw.ellipse((
        (center - inner) * unit, (center - inner) * unit,
        (center + inner) * unit, (center + inner) * unit,
    ), outline=line_color, width=width)

    return _normalize_icon(image, size)


def render_pencil_icon(size: int = 34, color=(32, 41, 56), weight: float = 1.0):
    """用 PIL 生成抗锯齿的简笔画铅笔图标。"""
    if Image is None or ImageDraw is None:
        return None
    scale = 5
    canvas = size * scale
    unit = canvas / 40.0
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    line_color = color + (255,)
    width = max(2, round(1.55 * unit * weight))
    cap = width / 2

    angle = math.radians(-45)
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    def rotate(x, y):
        return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

    local = [(0, 0), (7, -3.5), (29, -3.5)]
    for step in range(1, 9):
        angle = math.radians(-90 + 180 * step / 8)
        local.append((29 + 3.5 * math.cos(angle), 3.5 * math.sin(angle)))
    local.append((7, 3.5))
    rotated = [rotate(x, y) for x, y in local]
    min_x = min(point[0] for point in rotated)
    max_x = max(point[0] for point in rotated)
    min_y = min(point[1] for point in rotated)
    max_y = max(point[1] for point in rotated)
    offset_x = 20 - (min_x + max_x) / 2
    offset_y = 20 - (min_y + max_y) / 2
    rotated = [(x + offset_x, y + offset_y) for x, y in rotated]

    def round_path(points, radius, steps=6):
        result = []
        count = len(points)
        for index in range(count):
            previous = points[index - 1]
            point = points[index]
            following = points[(index + 1) % count]
            v1 = (previous[0] - point[0], previous[1] - point[1])
            v2 = (following[0] - point[0], following[1] - point[1])
            l1 = math.hypot(*v1) or 1
            l2 = math.hypot(*v2) or 1
            r = min(radius, l1 / 2, l2 / 2)
            start = (point[0] + v1[0] / l1 * r, point[1] + v1[1] / l1 * r)
            end = (point[0] + v2[0] / l2 * r, point[1] + v2[1] / l2 * r)
            for step_index in range(steps + 1):
                t = step_index / steps
                result.append((
                    (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * point[0] + t ** 2 * end[0],
                    (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * point[1] + t ** 2 * end[1],
                ))
        return result

    outline = round_path(rotated, 1.0)
    scaled = [(x * unit, y * unit) for x, y in outline]
    scaled.append(scaled[0])
    draw.line(scaled, fill=line_color, width=width, joint='curve')
    for x, y in scaled:
        draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=line_color)

    band_a = rotate(26, -3.5)
    band_b = rotate(26, 3.5)
    band_a = ((band_a[0] + offset_x) * unit, (band_a[1] + offset_y) * unit)
    band_b = ((band_b[0] + offset_x) * unit, (band_b[1] + offset_y) * unit)
    draw.line([band_a, band_b], fill=line_color, width=width)
    for x, y in (band_a, band_b):
        draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=line_color)

    return _normalize_icon(image, size)


def render_house_icon(size: int = 34, color=(32, 41, 56), weight: float = 1.0):
    """用 PIL 生成抗锯齿的简笔画房屋图标。"""
    if Image is None or ImageDraw is None:
        return None
    scale = 5
    canvas = size * scale
    unit = canvas / 40.0
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    line_color = color + (255,)
    width = max(2, round(1.7 * unit * weight))
    cap = width / 2

    points = [
        (7, 19), (20, 7), (33, 19), (33, 31),
        (24, 31), (24, 26), (16, 26), (16, 31),
        (7, 31),
    ]

    def round_path(pts, radius, steps=6):
        result = []
        count = len(pts)
        for index in range(count):
            previous = pts[index - 1]
            point = pts[index]
            following = pts[(index + 1) % count]
            v1 = (previous[0] - point[0], previous[1] - point[1])
            v2 = (following[0] - point[0], following[1] - point[1])
            l1 = math.hypot(*v1) or 1
            l2 = math.hypot(*v2) or 1
            r = min(radius, l1 / 2, l2 / 2)
            start = (point[0] + v1[0] / l1 * r, point[1] + v1[1] / l1 * r)
            end = (point[0] + v2[0] / l2 * r, point[1] + v2[1] / l2 * r)
            for step_index in range(steps + 1):
                t = step_index / steps
                result.append((
                    (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * point[0] + t ** 2 * end[0],
                    (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * point[1] + t ** 2 * end[1],
                ))
        return result

    outline = round_path(points, 2.2)
    scaled = [(x * unit, y * unit) for x, y in outline]
    scaled.append(scaled[0])
    draw.line(scaled, fill=line_color, width=width, joint='curve')
    for x, y in scaled:
        draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=line_color)

    return _normalize_icon(image, size, stretch=True)


def render_wrench_icon(size: int = 34, color=(32, 41, 56), weight: float = 1.0):
    """从 Segoe MDL2 字形生成原版扳手图标（抗锯齿）。"""
    if Image is None or ImageDraw is None or ImageFont is None:
        return None
    font_path = os.path.join(os.environ.get('WINDIR', r'C:\Windows'),
                             'Fonts', 'segmdl2.ttf')
    scale = 4
    canvas = size * scale
    try:
        font = ImageFont.truetype(font_path, round(canvas * 0.9))
    except OSError:
        return None
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    glyph = chr(0xE90F)
    left, top, right, bottom = draw.textbbox((0, 0), glyph, font=font)
    width = right - left
    height = bottom - top
    position = ((canvas - width) / 2 - left, (canvas - height) / 2 - top)
    draw.text(position, glyph, font=font, fill=color + (255,))
    if weight > 1.05 and ImageFilter is not None:
        image = image.filter(ImageFilter.MaxFilter(3))
    elif weight < 0.95 and ImageFilter is not None:
        image = image.filter(ImageFilter.MinFilter(3))
    return _normalize_icon(image, size)


def _hex_to_rgb(value: str):
    value = value.lstrip('#')
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


ICON_RENDERERS = {
    'home': render_house_icon,
    'pencil': render_pencil_icon,
    'fix': render_wrench_icon,
    'frame': render_camera_icon,
    'settings': render_gear_icon,
}


def create_card(parent, title: str = ''):
    card = RoundedFrame(parent, radius=8)
    if title:
        tk.Label(
            card.body, text=title, bg=UI_CARD, fg=UI_TEXT,
            font=(UI_DISPLAY_FONT, UI_BODY_SIZE, 'bold'),
        ).pack(anchor='w', padx=16, pady=(8, 0))
    body = tk.Frame(card.body, bg=UI_CARD)
    body.pack(fill='both', expand=True, padx=16, pady=(5, 8))
    return card, body


def create_hero(parent, title: str, subtitle: str, icon_size: int = 120):
    card = RoundedFrame(parent, radius=12)
    inner = tk.Frame(card.body, bg=UI_CARD)
    inner.pack(fill='x', padx=24, pady=7)
    left = tk.Frame(inner, bg=UI_CARD)
    left.pack(side='left', fill='x', expand=True)
    tk.Label(
        left, text=title, bg=UI_CARD, fg=UI_TEXT,
        font=UI_TITLE_FONT,
    ).pack(anchor='w')
    tk.Label(
        left, text=subtitle, bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_BODY_SIZE),
    ).pack(anchor='w', pady=(6, 0))
    icon = load_app_icon(icon_size)
    if icon is not None:
        label = tk.Label(inner, image=icon, bg=UI_CARD)
        label.image = icon
        label.pack(side='right', padx=(16, 0))
    return card

# 繁化姬（https://zhconvert.org）台湾化接口
ZHCONVERT_API = 'https://api.zhconvert.org/convert'
ZHCONVERT_CONVERTER = 'Taiwan'
ZHCONVERT_MAX_CHARS = 4000
ZHCONVERT_TIMEOUT = 30
TAIWAN_REPORT_NAME = '繁体台湾化对比.html'
NOTICES_REPORT_NAME = '字幕问题检查报告.html'
NOTICES_DATA_NAME = '字幕问题数据.json'
EDIT_SOURCE_PREFIX = '字幕修改稿'

# ASS 样式行字段位置
STYLE_COLOUR_FIELDS = (3, 4, 5, 6)
STYLE_MARGIN_V_FIELD = 21

# ssaHdrify（https://github.com/gky99/ssaHdrify）色彩映射参数
HDR_SUB_BRIGHTNESS = 100.0
HDR_SRGB_TO_XYZ = (
    (0.4124, 0.3576, 0.1805),
    (0.2126, 0.7152, 0.0722),
    (0.0193, 0.1192, 0.9505),
)
HDR_XYZ_TO_BT2020 = (
    (1.71665119, -0.35567078, -0.25336628),
    (-0.66668435, 1.61648124, 0.01576855),
    (0.01763986, -0.04277061, 0.94210312),
)
HDR_PQ_M1 = 2610 / 16384
HDR_PQ_M2 = 2523 / 4096 * 128
HDR_PQ_C1 = 3424 / 4096
HDR_PQ_C2 = 2413 / 4096 * 32
HDR_PQ_C3 = 2392 / 4096 * 32

match_inline_colour = re.compile(r'(\\[1-4]?c&H)([0-9A-Fa-f]{2,})(?=[&})\\])')


def _decode_srgb(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _pq_encode(nits: float) -> float:
    luma = min(max(nits / 10000.0, 0.0), 1.0) ** HDR_PQ_M1
    return ((HDR_PQ_C1 + HDR_PQ_C2 * luma) / (1 + HDR_PQ_C3 * luma)) ** HDR_PQ_M2


def srgb_to_hdr(rgb, brightness: float = HDR_SUB_BRIGHTNESS):
    """按 ssaHdrify 的流程把 sRGB 颜色映射到 BT.2020 + PQ。"""
    red, green, blue = (_decode_srgb(value / 255.0) for value in rgb)
    x = HDR_SRGB_TO_XYZ[0][0] * red + HDR_SRGB_TO_XYZ[0][1] * green + HDR_SRGB_TO_XYZ[0][2] * blue
    y = HDR_SRGB_TO_XYZ[1][0] * red + HDR_SRGB_TO_XYZ[1][1] * green + HDR_SRGB_TO_XYZ[1][2] * blue
    z = HDR_SRGB_TO_XYZ[2][0] * red + HDR_SRGB_TO_XYZ[2][1] * green + HDR_SRGB_TO_XYZ[2][2] * blue
    x *= brightness
    y *= brightness
    z *= brightness
    linear = (
        HDR_XYZ_TO_BT2020[0][0] * x + HDR_XYZ_TO_BT2020[0][1] * y + HDR_XYZ_TO_BT2020[0][2] * z,
        HDR_XYZ_TO_BT2020[1][0] * x + HDR_XYZ_TO_BT2020[1][1] * y + HDR_XYZ_TO_BT2020[1][2] * z,
        HDR_XYZ_TO_BT2020[2][0] * x + HDR_XYZ_TO_BT2020[2][1] * y + HDR_XYZ_TO_BT2020[2][2] * z,
    )
    return tuple(int(round(_pq_encode(value) * 255)) for value in linear)


def parse_ass_colour(digits: str):
    """解析 BBGGRR / AABBGGRR，返回 (alpha, (r, g, b))，格式不符时返回 None。"""
    if len(digits) == 8:
        alpha, body = digits[:2], digits[2:]
    elif len(digits) == 6:
        alpha, body = '', digits
    else:
        return None
    try:
        blue, green, red = int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)
    except ValueError:
        return None
    return alpha, (red, green, blue)


def format_ass_colour(alpha: str, rgb) -> str:
    red, green, blue = rgb
    return f'&H{alpha}{blue:02X}{green:02X}{red:02X}'


def hdrify_ass_colour(value: str, brightness: float = HDR_SUB_BRIGHTNESS) -> str:
    """把 ASS 的 &HAABBGGRR 颜色转换成 HDR 映射结果。"""
    text = value.strip()
    if not text.upper().startswith('&H'):
        return value
    parsed = parse_ass_colour(text[2:].rstrip('&'))
    if not parsed:
        return value
    alpha, rgb = parsed
    return format_ass_colour(alpha, srgb_to_hdr(rgb, brightness))


def hdrify_style_line(line: str, brightness: float = HDR_SUB_BRIGHTNESS) -> str:
    data = line.split(',')
    data[0] = data[0].replace('_SDR', '_HDR')
    for index in STYLE_COLOUR_FIELDS:
        data[index] = hdrify_ass_colour(data[index], brightness)
    return ','.join(data)


def hdrify_event_colours(text: str, brightness: float = HDR_SUB_BRIGHTNESS) -> str:
    """转换行内的 \\c&HBBGGRR& 等颜色标签。"""

    def replacer(match):
        prefix, digits = match.group(1), match.group(2)
        parsed = parse_ass_colour(digits)
        if not parsed:
            return match.group(0)
        alpha, rgb = parsed
        red, green, blue = srgb_to_hdr(rgb, brightness)
        return f'{prefix}{alpha}{blue:02X}{green:02X}{red:02X}'

    return match_inline_colour.sub(replacer, text)


SDR_STYLES = [
    'Style: ZH_Bilingual_SDR,思源黑体 Medium,80,&H00EAEAEA,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,14,1',
    'Style: ZH_Single_SDR,思源黑体 Medium,80,&H00EAEAEA,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,40,1',
    'Style: ZH_Annotation_SDR,思源黑体 Medium,66,&H00EAEAEA,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,8,0,0,14,1',
    'Style: ZH_lyrics_SDR,思源黑体 Medium,66,&H00EAEAEA,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,7,66,0,14,1',
    'Style: EN_Bilingual_SDR,思源黑体 Medium,52,&H003CA8DC,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,14,1',
    'Style: EN_Single_SDR,思源黑体 Medium,52,&H00EAEAEA,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,40,1',
]

# HDR 样式颜色不再手写，按 ssaHdrify 的映射从 SDR 样式实时生成
MID_BLACK_MARGINS = {
    'ZH_Bilingual': 58,
    'ZH_Single': 84,
    'ZH_Annotation': 58,
    'EN_Bilingual': 58,
    'EN_Single': 84,
}

def srt_time_to_ass(value: str):
    match = re.match(r'^\s*(\d+):(\d{1,2}):(\d{1,2})(?:[,.](\d{1,3}))?', value)
    if not match:
        return None
    hours, minutes, seconds, fraction = match.groups()
    fraction = fraction or '0'
    milliseconds = int(fraction.ljust(3, '0')[:3])
    return f'{int(hours)}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds // 10:02d}'

def srt_to_ass(text: str) -> str:
    blocks = re.split(r'\n\s*\n', text.strip())
    dialogues = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines()]
        time_index = None
        start = end = None
        for index, line in enumerate(lines):
            if '-->' in line:
                parts = line.split('-->')
                if len(parts) >= 2:
                    start = srt_time_to_ass(parts[0])
                    end = srt_time_to_ass(parts[1].strip().split()[0])
                    time_index = index
                break
        if time_index is None or start is None or end is None:
            continue
        text_lines = []
        for line in lines[time_index + 1:]:
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'<br\s*/?>', r'\\N', line, flags=re.I)
            line = re.sub(r'<[^>]+>', '', line)
            line = html.unescape(line).strip()
            if line:
                text_lines.append(line)
        if not text_lines:
            continue
        dialogue_text = r'\N'.join(text_lines)
        dialogues.append(f'Dialogue: 0,{start},{end},Default,,0,0,0,,{dialogue_text}\n')

    header = (
        '[Script Info]\n'
        'ScriptType: v4.00+\n'
        'PlayResX: 1920\n'
        'PlayResY: 1080\n'
        '\n'
        '[V4+ Styles]\n'
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
        'Style: Default,思源黑体 Medium,80,&H00EAEAEA,&HF0000000,&H000D0500,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,66,1\n'
        '\n'
        '[Events]\n'
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    )
    return header + ''.join(dialogues)

class Section(Enum):
    SCRIPT_INFO = 1
    STYLES = 2
    EVENTS = 3
    AEGISUB = 10
    OTHERS = 0

class Aegisub():
    def __init__(self, filename: str, is_HDR: bool = False, is_mid_black: bool = False):
        self.filename = filename
        self.raw_contents = []
        self.mode = Section.OTHERS
        self.xRatio = 1
        self.yRatio = 1
        self.is_HDR = is_HDR
        self.is_mid_black = is_mid_black
        self.hdr_brightness = HDR_SUB_BRIGHTNESS
        if is_HDR:
            self.contents = {
                '1-简英双语-HDR-zh': OUT_BILINGUAL,
                '3-简体中文-HDR-zh': OUT_CHS,
                '4-繁体中文-HDR-zh': OUT_CHT,
                '5-英文-HDR-en': OUT_ENG,
            }
        else:
            self.contents = {
                '1-简英双语-zh': OUT_BILINGUAL,
                '2-简体中文-zh': OUT_CHS,
                '3-繁体中文-zh': OUT_CHT,
                '4-英文-en': OUT_ENG,
            }
        self.notices = []
        self.notice_index = 0
        self.timeline_events = []
        self.style_alignments = {}
        self.source_has_cjk = False
        self.source_has_latin = False
        self.source_is_bilingual = False
        self.source_is_chinese_only = False
        self.source_order = 'zh_first'
        self.cht_indexes = []

    def add_notice(self, text: str, index: int = None):
        if index is None:
            index = self.notice_index
        self.notices.append(f'{index},{text}\n')

    def detect_source_type(self):
        total = 0
        cjk_only = 0
        latin_only = 0
        bilingual = 0
        zh_first = 0
        en_first = 0
        for line in self.raw_contents:
            if not match_events_dialogue.search(line):
                continue
            data = line.split(',', 9)
            if len(data) < 10:
                continue
            text = data[9]
            if has_special_effect(text):
                continue
            plain = match_override_tag.sub('', text)
            segments = [segment for segment in match_events_newline.split(plain) if segment.strip()]
            has_cjk = any(match_cjk.search(segment) for segment in segments)
            has_latin = any(match_latin.search(segment) for segment in segments)
            has_latin_only = any(
                match_latin.search(segment) and not match_cjk.search(segment)
                for segment in segments
            )
            if has_cjk:
                self.source_has_cjk = True
            if has_latin:
                self.source_has_latin = True
            if has_cjk and has_latin_only:
                bilingual += 1
            elif has_cjk:
                cjk_only += 1
            elif has_latin:
                latin_only += 1

            cjk_positions = [i for i, segment in enumerate(segments) if match_cjk.search(segment)]
            latin_only_positions = [
                i for i, segment in enumerate(segments)
                if match_latin.search(segment) and not match_cjk.search(segment)
            ]
            if cjk_positions and latin_only_positions:
                if min(cjk_positions) < min(latin_only_positions):
                    zh_first += 1
                else:
                    en_first += 1

            total += 1
        # 超过一半的对话事件中，中英文分属不同字幕行时，才按双语片源处理
        self.source_is_bilingual = total > 0 and bilingual * 2 >= total
        chinese_events = cjk_only + bilingual
        self.source_is_chinese_only = (
            not self.source_is_bilingual
            and chinese_events > latin_only
            and chinese_events > 0
        )
        self.source_order = 'zh_first' if zh_first >= en_first else 'en_first'

    def get_event_alignment(self, text: str, style_name: str, is_annotation: bool) -> int:
        matches = re.findall(r'\\an(\d)', text)
        if matches:
            return int(matches[-1])
        if is_annotation:
            return 8
        return self.style_alignments.get(style_name.lower(), 2)

    def check_timeline_overlaps(self):
        def is_exempt(first: int, second: int) -> bool:
            # 底部对白与顶部注释/顶部字幕重叠时，不提示
            return ((first == 2 and second in (7, 8)) or
                    (second == 2 and first in (7, 8)))

        events = sorted(self.timeline_events, key=lambda event: (event['start'], event['end']))
        active = []
        for event in events:
            active = [item for item in active if item['end'] > event['start']]
            for previous in active:
                if not is_exempt(previous['align'], event['align']):
                    self.notices.append(
                        f"{event['index']},与第{previous['index']}条字幕时间轴重叠,请处理\n"
                    )
                    break
            active.append(event)

    def set_xRatio(self, xRatio: float):
        self.xRatio = xRatio

    def set_yRatio(self, yRatio: float):
        self.yRatio = yRatio

    def read_file(self):
        with open(self.filename, 'rb') as f:
            raw = f.read()

        # 自动识别常见字幕编码：UTF-8 / UTF-16 / GB18030(GBK)
        if raw.startswith(b'\xef\xbb\xbf'):
            text = raw.decode('utf-8-sig')
        elif raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            text = raw.decode('utf-16')
        elif b'\x00' in raw[:4]:
            # 无 BOM 的 UTF-16 LE / BE
            text = raw.decode('utf-16-le') if raw[0] != 0 else raw.decode('utf-16-be')
        else:
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('gb18030')

        text = text.replace('\r\n', '\n').replace('\r', '\n')
        is_srt = self.filename.lower().endswith('.srt')
        if is_srt and '[Script Info]' in text and '[Events]' in text:
            is_srt = False
        if not is_srt and '[Script Info]' not in text and '[Events]' not in text and '-->' in text:
            is_srt = True
        if is_srt:
            text = srt_to_ass(text)
        self.raw_contents = text.splitlines(keepends=True)

    def match_function_move(self, match) -> str:
        if match:
            return rf'\move({float(match.group(1))*self.xRatio:.3f},{float(match.group(2))*self.yRatio:.3f},{float(match.group(3))*self.xRatio:.3f},{float(match.group(4))*self.yRatio:.3f}'

    def match_function_pos(self, match) -> str:
        if match:
            return rf'\pos({float(match.group(1))*self.xRatio:.3f},{float(match.group(2))*self.yRatio:.3f}'

    def match_function_org(self, match) -> str:
        if match:
            return rf'\org({float(match.group(1))*self.xRatio:.3f},{float(match.group(2))*self.yRatio:.3f}'

    def match_function_iclip(self, match) -> str:
        if match:
            return rf'\iclip({float(match.group(1))*self.xRatio:.3f},{float(match.group(2))*self.yRatio:.3f},{float(match.group(3))*self.xRatio:.3f},{float(match.group(4))*self.yRatio:.3f}'

    def match_function_clip(self, match) -> str:
        if match:
            return rf'\clip({float(match.group(1))*self.xRatio:.3f},{float(match.group(2))*self.yRatio:.3f},{float(match.group(3))*self.xRatio:.3f},{float(match.group(4))*self.yRatio:.3f}'

    def match_function_fs(self, match) -> str:
        if match:
            return rf'\fs{round(int(match.group(1)) * self.yRatio)}'

def get_style_name(sub: Aegisub, kind: str) -> str:
    return f'{kind}_{"HDR" if sub.is_HDR else "SDR"}'

def get_styles(sub: Aegisub) -> list:
    if sub.is_HDR:
        brightness = getattr(sub, 'hdr_brightness', HDR_SUB_BRIGHTNESS)
        styles = [hdrify_style_line(line, brightness) for line in SDR_STYLES]
    else:
        styles = SDR_STYLES.copy()
    if not sub.is_mid_black:
        return styles.copy()

    result = []
    for line in styles:
        data = line.split(',')
        kind = data[0].replace('Style: ', '').rsplit('_', 1)[0]
        if kind in MID_BLACK_MARGINS:
            data[STYLE_MARGIN_V_FIELD] = str(MID_BLACK_MARGINS[kind])
        result.append(','.join(data))

    return result

def build_sdr_bilingual_lines(sub: Aegisub, lines: list) -> list:
    """把 HDR 双语内容转成 SDR 版：换回 SDR 样式，并把样式引用改回 _SDR。"""
    original = sub.is_HDR
    sub.is_HDR = False
    try:
        sdr_styles = get_styles(sub)
    finally:
        sub.is_HDR = original
    result = []
    styles_inserted = False
    for line in lines:
        if line.startswith('Style: '):
            if not styles_inserted:
                result.extend(f'{style}\n' for style in sdr_styles)
                styles_inserted = True
            continue
        result.append(line.replace('_HDR', '_SDR'))
    return result


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

CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.cmct_style_adjustment_v2.json')

def load_config() -> dict:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_config(data: dict):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_script_info(meta: dict = None) -> str:
    meta = meta or {}

    def value(key: str) -> str:
        return str(meta.get(key, '') or '').strip()

    return (
        "[Script Info]\n"
        f"Title: {value('title')}\n"
        f"Original Script: {value('original_script')}\n"
        f"Original Translation: {value('original_translation')}\n"
        f"Original Timing: {value('original_timing')}\n"
        f"Original Editing: {value('original_editing')}\n"
        f"Script Updated By: {value('script_updated_by')}\n"
        "Update Details: \n"
        "ScriptType: v4.00+\n"
        "Collisions: Normal\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "Timer: 100.0000\n"
        "Synch Point: \n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: no\n"
        "YCbCr Matrix: TV.709\n"
        "\n"
    )

def parse_ass_time(value: str):
    """把 ASS 时间 H:MM:SS.cc 转为毫秒。"""
    match = re.match(r'^(\d+):(\d{1,2}):(\d{1,2})(?:[.,](\d{1,3}))?$', value.strip())
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    fraction = match.group(4) or ''
    if len(fraction) == 3:
        milliseconds = int(fraction)
    elif len(fraction) == 2:
        milliseconds = int(fraction) * 10
    elif len(fraction) == 1:
        milliseconds = int(fraction) * 100
    else:
        milliseconds = 0
    return ((hours * 3600 + minutes * 60 + seconds) * 1000) + milliseconds

LYRIC_MARKERS = re.compile(r'[∮♩♪♫♬*#＊＃]')
DIALOGUE_PREFIX_TAGS = re.compile(r'^((?:\{[^}]*\})*)')
HYPHEN_PLACEHOLDER = '\u0000'

# 英文行中的全角 ASCII 字符统一转半角
FULLWIDTH_ASCII_MAP = str.maketrans({
    '！': '!', '＂': '"', '＃': '#', '＄': '$', '％': '%', '＆': '&',
    '＇': "'", '（': '(', '）': ')', '＊': '*', '＋': '+', '，': ',',
    '－': '-', '．': '.', '／': '/', '：': ':', '；': ';', '＜': '<',
    '＝': '=', '＞': '>', '？': '?', '＠': '@', '［': '[', '＼': '\\',
    '］': ']', '＾': '^', '＿': '_', '｀': '`', '｛': '{', '｜': '|',
    '｝': '}', '～': '~',
    '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
    '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
    'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
    'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L',
    'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
    'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X',
    'Ｙ': 'Y', 'Ｚ': 'Z',
    'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
    'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j', 'ｋ': 'k', 'ｌ': 'l',
    'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r',
    'ｓ': 's', 'ｔ': 't', 'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x',
    'ｙ': 'y', 'ｚ': 'z',
})

# 中文行只把全角数字、字母转半角，保留全角括号等规定符号
FULLWIDTH_ALNUM_MAP = str.maketrans(dict(
    [(chr(0xFF10 + i), chr(0x30 + i)) for i in range(10)] +
    [(chr(0xFF21 + i), chr(0x41 + i)) for i in range(26)] +
    [(chr(0xFF41 + i), chr(0x61 + i)) for i in range(26)]
))

def apply_outside_tags(text: str, func) -> str:
    """只处理花括号外的文字，保持 ASS 标签不变。"""
    parts = match_override_split.split(text)
    for index in range(0, len(parts), 2):
        parts[index] = func(parts[index])
    return ''.join(parts)

@lru_cache(maxsize=20000)
def convert_zh(text: str, target: str) -> str:
    """转换简繁；繁体输出把成对引号换成直角引号「」。"""
    text = zhconv.convert(text, target)
    if target == 'zh-hant':
        text = corner_brackets(text)
    return text

def convert_outside_tags(text: str, target: str) -> str:
    return apply_outside_tags(text, lambda part: convert_zh(part, target))

def is_word_char(char: str) -> bool:
    return bool(char) and (char.isalnum() or bool(match_cjk.match(char)))

def complete_quotes(text: str) -> str:
    """单条字幕中只有一个引号时，尝试补齐成对引号。"""
    positions = [index for index, char in enumerate(text) if char == '"']
    if len(positions) % 2 == 1:
        last = positions[-1]
        after = match_override_tag.sub('', text[last + 1:]).strip()
        if not after:
            # 引号在句尾，补一个开引号
            match = re.match(r'^((?:\{[^}]*\})*(?:\s*-\s*)?)', text)
            prefix = match.group(1) if match else ''
            text = prefix + '"' + text[len(prefix):]
        else:
            # 引号在句首或行中，补一个闭引号
            text = text.rstrip() + '"'
    return text

def format_quotes(text: str) -> str:
    """引号外侧加空格，引号内侧不留空格。"""
    text = complete_quotes(text)
    result = []
    inside = False
    index = 0
    length = len(text)

    while index < length:
        char = text[index]
        if char == '"':
            if not inside:
                if result and result[-1] != ' ' and is_word_char(result[-1]):
                    result.append(' ')
                result.append('"')
                inside = True
                index += 1
                while index < length and text[index] == ' ':
                    index += 1
                continue
            else:
                while result and result[-1] == ' ':
                    result.pop()
                result.append('"')
                inside = False
                if index + 1 < length and text[index + 1] != ' ' and is_word_char(text[index + 1]):
                    result.append(' ')
        else:
            result.append(char)
        index += 1

    return ''.join(result)

def corner_brackets(text: str) -> str:
    """把成对的半角引号换成直角引号，跳过样式标签内的内容。"""
    result = []
    opening = True
    in_tag = False
    for char in text:
        if char == '{':
            in_tag = True
        elif char == '}':
            in_tag = False
        if char == '"' and not in_tag:
            result.append('「' if opening else '」')
            opening = not opening
        else:
            result.append(char)
    return ''.join(result)

def format_dialogue_dashes(text: str) -> str:
    """区分对话符和英文复合词连字符，并统一对话符前后空格。"""
    # 先把各种横线统一为半角连字符
    text = text.replace('–', '-').replace('—', '-').replace('－', '-')
    # 行内连字符：free- will -> free-will
    text = re.sub(r'(?<=\S)-\s+', '-', text)
    # 前后都不是空格的连字符视为复合词/编号连字符，例如 twenty-three、6188-祖鲁
    text = re.sub(r'(?<=\S)-(?=\S|$)', HYPHEN_PLACEHOLDER, text)
    text = re.sub(r'\s*-\s*', ' - ', text)
    text = re.sub(r'^\s*-\s*', '- ', text)
    text = re.sub(r'^-\s+$', '-', text)
    return text.replace(HYPHEN_PLACEHOLDER, '-')

def normalize_zh_ellipsis(text: str) -> str:
    """中文省略号：只保留文字后的全角省略号。"""
    text = text.replace('……', '…')
    text = text.replace('···', '…')
    text = re.sub(r'\.{2,}', '…', text)
    text = re.sub(r'…{2,}', '…', text)
    text = text.replace('——', '…')
    text = re.sub(r'--+', '…', text)
    # 句首省略号
    text = re.sub(r'^(\s*-\s*)…+', r'\1', text)
    text = re.sub(r'^\s*…+', '', text)
    # 对话符后的省略号
    text = re.sub(r'(\s-\s*)…+', r'\1', text)
    # 句首引号、括号后的省略号
    text = re.sub(r'([「『"]\s*)…+', r'\1', text)
    text = re.sub(r'([（(]\s*)…+', r'\1', text)
    # 文字后的省略号，后面仍有文字时补一个空格
    text = re.sub(r'…(?=[^\s…])', '… ', text)
    return text

def process_zh(text: str, is_music: bool = False) -> str:
    def _process(part: str) -> str:
        # 参考 SrtEdit 中文标点替换表
        part = part.translate(FULLWIDTH_ALNUM_MAP)
        part = part.replace('﹟', ' ')
        part = part.replace('〝', '"').replace('〞', '"')
        part = part.replace('‥', '…')
        part = part.replace('－', '-')
        part = part.replace('\u200e', ' ')
        part = part.replace('\u200b', '').replace('\u200c', '')
        part = part.replace('\u200d', '').replace('\u2060', '').replace('\ufeff', '')

        if is_music:
            part = re.sub(r'[∮♩♪♫♬*#＊＃]', ' ', part)
        else:
            part = re.sub(r'[∮♩♪♫♬]', ' ', part)

        # 引号先统一成半角
        part = part.replace('“', '"').replace('”', '"')
        part = part.replace('「', '"').replace('」', '"')
        part = part.replace('『', '"').replace('』', '"').replace('＂', '"')
        part = part.replace('‘', "'").replace('’', "'").replace('＇', "'")
        part = part.replace('［', '[').replace('］', ']')
        part = part.replace('【', '[').replace('】', ']')
        part = part.replace('[', '（').replace(']', '）')

        part = normalize_zh_ellipsis(part)

        # 中文标点替换为一个空格（ASCII 句点保留，避免破坏数字小数）
        part = re.sub(r'[，。！？、：；．,!?:;<>＜＞]', ' ', part)
        part = part.replace('~', '…')
        part = re.sub(r'…{2,}', '…', part)

        # 省略号紧贴前面的文字（文字 … -> 文字…）
        part = re.sub(r'\s+…+', '…', part)

        # 间隔号用于人名，前后不加空格
        part = part.replace('•', '·').replace('・', '·').replace('･', '·')
        part = re.sub(r'\s*·\s*', '·', part)

        # 书名号、括号内侧不加空格
        part = re.sub(r'《\s*', '《', part)
        part = re.sub(r'\s*》', '》', part)
        part = re.sub(r'（\s*', '（', part)
        part = re.sub(r'\s*）', '）', part)

        part = format_quotes(part)
        part = format_dialogue_dashes(part)
        part = re.sub(r'\s+', ' ', part)
        return part.strip()

    return apply_outside_tags(text, _process)

def process_en_commas(text: str) -> str:
    result = []
    for index, char in enumerate(text):
        if index == 0 and char == ',':
            continue
        result.append(char)
        if char == ',' and index < len(text) - 1:
            next_char = text[index + 1]
            prev_char = text[index - 1]
            if next_char not in ' "':
                if prev_char.isdigit() and next_char.isdigit():
                    continue
                result.append(' ')
    return ''.join(result)

def wrap_lyrics(text: str) -> str:
    match = DIALOGUE_PREFIX_TAGS.match(text)
    prefix = match.group(1) if match else ''
    body = text[len(prefix):].strip()
    if not body:
        return text
    return prefix + '♪ ' + body + ' ♪'

def process_en(text: str, is_music: bool = False) -> str:
    def _process(part: str) -> str:
        # 先统一全角 ASCII，避免全角歌词符号漏处理
        part = part.translate(FULLWIDTH_ASCII_MAP)
        part = part.replace('>>', '')

        if is_music:
            part = re.sub(r'[∮♩♪♫♬*#]', ' ', part)
        else:
            part = re.sub(r'[∮♩♪♫♬]', ' ', part)

        # 全角句号转半角（其余全角 ASCII 已由上面的映射处理）
        part = part.replace('。', '.')
        part = part.replace('？', '?').replace('：', ':').replace('；', ';')
        part = part.replace('（', '(').replace('）', ')')
        part = part.replace('、', ',')
        part = part.replace('“', '"').replace('”', '"')
        part = part.replace('「', '"').replace('」', '"')
        part = part.replace('‘', "'").replace('’', "'")
        part = part.replace('《', '"').replace('》', '"')
        part = part.replace('【', '[').replace('】', ']')
        part = part.replace('–', '-').replace('—', '-')
        part = part.replace('～', '~')

        # 省略号统一为英文三点
        part = part.replace('……', '...').replace('…', '...')
        part = re.sub(r'\.{4,}', '...', part)
        part = re.sub(r'(?<!\.)\.\.(?!\.)', '...', part)
        part = part.replace('. . .', '...')
        part = part.replace('... ...', '...')
        part = part.replace('--', '...')
        part = part.replace('- -', '...')

        # 单词后的省略号紧贴单词，如 and ... -> and...
        part = re.sub(r'(?<=[A-Za-z0-9])\s+\.{3}', '...', part)

        # 删除句首省略号及对话符后的省略号
        part = re.sub(r'^(\s*-\s*)\.{3,}\s*', r'\1', part)
        part = re.sub(r'^\s*\.{3,}\s*', '', part)
        part = re.sub(r'(\s-\s*)\.{3,}\s*', r'\1', part)

        # 问号/感叹号后接省略号时保留空格
        part = re.sub(r'([?!])(\.{3})', r'\1 \2', part)

        # 问号、感叹号后补空格
        part = re.sub(r'([?!])(?=[^\s"\'\)\]\},.!?;:])', r'\1 ', part)

        # 句号后接大写字母时补空格
        part = re.sub(r'(?<=[a-z])\.(?=[A-Z])', '. ', part)

        part = process_en_commas(part)

        # 两个单引号视作双引号
        part = part.replace("''", '"')

        part = format_quotes(part)
        part = format_dialogue_dashes(part)

        # 单独的小写 i 修正为大写 I
        part = re.sub(r'\bi\b', 'I', part)

        part = re.sub(r'\s+', ' ', part)
        return part.strip()

    result = apply_outside_tags(text, _process)
    if is_music:
        result = wrap_lyrics(result)
    return result

def clean_segment(text: str) -> str:
    text = match_font_tag.sub('', text)
    text = match_reset_tag.sub('', text)
    text = match_font_size_tag.sub('', text)
    text = match_colour_tag.sub('', text)
    text = match_blur_tag.sub('', text)
    text = match_fsvp_tag.sub('', text)
    text = match_bold_tag.sub('', text)
    text = match_italic_tag.sub('', text)
    text = match_underline_tag.sub('', text)
    text = match_strike_tag.sub('', text)
    text = match_encoding_tag.sub('', text)
    text = match_empty_tag.sub('', text)
    return text.strip()

def count_dialogue_symbols(text: str) -> int:
    plain = plain_text(text)
    return len(re.findall(r'(^|\s)-(?=\s|$)', plain))

def starts_with_dialogue(text: str) -> bool:
    plain = plain_text(text)
    return plain.lstrip().startswith('- ')

def add_dialogue_prefix(text: str) -> str:
    match = DIALOGUE_PREFIX_TAGS.match(text)
    prefix = match.group(1) if match else ''
    rest = text[len(prefix):]
    if rest.startswith('- ') or rest == '-':
        return text
    return prefix + '- ' + rest

def fix_dialogue_pair(sub: Aegisub, zh: str, en: str):
    """检查中英文行对话符；单行出现对话符时至少应有 2 个。"""
    zh_count = count_dialogue_symbols(zh)
    en_count = count_dialogue_symbols(en)
    zh_start = starts_with_dialogue(zh)
    en_start = starts_with_dialogue(en)
    fixed = False

    # 先自动补齐句首对话符
    if zh_count == 1 and en_count == 1 and not zh_start and not en_start:
        zh = add_dialogue_prefix(zh)
        en = add_dialogue_prefix(en)
        fixed = True
    elif zh_count >= 2 and en_count == zh_count - 1 and en_count > 0 and not en_start:
        # 中文对话符齐全，英文只在句首少一个
        en = add_dialogue_prefix(en)
        fixed = True
    elif en_count >= 2 and zh_count == en_count - 1 and zh_count > 0 and not zh_start:
        # 英文对话符齐全，中文只在句首少一个
        zh = add_dialogue_prefix(zh)
        fixed = True

    if fixed:
        sub.add_notice('对话符缺失已修复,请验证')
    else:
        # 单行中只要有对话符，就必须至少 2 个（2 人及以上对话）
        if 0 < zh_count < 2 or 0 < en_count < 2:
            sub.add_notice('对话符缺失,请处理')
        elif zh_count == 0 and en_count > 0:
            sub.add_notice('对话符缺失,请处理')
        elif en_count == 0 and zh_count > 0:
            sub.add_notice('对话符缺失,请处理')
        elif zh_count != en_count:
            sub.add_notice('对话符数量不匹配,请处理')

    return zh, en

def plain_text(text: str) -> str:
    return match_override_tag.sub('', text).strip()

def build_dialogue(data: list, style: str, text: str, zero_margin: bool = True) -> str:
    result = data.copy()
    result[3] = style
    if zero_margin:
        result[7] = '0'
    result[9] = text
    return ','.join(result) + '\n'

def format_segments(segments: list, convert_to: str = None) -> str:
    result = []
    for index, segment in enumerate(segments):
        text = segment['text']
        if convert_to:
            text = convert_zh(text, convert_to)
        # 句首不重复定义，换行后的行才设置行间距；每行都补回 \blur2
        if index == 0:
            text = '{\\blur2}' + text
        else:
            text = '{\\fsvp12\\blur2}' + text
        result.append(text)
    return '\\N'.join(result)

def format_bilingual(sub: Aegisub, segments: list, convert_zh_to: str = None) -> str:
    result = []
    current_style = None
    for index, segment in enumerate(segments):
        kind = 'ZH_Bilingual' if segment['zh'] else 'EN_Bilingual'
        style = get_style_name(sub, kind)
        text = segment['text']
        if convert_zh_to and segment['zh']:
            text = convert_zh(text, convert_zh_to)
        if index == 0:
            text = '{\\blur2}' + text
        else:
            tags = []
            # 换行后需要行间距；语言切换时同时切换样式
            if style != current_style:
                tags.append('\\r' + style)
            tags.append('\\fsvp12')
            tags.append('\\blur2')
            text = '{' + ''.join(tags) + '}' + text
        result.append(text)
        current_style = style
    return '\\N'.join(result)

def format_lyrics_bilingual(sub: Aegisub, segments: list, convert_zh_to: str = None) -> str:
    style = get_style_name(sub, 'ZH_lyrics')
    result = []
    for index, segment in enumerate(segments):
        text = segment['text']
        if convert_zh_to and segment['zh']:
            text = convert_zh(text, convert_zh_to)
        if index == 0:
            text = '{\\blur2}' + text
        else:
            # 重置到歌词样式，保持 \an7 顶部对齐，并补回 \blur2
            text = '{\\r' + style + '\\fsvp12\\blur2}' + text
        result.append(text)
    return '\\N'.join(result)

def get_special_effect(sub: Aegisub, data: str) -> str:
    # 处理move
    data = match_events_move.sub(sub.match_function_move, data)

    # 处理pos
    data = match_events_pos.sub(sub.match_function_pos, data)

    # 处理org
    data = match_events_org.sub(sub.match_function_org, data)

    # 处理iclip/clip
    data = match_events_iclip.sub(sub.match_function_iclip, data)
    data = match_events_clip.sub(sub.match_function_clip, data)

    return data

def fill_line(contents: dict, text: str):
    for key in contents:
        contents[key].append(text)


def fill_line_except_eng(contents: dict, text: str):
    """写入除英文以外的输出（注释行不进入英文文件）。"""
    for key in contents:
        if key != OUT_ENG:
            contents[key].append(text)

def fill_dialogue(sub: Aegisub, contents: dict, line: str):
    sub.notice_index += 1
    data = line.split(',', 9)
    if len(data) < 10:
        for key in contents:
            contents[key].append(line)
        return

    start_ms = parse_ass_time(data[1])
    end_ms = parse_ass_time(data[2])
    if start_ms is not None and end_ms is not None and end_ms - start_ms < 500:
        sub.add_notice('时间轴长度低于500ms,请处理')

    if not data[9]:
        return
    if data[9].endswith('\n'):
        data[9] = data[9][:-1]
    text = data[9]
    style_name = data[3].strip()
    align_matches = re.findall(r'\\an(\d)', text)
    if align_matches:
        base_alignment = int(align_matches[-1])
    else:
        base_alignment = sub.style_alignments.get(style_name.lower(), 2)

    # 特效字幕只保留到中文相关输出，英文文件剔除
    if has_special_effect(text):
        sub.add_notice('疑似特效字幕,请处理')
        text = match_events_fs.sub(sub.match_function_fs, text)
        text = get_special_effect(sub, text)
        text = match_blur3_tag.sub('', text)
        text = match_empty_tag.sub('', text)
        if base_alignment == 8:
            special_style = get_style_name(sub, 'ZH_Annotation')
        elif base_alignment == 7:
            special_style = get_style_name(sub, 'ZH_lyrics')
        elif match_cjk.search(plain_text(text)):
            special_style = get_style_name(sub, 'ZH_Single')
        else:
            special_style = get_style_name(sub, 'EN_Single')
        result_chs = build_dialogue(
            data, special_style, convert_outside_tags(text, 'zh-hans'), zero_margin=False)
        result_cht = build_dialogue(
            data, special_style, convert_outside_tags(text, 'zh-hans'), zero_margin=False)
        contents[OUT_BILINGUAL].append(result_chs)
        contents[OUT_CHS].append(result_chs)
        sub.cht_indexes.append(sub.notice_index)
        contents[OUT_CHT].append(result_cht)
        return

    is_annotation = base_alignment == 8
    is_lyrics = base_alignment == 7
    is_music = bool(LYRIC_MARKERS.search(plain_text(text)))
    segments = []
    for raw in match_events_newline.split(text):
        segment = clean_segment(raw)
        if not segment:
            continue
        plain = plain_text(segment)
        if not plain:
            continue
        is_chinese = bool(match_cjk.search(plain))
        is_english = (not is_chinese) and bool(match_latin.search(plain))
        if is_chinese:
            segment = process_zh(segment, is_music)
        elif is_english:
            segment = process_en(segment, is_music)
        else:
            segment = process_zh(segment, is_music)
        plain = plain_text(segment)
        if not plain:
            continue
        segments.append({'text': segment, 'zh': not is_english, 'en': is_english})

    if not segments:
        return

    # 双语片源中，两行字幕固定为“中文行 + 英文行”。
    # 即使中文行未翻译、只剩英文/数字，也保持中文行的样式槽位。
    if sub.source_is_bilingual and len(segments) == 2:
        english_index = 1 if sub.source_order == 'zh_first' else 0
        if not match_cjk.search(plain_text(segments[english_index]['text'])):
            for index, segment in enumerate(segments):
                is_zh_slot = (index == 0) if sub.source_order == 'zh_first' else (index == 1)
                segment['zh'] = is_zh_slot
                segment['en'] = not is_zh_slot

    zh_segments = [segment for segment in segments if segment['zh']]
    en_segments = [segment for segment in segments if segment['en']]

    # 中文字幕行没有中文，只有数字/英文/连字符
    for segment in zh_segments:
        plain = plain_text(segment['text'])
        if not match_cjk.search(plain) and re.fullmatch(r'[0-9A-Za-z\-\s]+', plain):
            sub.add_notice('中文行无中文,请验证')
            break

    if len(segments) > 2:
        if base_alignment == 2:
            sub.add_notice('字幕行数大于2,请处理')
        else:
            sub.add_notice('疑似多行注释,请处理')

    if is_music:
        if zh_segments and en_segments:
            sub.add_notice('疑似双语歌词,请检查')
        elif en_segments:
            sub.add_notice('疑似单英语歌词,请检查')
        else:
            sub.add_notice('疑似歌词,请检查')

    # 无 \an8 的双行纯中文字幕，按注释处理并补上 \an8
    auto_annotation = False
    if (not is_annotation and not align_matches and base_alignment == 2
            and len(zh_segments) == 2 and not en_segments
            and all(match_cjk.search(plain_text(segment['text'])) for segment in zh_segments)):
        is_annotation = True
        auto_annotation = True
        segments[0]['text'] = '{\\an8}' + segments[0]['text']

    if start_ms is not None and end_ms is not None:
        alignment = sub.get_event_alignment(text, style_name, is_annotation)
        sub.timeline_events.append({
            'index': sub.notice_index,
            'start': start_ms,
            'end': end_ms,
            'align': alignment,
        })

    if is_annotation:
        if auto_annotation:
            sub.add_notice('疑似双行注释,请检查')
        else:
            sub.add_notice('疑似注释,请检查')
        style = get_style_name(sub, 'ZH_Annotation')
        text_chs = format_segments(segments, convert_to='zh-hans')
        contents[OUT_BILINGUAL].append(build_dialogue(data, style, text_chs))
        contents[OUT_CHS].append(build_dialogue(data, style, text_chs))
        text_cht = format_segments(segments, convert_to='zh-hans')
        sub.cht_indexes.append(sub.notice_index)
        contents[OUT_CHT].append(build_dialogue(data, style, text_cht))
        return

    # 双语字幕中出现的单语行，提示人工检查
    if sub.source_is_bilingual and not is_music:
        if len(en_segments) > 1 and not zh_segments:
            sub.add_notice('疑似多行英文没有对应中文翻译,请处理')
        elif len(en_segments) == 1 and not zh_segments:
            sub.add_notice('疑似单行纯英文,请处理')
        elif len(zh_segments) == 1 and not en_segments:
            sub.add_notice('双语字幕发现疑似中文单语对话,请处理')

    # 对话符检查：单行出现对话符时至少应有 2 个
    if not is_music:
        if len(zh_segments) == 1 and len(en_segments) == 1:
            zh_text, en_text = fix_dialogue_pair(sub, zh_segments[0]['text'], en_segments[0]['text'])
            for segment in segments:
                segment['text'] = zh_text if segment['zh'] else en_text
            zh_segments = [segment for segment in segments if segment['zh']]
            en_segments = [segment for segment in segments if segment['en']]
        else:
            if any(0 < count_dialogue_symbols(segment['text']) < 2 for segment in segments):
                sub.add_notice('对话符缺失,请处理')
            elif zh_segments and en_segments:
                zh_total = sum(count_dialogue_symbols(segment['text']) for segment in zh_segments)
                en_total = sum(count_dialogue_symbols(segment['text']) for segment in en_segments)
                if zh_total == 0 and en_total > 0:
                    sub.add_notice('对话符缺失,请处理')
                elif en_total == 0 and zh_total > 0:
                    sub.add_notice('对话符缺失,请处理')
                elif zh_total != en_total:
                    sub.add_notice('对话符数量不匹配,请处理')

    # 单行长度与中文行阿拉伯数字检查
    zh_len = max((len(plain_text(segment['text'])) for segment in zh_segments), default=0)
    en_len = max((len(plain_text(segment['text'])) for segment in en_segments), default=0)
    if zh_len > 28 or en_len > 84:
        if zh_len and en_len:
            sub.add_notice(f'单行过长，英文：{en_len}，中文：{zh_len},请处理')
        elif zh_len:
            sub.add_notice(f'单行过长，中文：{zh_len},请处理')
        else:
            sub.add_notice(f'单行过长，英文：{en_len},请处理')
    if any(re.search(r'\d', plain_text(segment['text'])) for segment in zh_segments):
        sub.add_notice('存在阿拉伯数字,请检查')

    if zh_segments and en_segments:
        # 双语：按原顺序输出，逐行切换中/英样式
        if is_lyrics:
            bilingual_style = get_style_name(sub, 'ZH_lyrics')
            bilingual_text = format_lyrics_bilingual(sub, segments, convert_zh_to='zh-hans')
        else:
            first_kind = 'ZH_Bilingual' if segments[0]['zh'] else 'EN_Bilingual'
            bilingual_style = get_style_name(sub, first_kind)
            bilingual_text = format_bilingual(sub, segments, convert_zh_to='zh-hans')
        contents[OUT_BILINGUAL].append(build_dialogue(
            data, bilingual_style, bilingual_text))

        if is_lyrics:
            chinese_style = get_style_name(sub, 'ZH_lyrics')
            english_style = get_style_name(sub, 'ZH_lyrics')
        else:
            chinese_style = get_style_name(sub, 'ZH_Single')
            english_style = get_style_name(sub, 'EN_Single')
        contents[OUT_CHS].append(build_dialogue(
            data, chinese_style, format_segments(zh_segments, convert_to='zh-hans')))
        sub.cht_indexes.append(sub.notice_index)
        contents[OUT_CHT].append(build_dialogue(
            data, chinese_style, format_segments(zh_segments, convert_to='zh-hans')))
        contents[OUT_ENG].append(build_dialogue(
            data, english_style, format_segments(en_segments)))
    elif zh_segments:
        style = get_style_name(sub, 'ZH_lyrics' if is_lyrics else 'ZH_Single')
        text_chs = format_segments(zh_segments, convert_to='zh-hans')
        contents[OUT_BILINGUAL].append(build_dialogue(data, style, text_chs))
        contents[OUT_CHS].append(build_dialogue(data, style, text_chs))
        text_cht = format_segments(zh_segments, convert_to='zh-hans')
        sub.cht_indexes.append(sub.notice_index)
        contents[OUT_CHT].append(build_dialogue(data, style, text_cht))
    else:
        style = get_style_name(sub, 'ZH_lyrics' if is_lyrics else 'EN_Single')
        text_eng = format_segments(en_segments)
        contents[OUT_BILINGUAL].append(build_dialogue(data, style, text_eng))
        contents[OUT_ENG].append(build_dialogue(data, style, text_eng))
    

def build_success_message(html_path, output_dir, chinese_only=False, is_HDR=False):
    html_name = os.path.basename(html_path) if html_path else NOTICES_REPORT_NAME
    occupied_note = ''
    if html_name != NOTICES_REPORT_NAME:
        occupied_note += f"\n注意：{NOTICES_REPORT_NAME} 正在被占用，本次已写入 {html_name}"

    if chinese_only:
        if is_HDR:
            count = 3
            file_lines = [
                "1-简体中文-HDR-zh.ass（简体中文）",
                "2-简体中文-SDR-zh.ass（简体中文 SDR）",
                "3-繁体中文-HDR-zh.ass（繁体中文）",
            ]
        else:
            count = 2
            file_lines = [
                "1-简体中文-zh.ass（简体中文）",
                "2-繁体中文-zh.ass（繁体中文）",
            ]
    elif is_HDR:
        count = 5
        file_lines = [
            "1-简英双语-HDR-zh.ass（简英双语）",
            "2-简英双语-SDR-zh.ass（简英双语 SDR）",
            "3-简体中文-HDR-zh.ass（简体中文）",
            "4-繁体中文-HDR-zh.ass（繁体中文）",
            "5-英文-HDR-en.ass（英文）",
        ]
    else:
        count = 4
        file_lines = [
            "1-简英双语-zh.ass（简英双语）",
            "2-简体中文-zh.ass（简体中文）",
            "3-繁体中文-zh.ass（繁体中文）",
            "4-英文-en.ass（英文）",
        ]

    lines = [f"已生成 {count} 个字幕文件到文件夹：", output_dir, ""] + file_lines + [
        f"{html_name}（可视化报告）",
    ]
    if output_dir and os.path.exists(os.path.join(output_dir, TAIWAN_REPORT_NAME)):
        lines.append(f"{TAIWAN_REPORT_NAME}（繁化姬台湾化对比）")
    return '\n'.join(lines) + occupied_note


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


REPORT_CSS = """* { box-sizing: border-box; }
body {
    margin: 0;
    padding: 28px;
    background: #eef2f7;
    color: #263238;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
}
.container {
    max-width: 1080px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 14px;
    box-shadow: 0 10px 30px rgba(30, 45, 70, 0.12);
    overflow: hidden;
}
.header {
    padding: 24px 30px 18px;
    background: linear-gradient(135deg, #243b53 0%, #3b5b7a 100%);
    color: #ffffff;
}
.header h1 {
    margin: 0 0 10px;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.meta {
    font-size: 13px;
    color: #d9e2ec;
    line-height: 1.8;
}
.summary {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    padding: 18px 30px;
    background: #f8fafc;
    border-bottom: 1px solid #e5e9f0;
}
.stat {
    min-width: 120px;
    padding: 10px 14px;
    border-radius: 10px;
    background: #ffffff;
    border: 1px solid #e5e9f0;
    font-size: 13px;
    color: #52606d;
}
.stat b {
    display: block;
    margin-top: 4px;
    font-size: 20px;
    color: #243b53;
}
.stat.verify b {
    color: #b7791f;
}
.stat.check b {
    color: #64748b;
}
.stat.process b {
    color: #dc2626;
}
.chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 14px 30px 4px;
}
.chip {
    padding: 5px 10px;
    border-radius: 999px;
    background: #edf2f7;
    color: #486581;
    font-size: 12px;
}
.chip b {
    color: #243b53;
}
.alert {
    flex-basis: 100%;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    color: #b45309;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 13px;
}
.table-wrap {
    padding: 12px 30px 30px;
    max-height: 65vh;
    overflow: auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
th {
    position: sticky;
    top: 0;
    background: #334e68;
    color: #ffffff;
    text-align: left;
    padding: 12px 14px;
    font-weight: 600;
}
td {
    padding: 11px 14px;
    border-bottom: 1px solid #e5e9f0;
    vertical-align: top;
}
tbody tr:nth-child(even) {
    background: #f8fafc;
}
tbody tr:hover {
    background: #eef6ff;
}
tbody td:first-child {
    border-left: 4px solid transparent;
}
tbody tr.check td:first-child {
    border-left-color: #cbd5e1;
}
tbody tr.verify td:first-child {
    border-left-color: #f59e0b;
}
tbody tr.process td:first-child {
    border-left-color: #dc2626;
}
td.line {
    width: 80px;
    font-weight: 700;
    color: #2b6cb0;
}
td.before {
    width: 42%;
    color: #52606d;
}
.badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}
.badge.check {
    background: #e6ebf1;
    color: #5b6b7f;
    font-weight: 500;
}
.badge.verify {
    background: #fef3c7;
    color: #92400e;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(245, 158, 11, 0.20);
}
.badge.process {
    background: #dc2626;
    color: #ffffff;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(220, 38, 38, 0.25);
}
ins {
    background: #dcfce7;
    color: #166534;
    text-decoration: none;
    padding: 0 1px;
    border-radius: 3px;
}
del {
    background: #fee2e2;
    color: #991b1b;
    padding: 0 1px;
    border-radius: 3px;
}
.empty {
    padding: 48px 20px;
    text-align: center;
    color: #718096;
    font-size: 15px;
}"""


def render_report_page(page_title: str, heading: str, meta_html: str,
                       summary_html: str, table_html: str, chips_html: str = '') -> str:
    chips = f'<div class="chips">{chips_html}</div>' if chips_html else ''
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{page_title}</title>
<style>
{REPORT_CSS}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{heading}</h1>
        <div class="meta">{meta_html}</div>
    </div>
    <div class="summary">{summary_html}</div>
    {chips}
    <div class="table-wrap">{table_html}</div>
</div>
</body>
</html>'''


def build_notices_html(filename: str, title: str, notices: list, source_label: str = '') -> str:
    rows = []
    type_counts = Counter()
    verify_count = 0
    check_count = 0
    process_count = 0

    for notice in notices:
        line = notice.strip()
        if not line:
            continue
        parts = line.split(',', 2)
        if len(parts) < 3:
            continue
        line_no, problem, need = parts[0], parts[1], parts[2]
        type_counts[problem] += 1
        if '请验证' in need:
            verify_count += 1
            need_class = 'verify'
        elif '请处理' in need:
            process_count += 1
            need_class = 'process'
        else:
            check_count += 1
            need_class = 'check'
        rows.append(
            f'<tr class="{need_class}">'
            f'<td class="line">{html.escape(line_no)}</td>'
            f'<td>{html.escape(problem)}</td>'
            f'<td><span class="badge {need_class}">{html.escape(need)}</span></td>'
            '</tr>'
        )

    type_chips = ''.join(
        f'<span class="chip">{html.escape(problem)} <b>{count}</b></span>'
        for problem, count in type_counts.most_common()
    )
    if rows:
        table = (
            '<table>'
            '<thead><tr><th>行号</th><th>问题</th><th>需要</th></tr></thead>'
            '<tbody>' + ''.join(rows) + '</tbody>'
            '</table>'
        )
    else:
        table = '<div class="empty">未发现问题</div>'

    summary = (
        f'<div class="stat">问题总数<b>{len(rows)}</b></div>'
        f'<div class="stat verify">请验证<b>{verify_count}</b></div>'
        f'<div class="stat check">请检查<b>{check_count}</b></div>'
        f'<div class="stat process">请处理<b>{process_count}</b></div>'
    )
    title_text = html.escape(title or '未命名')
    source = html.escape(source_label or os.path.basename(filename))
    return render_report_page(
        f'字幕问题检查报告 - {title_text}',
        '字幕问题检查报告',
        f'片名：{title_text}<br>源文件：{source}',
        summary,
        table,
        type_chips,
    )


def zhconvert_api(texts, converter=ZHCONVERT_CONVERTER):
    """批量调用繁化姬，返回与 texts 等长的转换结果；失败时抛出异常。"""
    results = []
    index = 0
    while index < len(texts):
        group = []
        size = 0
        while index + len(group) < len(texts):
            item = texts[index + len(group)]
            if group and size + len(item) + 1 > ZHCONVERT_MAX_CHARS:
                break
            group.append(item)
            size += len(item) + 1
        body = urllib.parse.urlencode({
            'converter': converter,
            'text': '\n'.join(group),
        }).encode('utf-8')
        request = urllib.request.Request(
            ZHCONVERT_API,
            data=body,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'User-Agent': 'ohMyAssNoto/1.0',
            },
        )
        last_error = None
        result = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=ZHCONVERT_TIMEOUT) as response:
                    result = json.loads(response.read().decode('utf-8'))
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.5)
        if result is None:
            raise last_error
        if not isinstance(result, dict):
            raise RuntimeError('繁化姬返回内容格式异常')
        if result.get('code') != 0:
            raise RuntimeError(result.get('msg') or '繁化姬返回错误')
        pieces = (result.get('data') or {}).get('text', '').split('\n')
        if len(pieces) != len(group):
            raise RuntimeError('繁化姬返回行数与提交行数不一致')
        results.extend(pieces)
        index += len(group)
    return results


def split_dialogue_text(text: str):
    """按 \\N 和覆盖标签拆分文本，返回 (排版, 可转换的文字片段)。"""
    layout = []
    parts = []
    for piece in text.split('\\N'):
        chunks = match_override_split.split(piece)
        layout.append(chunks)
        parts.extend(chunks[0::2])
    return layout, parts


def join_dialogue_text(layout, values):
    iterator = iter(values)
    pieces = []
    for chunks in layout:
        rebuilt = list(chunks)
        for position in range(0, len(rebuilt), 2):
            rebuilt[position] = next(iterator)
        pieces.append(''.join(rebuilt))
    return '\\N'.join(pieces)


def convert_cht_contents(lines, indexes=None, use_api=True):
    """把繁体输出转成台湾繁体。

    返回 (新行, 对比记录, 错误信息, 台湾化后超长行)。
    对比记录以普通繁体（本地简繁转换）为基准，与台湾化结果比较。
    """
    entries = []
    all_parts = []
    for line_index, line in enumerate(lines):
        if not line.startswith('Dialogue:'):
            continue
        data = line.split(',', 9)
        if len(data) < 10:
            continue
        suffix = '\n' if data[9].endswith('\n') else ''
        text = data[9][:-1] if suffix else data[9]
        layout, parts = split_dialogue_text(text)
        entries.append({
            'index': line_index,
            'data': data,
            'layout': layout,
            'parts': parts,
            'suffix': suffix,
            'text': text,
        })
        all_parts.extend(parts)

    # 普通繁体：本地简繁转换，作为对比基准
    local_parts = [zhconv.convert(part, 'zh-hant') for part in all_parts]
    taiwan_parts = local_parts
    error = ''
    if use_api and all_parts:
        try:
            taiwan_parts = zhconvert_api(all_parts)
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'

    result = list(lines)
    changes = []
    overlong = []
    cursor = 0
    for number, entry in enumerate(entries, 1):
        count = len(entry['parts'])
        taiwan_values = taiwan_parts[cursor:cursor + count]
        local_values = local_parts[cursor:cursor + count]
        cursor += count

        new_text = corner_brackets(join_dialogue_text(entry['layout'], taiwan_values))
        local_text = corner_brackets(join_dialogue_text(entry['layout'], local_values))
        data = list(entry['data'])
        data[9] = new_text + entry['suffix']
        result[entry['index']] = ','.join(data)

        before = plain_text(local_text).replace('\\N', ' / ')
        after = plain_text(new_text).replace('\\N', ' / ')
        if before != after:
            changes.append({
                'index': number,
                'time': entry['data'][1].strip(),
                'before': before,
                'after': after,
            })

        # 台湾化后重新做 28 字符检查；简体原文已超长的不重复提示
        simplified_pieces = entry['text'].split('\\N')
        for position, piece in enumerate(new_text.split('\\N')):
            source_piece = simplified_pieces[position] if position < len(simplified_pieces) else ''
            length = len(plain_text(piece))
            if length > 28 and len(plain_text(source_piece)) <= 28:
                event_index = None
                if indexes and number - 1 < len(indexes):
                    event_index = indexes[number - 1]
                overlong.append({
                    'index': event_index,
                    'time': entry['data'][1].strip(),
                    'length': length,
                })
    return result, changes, error, overlong


def build_diff_html(before: str, after: str) -> str:
    matcher = difflib.SequenceMatcher(None, before, after)
    pieces = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            pieces.append(html.escape(before[i1:i2]))
        elif tag == 'delete':
            pieces.append(f'<del>{html.escape(before[i1:i2])}</del>')
        elif tag == 'insert':
            pieces.append(f'<ins>{html.escape(after[j1:j2])}</ins>')
        else:
            pieces.append(
                f'<del>{html.escape(before[i1:i2])}</del>'
                f'<ins>{html.escape(after[j1:j2])}</ins>'
            )
    return ''.join(pieces)


def build_taiwan_compare_html(title: str, filename: str, changes: list, error: str = '') -> str:
    rows = []
    for change in changes:
        rows.append(
            f'<tr><td class="line">{change["index"]}</td>'
            f'<td class="before">{html.escape(change["before"])}</td>'
            f'<td>{build_diff_html(change["before"], change["after"])}</td></tr>'
        )
    if rows:
        table = (
            '<table><thead><tr>'
            '<th>#</th><th>普通繁体</th><th>台湾化（繁化姬）</th>'
            '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        )
    else:
        table = '<div class="empty">没有需要台湾化的改动</div>'

    chips = ''
    if error:
        chips = (
            '<div class="alert">繁化姬调用失败，已改用本地简繁转换：'
            f'{html.escape(error)}</div>'
        )

    title_text = html.escape(title or '未命名')
    source = html.escape(os.path.basename(filename))
    summary = f'<div class="stat">改动行数<b>{len(changes)}</b></div>'
    return render_report_page(
        f'繁体台湾化对比 - {title_text}',
        '繁体台湾化对比',
        f'片名：{title_text}<br>源文件：{source}',
        summary,
        table,
        chips,
    )


def process_file(filename: str, is_HDR: bool, is_mid_black: bool, meta: dict = None):
    meta = meta or {}
    sub = Aegisub(filename, is_HDR, is_mid_black)
    try:
        sub.hdr_brightness = float(meta.get('hdr_brightness', HDR_SUB_BRIGHTNESS))
    except (TypeError, ValueError):
        sub.hdr_brightness = HDR_SUB_BRIGHTNESS
    sub.read_file()
    sub.detect_source_type()

    if sub.source_is_chinese_only:
        if is_HDR:
            sub.contents = {
                '1-简体中文-HDR-zh': OUT_CHS,
                '3-繁体中文-HDR-zh': OUT_CHT,
            }
        else:
            sub.contents = {
                '1-简体中文-zh': OUT_CHS,
                '2-繁体中文-zh': OUT_CHT,
            }
    elif is_HDR:
        sub.contents = {
            '1-简英双语-HDR-zh': OUT_BILINGUAL,
            '3-简体中文-HDR-zh': OUT_CHS,
            '4-繁体中文-HDR-zh': OUT_CHT,
            '5-英文-HDR-en': OUT_ENG,
        }
    else:
        sub.contents = {
            '1-简英双语-zh': OUT_BILINGUAL,
            '2-简体中文-zh': OUT_CHS,
            '3-繁体中文-zh': OUT_CHT,
            '4-英文-en': OUT_ENG,
        }

    meta = meta or {}
    title = str(meta.get('title', '') or '').strip()
    updated_by = str(meta.get('script_updated_by', '') or '').strip()
    source_label = str(meta.get('source_label', '') or '').strip() or os.path.basename(filename)
    if not title:
        raise ValueError('片名为必填项，请填写后再生成')
    if not updated_by:
        raise ValueError('字幕员为必填项，请填写后再生成')

    output_dir = get_output_dir(filename, title, meta.get('output_root', ''))
    if output_dir is None:
        raise ValueError('片名不能用于文件夹名，请修改')
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        raise ValueError(f'无法创建输出文件夹：{exc}')

    contents = {
        OUT_BILINGUAL: [],
        OUT_CHS: [],
        OUT_CHT: [],
        OUT_ENG: [],
    }

    mode = Section.OTHERS
    script_info_written = False
    styles_written = False

    for line in sub.raw_contents:
        if match_paragraph_script_info.search(line):
            mode = Section.SCRIPT_INFO
            if not script_info_written:
                fill_line(contents, get_script_info(meta))
                script_info_written = True
        elif match_paragraph_styles.search(line):
            mode = Section.STYLES
            fill_line(contents, line)
        elif match_paragraph_events.search(line):
            if mode == Section.STYLES and not styles_written:
                for style_line in get_styles(sub):
                    fill_line(contents, f'{style_line}\n')
                styles_written = True
            mode = Section.EVENTS
            fill_line(contents, line)
        elif match_paragraph_aegisub.search(line):
            mode = Section.AEGISUB
        else:
            if mode == Section.SCRIPT_INFO:
                # 只读取原始分辨率用于坐标缩放，不输出原始 Script Info
                if match_script_info_play_x.search(line):
                    match = match_script_info_play_x.search(line)
                    sub.set_xRatio(1920 / int(match.group(1)))
                elif match_script_info_play_y.search(line):
                    match = match_script_info_play_y.search(line)
                    sub.set_yRatio(1080 / int(match.group(1)))
            elif mode == Section.STYLES:
                if line.lstrip().lower().startswith('style:'):
                    style_data = line.split(',')
                    if len(style_data) > 18:
                        style_name = style_data[0].split(':', 1)[1].strip()
                        try:
                            sub.style_alignments[style_name.lower()] = int(style_data[18])
                        except ValueError:
                            pass
                    continue
                if line == '\n':
                    if not styles_written:
                        for style_line in get_styles(sub):
                            fill_line(contents, f'{style_line}\n')
                        styles_written = True
                    fill_line(contents, line)
                else:
                    fill_line(contents, line)
            elif mode == Section.EVENTS:
                stripped = line.lstrip()
                if stripped.lower().startswith('comment:'):
                    # 注释行（通常是中文说明）不进入英文文件
                    fill_line_except_eng(contents, line)
                elif match_events_dialogue.search(line):
                    fill_dialogue(sub, contents, line)
                else:
                    fill_line(contents, line)
            elif mode == Section.AEGISUB:
                continue
            else:
                fill_line(contents, line)

    if not script_info_written:
        for key in contents:
            contents[key].insert(0, get_script_info(meta))

    # 繁体输出统一做台湾化：优先走繁化姬，失败时退回本地转换
    use_taiwan = bool(meta.get('taiwan', True))
    taiwan_error = ''
    if contents[OUT_CHT]:
        contents[OUT_CHT], taiwan_changes, taiwan_error, taiwan_overlong = convert_cht_contents(
            contents[OUT_CHT], sub.cht_indexes, use_api=use_taiwan)
        for item in taiwan_overlong:
            if use_taiwan:
                sub.add_notice(f'台湾化后单行过长，中文：{item["length"]},请处理', index=item['index'])
        report_path = os.path.join(output_dir, TAIWAN_REPORT_NAME)
        if use_taiwan and (taiwan_changes or taiwan_error):
            write_text_with_fallback(
                report_path,
                build_taiwan_compare_html(title, filename, taiwan_changes, taiwan_error),
            )
            if taiwan_error:
                sub.add_notice('繁化姬台湾化失败,请检查')
        elif os.path.exists(report_path):
            try:
                os.remove(report_path)
            except OSError:
                pass

    # HDR 时额外另存一份未做 HDR 颜色映射的 SDR 版本
    sdr_content = None
    sdr_name = ''
    if is_HDR:
        if sub.source_is_chinese_only:
            sdr_content = list(contents[OUT_CHS])
            sdr_name = '2-简体中文-SDR-zh.ass'
        else:
            sdr_content = list(contents[OUT_BILINGUAL])
            sdr_name = '2-简英双语-SDR-zh.ass'

    # HDR 时把行内颜色标签按 ssaHdrify 的映射一起转换
    if is_HDR:
        for key in contents:
            contents[key] = [
                hdrify_event_colours(line, sub.hdr_brightness) if line.startswith('Dialogue:') else line
                for line in contents[key]
            ]

    for key, value in sub.contents.items():
        if sub.source_is_chinese_only and value in (OUT_BILINGUAL, OUT_ENG):
            continue
        file = os.path.join(output_dir, f'{key}.ass')
        with open(file, 'w', encoding='utf-8-sig') as f:
            f.writelines(contents[f'{value}'])

    if sdr_content is not None:
        file = os.path.join(output_dir, sdr_name)
        with open(file, 'w', encoding='utf-8-sig') as f:
            f.writelines(build_sdr_bilingual_lines(sub, sdr_content))

    sub.check_timeline_overlaps()
    sub.notices.sort(key=lambda notice: int(notice.split(',', 1)[0]))

    html_file = write_text_with_fallback(
        os.path.join(output_dir, NOTICES_REPORT_NAME),
        build_notices_html(filename, title, sub.notices, source_label),
    )

    notices_data = []
    for notice in sub.notices:
        parts = notice.strip().split(',', 2)
        if len(parts) != 3:
            continue
        try:
            index = int(parts[0])
        except ValueError:
            continue
        notices_data.append({'index': index, 'problem': parts[1], 'need': parts[2]})
    try:
        with open(os.path.join(output_dir, NOTICES_DATA_NAME), 'w', encoding='utf-8') as handle:
            json.dump({
                'version': 1,
                'source': os.path.abspath(filename),
                'source_label': source_label,
                'output_dir': os.path.abspath(output_dir),
                'title': title,
                'is_hdr': bool(is_HDR),
                'is_mid_black': bool(is_mid_black),
                'meta': {
                    'title': title,
                    'script_updated_by': updated_by,
                    'original_script': meta.get('original_script', ''),
                    'original_translation': meta.get('original_translation', ''),
                    'original_timing': meta.get('original_timing', ''),
                    'original_editing': meta.get('original_editing', ''),
                    'taiwan': bool(meta.get('taiwan', True)),
                    'hdr_brightness': sub.hdr_brightness,
                    'source_label': source_label,
                },
                'notices': notices_data,
            }, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return html_file, output_dir, sub.source_is_chinese_only

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')
BLACK_THRESHOLD = 15
BLACK_SAMPLE_COLUMNS = 960


def get_black_bar_type(scaled_bottom: float) -> str:
    if scaled_bottom <= 0:
        return '无黑边'
    if scaled_bottom <= 50:
        return '小黑边'
    if scaled_bottom <= 108:
        return '中黑边'
    if scaled_bottom < 150:
        return '大黑边'
    return '超大黑边'


def detect_black_bars(image_path: str, progress_callback=None) -> dict:
    """逐列扫描图片上下黑边，返回原始像素和 1080p 等效值。"""
    if Image is None:
        raise RuntimeError('黑边检测需要 Pillow')
    with Image.open(image_path) as source:
        width, height = source.size
        if not width or not height:
            raise ValueError('图片尺寸无效')
        red, green, blue = source.convert('RGB').split()
        # 取三分量最大值，等价于原来的 max(pixel)，但由 C 层完成
        bright = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        data = bright.tobytes()

    scale_factor = height / 1080.0
    step = max(1, width // BLACK_SAMPLE_COLUMNS)
    columns = list(range(0, width, step))
    total = len(columns)

    # 用字节表把“亮于阈值”标成 1，再用 find/rfind 定位上下边缘
    mask = bytes(1 if value > BLACK_THRESHOLD else 0 for value in range(256))
    masked = data.translate(mask)
    last_row_offset = (height - 1) * width

    top_edges = []
    bottom_edges = []
    for index, x in enumerate(columns):
        if masked[x]:
            top = 0
        else:
            top = masked[x::width].find(b'\x01')
            if top < 0:
                top = height
        top_edges.append(top)

        if masked[last_row_offset + x]:
            bottom_edges.append(height - 1)
        else:
            bottom = masked[x::width].rfind(b'\x01')
            bottom_edges.append(0 if bottom < 0 else bottom)

        if progress_callback and (index % 32 == 0 or index == total - 1):
            progress_callback(index + 1, total)

    top_bar = Counter(top_edges).most_common(1)[0][0]
    common_bottom = Counter(bottom_edges).most_common(1)[0][0]
    bottom_bar = height - 1 - common_bottom

    # 全黑图片
    if top_bar == height and common_bottom == 0:
        top_bar = 0
        bottom_bar = 0

    scaled_bottom = bottom_bar / scale_factor if scale_factor else bottom_bar
    return {
        'width': width,
        'height': height,
        'top': top_bar,
        'bottom': bottom_bar,
        'scale': scale_factor,
        'scaled_bottom': scaled_bottom,
        'type': get_black_bar_type(scaled_bottom),
    }


class BlackBarDetectorWindow:
    def __init__(self, master, on_mid_black=None):
        self.master = master
        self.on_mid_black = on_mid_black
        self.window = tk.Toplevel(master)
        self.window.title("CMCT 黑边检测")
        self.window.geometry("640x700")
        self.window.minsize(540, 560)
        try:
            self.window.iconbitmap(default=resource_path('ohMyAss Noto.ico'))
        except tk.TclError:
            pass
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.results = []
        self.build_ui()
        center_window(self.window, master)

    def build_ui(self):
        self.window.configure(bg=UI_BG)
        content = tk.Frame(self.window, bg=UI_BG, padx=18, pady=16)
        content.pack(fill='both', expand=True)

        intro = (
            "通过原盘截图检测上下黑边大小\n"
            "画面边缘尽量明亮，建议使用多张截图交叉验证\n"
            "2160p 会自动换算为 1080p 等效像素\n"
            "检测完成后会自动联动主界面的“中黑边”选项"
        )
        tk.Label(
            content, text=intro, bg=UI_BG, fg=UI_MUTED,
            font=(UI_FONT, UI_SMALL_SIZE), justify='center',
        ).pack(pady=(2, 12))

        drop_text = "将图片拖到这里\n或点击“选择图片”按钮"
        if not DND_AVAILABLE:
            drop_text = "拖拽功能需要安装 tkinterdnd2\n可点击此处选择图片"
        self.drop_area = tk.Label(
            content,
            text=drop_text,
            relief='flat',
            bd=0,
            height=4,
            justify='center',
            bg='#fafafa',
            fg=UI_MUTED,
            font=(UI_FONT, UI_BODY_SIZE),
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=UI_BORDER,
        )
        self.drop_area.pack(fill='x', pady=(0, 12))
        self.drop_area.bind('<Button-1>', lambda event: self.choose_images())
        if DND_AVAILABLE:
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind('<<Drop>>', self.on_drop)

        button_frame = tk.Frame(content, bg=UI_BG)
        button_frame.pack(pady=(0, 8))
        self.btn_select = ttk.Button(button_frame, text="选择图片", command=self.choose_images, style='Secondary.TButton')
        self.btn_select.pack(side='left', padx=6)
        self.btn_clear = ttk.Button(button_frame, text="清空结果", command=self.clear_results, style='Secondary.TButton')
        self.btn_clear.pack(side='left', padx=6)

        self.status_var = tk.StringVar(value="等待图片...")
        ttk.Label(content, textvariable=self.status_var, style='Status.TLabel').pack(pady=(2, 6))

        self.progress = ttk.Progressbar(content, orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', pady=(0, 8))

        result_frame = tk.Frame(content, bg=UI_CARD, highlightthickness=1,
                                highlightbackground=UI_BORDER, highlightcolor=UI_BORDER)
        result_frame.pack(fill='both', expand=True)
        scrollbar = tk.Scrollbar(result_frame)
        scrollbar.pack(side='right', fill='y')
        self.result_text = tk.Text(
            result_frame,
            height=12,
            wrap='word',
            yscrollcommand=scrollbar.set,
            state='disabled',
            font=(UI_FONT, UI_SMALL_SIZE),
            bg=UI_CARD,
            fg=UI_TEXT,
            relief='flat',
            padx=10,
            pady=10,
            highlightthickness=0,
            bd=0,
            insertbackground=UI_TEXT,
        )
        self.result_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.result_text.yview)

    def on_drop(self, event):
        paths = self.window.tk.splitlist(event.data)
        images = [path for path in paths if path.lower().endswith(IMAGE_EXTENSIONS)]
        if not images:
            messagebox.showinfo(
                "提示",
                "请拖入图片文件（jpg/png/bmp/tif/webp）",
                parent=self.window,
            )
            return
        self.analyse_images(images)

    def choose_images(self):
        paths = filedialog.askopenfilenames(
            title="选择电影截图",
            parent=self.window,
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.analyse_images(list(paths))

    def clear_results(self):
        self.results = []
        self.result_text.config(state='normal')
        self.result_text.delete('1.0', 'end')
        self.result_text.config(state='disabled')
        self.status_var.set("等待图片...")
        self.progress['value'] = 0

    def append_result(self, text):
        self.result_text.config(state='normal')
        self.result_text.insert('end', text + '\n')
        self.result_text.see('end')
        self.result_text.config(state='disabled')

    def analyse_images(self, paths):
        if Image is None:
            messagebox.showerror(
                "缺少依赖",
                "黑边检测需要 Pillow，请先运行：pip install pillow",
                parent=self.window,
            )
            return
        if not paths:
            return

        self.btn_select.config(state='disabled')
        self.btn_clear.config(state='disabled')
        self.results = []
        self.result_text.config(state='normal')
        self.result_text.delete('1.0', 'end')
        self.result_text.config(state='disabled')

        total = len(paths)
        for index, path in enumerate(paths, 1):
            filename = os.path.basename(path)
            self.status_var.set(f"正在检测 {index}/{total}: {filename}")
            self.progress['maximum'] = 100
            self.progress['value'] = 0
            self.window.update_idletasks()

            def progress_callback(current, maximum):
                self.progress['maximum'] = maximum
                self.progress['value'] = current
                self.window.update_idletasks()

            try:
                result = detect_black_bars(path, progress_callback)
            except Exception as exc:
                self.append_result(f"【{filename}】\n检测失败：{exc}\n")
                continue

            self.results.append(result)
            mid_hint = '勾选' if result['type'] == '中黑边' else '不勾选'
            self.append_result(
                f"【{filename}】\n"
                f"分辨率：{result['width']}×{result['height']}\n"
                f"上黑边：{result['top']} px\n"
                f"下黑边：{result['bottom']} px\n"
                f"总黑边：{result['top'] + result['bottom']} px\n"
                f"1080p 等效下黑边：{result['scaled_bottom']:.1f} px\n"
                f"黑边类型：{result['type']}\n"
                f"中黑边勾选参考：{mid_hint}\n"
            )

        if len(self.results) > 1:
            self.append_summary()
        elif len(self.results) == 1:
            self.status_var.set(f"检测完成：{os.path.basename(paths[0])}")
        else:
            self.status_var.set("未成功检测到图片")

        self.sync_mid_black_option()
        self.progress['value'] = 0
        self.btn_select.config(state='normal')
        self.btn_clear.config(state='normal')

    def sync_mid_black_option(self):
        if not self.results:
            return
        if len(self.results) > 1:
            common_type = Counter(item['type'] for item in self.results).most_common(1)[0][0]
        else:
            common_type = self.results[0]['type']
        checked = common_type == '中黑边'
        if self.on_mid_black:
            self.on_mid_black(checked)
        self.append_result(f"已联动主界面中黑边选项：{'勾选' if checked else '不勾选'}\n")

    def append_summary(self):
        tops = [item['top'] for item in self.results]
        bottoms = [item['bottom'] for item in self.results]
        scaled = [item['scaled_bottom'] for item in self.results]
        types = Counter(item['type'] for item in self.results)
        common_type = types.most_common(1)[0][0]
        mid_hint = '勾选' if common_type == '中黑边' else '不勾选'
        self.append_result(
            "【综合结果】\n"
            f"检测图片：{len(self.results)} 张\n"
            f"上黑边中位数：{statistics.median(tops):.1f} px\n"
            f"下黑边中位数：{statistics.median(bottoms):.1f} px\n"
            f"1080p 等效下黑边中位数：{statistics.median(scaled):.1f} px\n"
            f"最多类型：{common_type}\n"
            f"中黑边勾选参考：{mid_hint}\n"
        )
        self.status_var.set(f"检测完成：共 {len(self.results)} 张图片")

    def close(self):
        self.window.destroy()


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


# ===================== BDN XML / SUP 生成（外部工具，在线更新） =====================

BDN_TOOL_ROOT = os.path.join(
    os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
    'ohMyAssNoto', 'tools',
)
SEVEN_ZIP_URL = 'https://www.7-zip.org/a/7zr.exe'
GITHUB_RELEASES_API = 'https://api.github.com/repos/{repo}/releases?per_page=20'
TOOLS_USER_AGENT = 'ohMyAssNoto/1.0'
BDN_TOOL_SPECS = {
    'ass2bdnxml': {
        'label': 'ass2bdnxml',
        'repo': 'cubicibo/ass2bdnxml',
        'exe': 'ass2bdnxml.exe',
        'asset_keywords': ('winx86_64', 'win_x64', 'win64', 'win', 'ass2bdnxml'),
        'required_keywords': (),
        'probe_args': [],
        'probe_expect': ('usage', 'ass2bdnxml'),
    },
    'super': {
        'label': 'SUPer',
        'repo': 'cubicibo/SUPer',
        'exe': 'SUPer_CLI.exe',
        'asset_keywords': ('win_x64', 'win64', 'win'),
        'required_keywords': ('cli',),
        'probe_args': ['-v'],
        'probe_expect': ('cubicibo', 'v0.', 'super'),
    },
}
BDN_FORMATS = ('1080p', '1080i', '720p', '576i', '480i')
BDN_FPS = ('23.976', '24', '25', '29.97', '50', '59.94')
BDN_QUANTIZERS = (
    ('libimagequant（质量最好）', '3'),
    ('Qtzr（质量高，体积大）', '0'),
    ('HexTree（均衡）', '2'),
    ('Pillow（最快）', '1'),
)


def _no_window_flag():
    return getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0


def bdn_tool_dir(name: str) -> str:
    return os.path.join(BDN_TOOL_ROOT, name)


def load_bdn_tool_state(name: str) -> dict:
    try:
        with open(os.path.join(bdn_tool_dir(name), 'state.json'), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_bdn_tool_state(name: str, data: dict):
    folder = bdn_tool_dir(name)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, 'state.json'), 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def bdn_tool_exe(name: str) -> str:
    state = load_bdn_tool_state(name)
    relative = state.get('exe') or BDN_TOOL_SPECS[name]['exe']
    return os.path.join(bdn_tool_dir(name), 'app', relative)


def bdn_tool_version_text() -> str:
    parts = []
    for name in ('ass2bdnxml', 'super'):
        state = load_bdn_tool_state(name)
        parts.append(f'{BDN_TOOL_SPECS[name]["label"]} {state.get("tag") or "未安装"}')
    return ' · '.join(parts)


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


def _broadcast_font_change():
    """通知其他窗口字体已变化（带超时，避免被无响应窗口卡住）。"""
    try:
        send_timeout = ctypes.windll.user32.SendMessageTimeoutW
        send_timeout.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t,
            ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_size_t),
        ]
        send_timeout.restype = ctypes.c_size_t
        result = ctypes.c_size_t()
        send_timeout(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, ctypes.byref(result))
    except Exception:
        pass


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
    except Exception:
        pass
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
                    downloaded = True
                    break
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


def _tools_request(url: str, timeout: int = 60):
    request = urllib.request.Request(url, headers={'User-Agent': TOOLS_USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def download_file(url: str, dest: str, log=None, timeout: int = 120):
    with _tools_request(url, timeout=timeout) as response, open(dest, 'wb') as out:
        total = int(response.headers.get('Content-Length') or 0)
        done = 0
        shown = -1
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if log and total:
                percent = int(done * 100 / total)
                if percent != shown and percent % 10 == 0:
                    shown = percent
                    log(f'下载中 {percent}%')
    return dest


def ensure_seven_zip(log=None) -> str:
    path = os.path.join(BDN_TOOL_ROOT, '7zr.exe')
    if os.path.isfile(path) and os.path.getsize(path) > 100000:
        return path
    os.makedirs(BDN_TOOL_ROOT, exist_ok=True)
    if log:
        log('首次使用，正在下载 7zr 解压组件…')
    download_file(SEVEN_ZIP_URL, path, log=log)
    if not os.path.isfile(path):
        raise RuntimeError('7zr 下载失败')
    return path


def fetch_tool_releases(repo: str):
    url = GITHUB_RELEASES_API.format(repo=repo)
    with _tools_request(url) as response:
        data = json.loads(response.read().decode('utf-8'))
    if isinstance(data, dict):
        raise RuntimeError(data.get('message') or f'GitHub 接口返回异常（{repo}）')
    if not isinstance(data, list):
        raise RuntimeError(f'GitHub 接口返回异常（{repo}）')
    return data


def _release_cache_path() -> str:
    return os.path.join(BDN_TOOL_ROOT, 'releases_cache.json')


def _load_release_cache(repo: str):
    try:
        with open(_release_cache_path(), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        items = data.get(repo)
        if not isinstance(items, list):
            return []
        candidates = []
        for tag, name, url in items:
            if tag and name and url:
                candidates.append((tag, {'name': name, 'browser_download_url': url, 'size': 0}))
        return candidates
    except Exception:
        return []


def _save_release_cache(repo: str, candidates: list):
    try:
        path = _release_cache_path()
        data = {}
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        data[repo] = [
            [tag, asset.get('name', ''), asset.get('browser_download_url', '')]
            for tag, asset in candidates
        ]
        os.makedirs(BDN_TOOL_ROOT, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _match_asset(name: str, spec: dict) -> bool:
    lower = name.lower()
    if not lower.endswith('.7z'):
        return False
    if not any(keyword in lower for keyword in spec['asset_keywords']):
        return False
    if spec['required_keywords'] and not all(
            keyword in lower for keyword in spec['required_keywords']):
        return False
    return True


def _html_latest_tag(repo: str) -> str:
    """通过 releases/latest 跳转拿到最新版本号（一次请求，不走 API）。"""
    response = _tools_request(f'https://github.com/{repo}/releases/latest', timeout=60)
    final_url = response.geturl()
    match = re.search(r'/releases/tag/([^/?#]+)', final_url)
    if not match:
        raise RuntimeError('无法获取最新版本号')
    return urllib.parse.unquote(match.group(1))


def _html_release_tags(repo: str, limit: int = 8):
    """解析 GitHub Releases 页面上的版本号，不消耗 API 配额。"""
    page = _tools_request(f'https://github.com/{repo}/releases', timeout=60).read()
    tags = []
    for tag in re.findall(r'/releases/tag/([^"\'#?<>\s]+)', page.decode('utf-8', 'replace')):
        tag = urllib.parse.unquote(tag)
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:limit]


def _html_tag_candidates(repo: str, tag: str, spec: dict):
    """解析某个版本的资产列表。"""
    page = _tools_request(
        f'https://github.com/{repo}/releases/expanded_assets/{urllib.parse.quote(tag)}',
        timeout=60,
    ).read().decode('utf-8', 'replace')
    candidates = []
    seen = set()
    for href in re.findall(r'href="(/[^"]+/releases/download/[^"]+)"', page):
        url = 'https://github.com' + href
        name = urllib.parse.unquote(url.rsplit('/', 1)[-1])
        if url in seen or not _match_asset(name, spec):
            continue
        seen.add(url)
        candidates.append((tag, {
            'name': name,
            'browser_download_url': url,
            'size': 0,
        }))
    return candidates


def _fallback_candidates(repo: str, spec: dict, log=None):
    """发布页解析失败时，退回 GitHub API，再退回本地缓存。"""
    errors = []
    try:
        releases = fetch_tool_releases(repo)
        candidates = []
        seen = set()
        for tag, asset in _tool_asset_candidates(releases, spec):
            url = asset.get('browser_download_url', '')
            if url in seen:
                continue
            seen.add(url)
            candidates.append((tag, asset))
        if candidates:
            _save_release_cache(repo, candidates)
            return candidates
        errors.append('GitHub 接口没有可用的安装包')
    except Exception as exc:
        errors.append(f'GitHub 接口失败：{exc}')

    cached = _load_release_cache(repo)
    if cached:
        if log:
            log('在线获取失败，改用上次缓存的版本信息')
        return cached
    raise RuntimeError('；'.join(errors))


def _tool_asset_candidates(releases: list, spec: dict):
    seen = set()
    for release in releases:
        tag = release.get('tag_name') or ''
        for asset in release.get('assets') or []:
            name = asset.get('name') or ''
            if not _match_asset(name, spec):
                continue
            url = asset.get('browser_download_url')
            if not url or url in seen:
                continue
            seen.add(url)
            yield tag, asset


def _extract_archive(seven_zip: str, archive: str, dest: str):
    os.makedirs(dest, exist_ok=True)
    result = subprocess.run(
        [seven_zip, 'x', archive, f'-o{dest}', '-y'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=900, creationflags=_no_window_flag(),
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or '解压失败').strip().splitlines()
        raise RuntimeError(message[-1] if message else '解压失败')


def _find_file(root: str, filename: str) -> str:
    for base, _dirs, files in os.walk(root):
        if filename in files:
            return os.path.join(base, filename)
    return ''


def _probe_tool(exe_path: str, args, expect) -> bool:
    try:
        result = subprocess.run(
            [exe_path] + list(args),
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=120, cwd=os.path.dirname(exe_path),
            creationflags=_no_window_flag(),
        )
    except Exception:
        return False
    text = ((result.stdout or '') + (result.stderr or '')).lower()
    return any(word in text for word in expect)


def install_bdn_tool(name: str, log=None, force: bool = False):
    """从 GitHub Releases 下载并安装工具；失败返回 (False, 原因)。"""
    spec = BDN_TOOL_SPECS[name]
    state = load_bdn_tool_state(name)
    installed = bool(state.get('exe')) and os.path.isfile(bdn_tool_exe(name))
    if installed and not force:
        return True, state.get('tag', '')

    tags = []
    html_error = ''
    try:
        latest_tag = _html_latest_tag(spec['repo'])
    except Exception as exc:
        latest_tag = ''
        html_error = str(exc)

    fallback = []
    if not latest_tag:
        fallback = _fallback_candidates(spec['repo'], spec, log)
        latest_tag = fallback[0][0] if fallback else ''

    # 已安装且上次检查过同一个最新版本时，不再重复下载
    if installed and state.get('checked') == latest_tag and latest_tag:
        if log:
            if state.get('tag') == latest_tag:
                log(f'{spec["label"]} {latest_tag} 已是最新版本')
            else:
                log(f'{spec["label"]} 当前 {state.get("tag", "")}，已检查过最新版本 {latest_tag}')
        return True, state.get('tag', '')

    def candidate_stream():
        if latest_tag and not fallback:
            for candidate in _html_tag_candidates(spec['repo'], latest_tag, spec):
                yield candidate
            try:
                other_tags = _html_release_tags(spec['repo'])
            except Exception:
                return
            for tag in other_tags:
                if tag == latest_tag:
                    continue
                try:
                    for candidate in _html_tag_candidates(spec['repo'], tag, spec):
                        yield candidate
                except Exception:
                    continue
        else:
            for pair in fallback:
                yield pair

    seven = ensure_seven_zip(log)
    errors = []
    if html_error and not tags:
        errors.append(f'发布页解析失败：{html_error}')
    for tag, asset in candidate_stream():
        work = tempfile.mkdtemp(prefix=f'ohmyass_{name}_')
        try:
            size = int(asset.get('size') or 0) // 1048576
            if log:
                suffix = f'（{size} MB）' if size else ''
                log(f'下载 {spec["label"]} {tag}{suffix}…')
            archive = os.path.join(work, 'tool.7z')
            download_file(asset['browser_download_url'], archive)
            extract_dir = os.path.join(work, 'extract')
            _extract_archive(seven, archive, extract_dir)
            exe_path = _find_file(extract_dir, spec['exe'])
            if not exe_path:
                errors.append(f'{tag}：压缩包内没有 {spec["exe"]}')
                continue
            if not _probe_tool(exe_path, spec['probe_args'], spec['probe_expect']):
                errors.append(f'{tag}：程序无法启动（上游包可能缺少依赖）')
                continue
            target = os.path.join(bdn_tool_dir(name), 'app')
            shutil.rmtree(target, ignore_errors=True)
            os.makedirs(target, exist_ok=True)
            payload = os.path.dirname(exe_path)
            for item in os.listdir(payload):
                shutil.move(os.path.join(payload, item), os.path.join(target, item))
            save_bdn_tool_state(name, {
                'tag': tag,
                'checked': latest_tag or tag,
                'asset': asset.get('name', ''),
                'exe': os.path.relpath(exe_path, payload).replace('\\', '/'),
                'url': asset.get('browser_download_url', ''),
                'installed': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            if log:
                log(f'{spec["label"]} {tag} 安装完成')
            return True, tag
        except Exception as exc:
            errors.append(f'{tag}：{exc}')
        finally:
            shutil.rmtree(work, ignore_errors=True)
    detail = '；'.join(errors[-4:]) if errors else '没有找到可用的发布包'
    return False, detail


def install_all_bdn_tools(log=None, force: bool = False):
    for name in ('ass2bdnxml', 'super'):
        ok, info = install_bdn_tool(name, log, force=force)
        if not ok:
            return False, f'{BDN_TOOL_SPECS[name]["label"]} 安装失败：{info}'
    return True, ''


def ensure_bdn_tools(log=None):
    missing = [
        name for name in ('ass2bdnxml', 'super')
        if not os.path.isfile(bdn_tool_exe(name))
    ]
    if not missing:
        return True, ''
    if log:
        log('首次使用需要下载 ass2bdnxml 与 SUPer（约 90 MB）…')
    return install_all_bdn_tools(log)


def _normalize_bdn_xml(path: str):
    """ass2bdnxml 在中文系统上会用 GBK 写 XML，这里统一转成 UTF-8。"""
    try:
        with open(path, 'rb') as handle:
            data = handle.read()
    except OSError:
        return
    try:
        data.decode('utf-8')
        return
    except UnicodeDecodeError:
        pass
    for encoding in ('gb18030', 'big5', 'cp1252'):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            with open(path, 'w', encoding='utf-8-sig', newline='') as handle:
                handle.write(text)
        except OSError:
            pass
        return


def build_super_args(params: dict, sup_path: str, make_pes: bool = False):
    """按高级参数拼出 SUPer 命令行。"""
    params = {**BDN_PARAM_DEFAULTS, **(params or {})}
    args = [
        bdn_tool_exe('super'), '-i', 'bdn.xml',
        '-q', str(params.get('quantizer', '3')),
        '-c', str(params.get('compression', '80')),
        '-a', str(params.get('acqrate', '100')),
        '-b', str(params.get('color', 'bt709')).replace('bt', ''),
        '-e', str(params.get('extra_acq', '2')),
        '--ssim-tol', str(params.get('ssim_tol', '0')),
        '-y', sup_path,
    ]
    threads = str(params.get('threads', 'auto'))
    if threads and threads.lower() != 'auto':
        args += ['-t', threads]
    if params.get('allow_normal'):
        args.append('-n')
    if params.get('prefer_normal'):
        args.append('-k')
    if params.get('buffer'):
        args.append('-d')
    if params.get('full_palette'):
        args.append('-p')
    try:
        redraw = float(params.get('redraw_period') or 0)
    except ValueError:
        redraw = 0.0
    if redraw > 0:
        args += ['--redraw-period', f'{redraw:g}']
    max_kbps = str(params.get('max_kbps') or '').strip()
    if max_kbps and max_kbps != '0':
        args += ['-m', max_kbps]
    log_level = str(params.get('log_level') or 'off')
    if log_level != 'off':
        args += ['-l', log_level]
    if make_pes:
        args.append('-w')
    return args


VS_BUNDLE_FILES = ('avs2bdnxml.exe', 'VSFilterMod.dll', 'AviSynth.dll', 'DevIL.dll')
VS_RENDER_FPS = ('23.976', '24', '25', '29.97', '50', '59.94')
VS_VIDEO_SIZE = {
    '1080p': (1920, 1080), '1080i': (1920, 1080),
    '720p': (1280, 720), '576i': (720, 576), '480i': (720, 480),
}
VS_FPS_EXPR = {
    '23.976': '24000.0/1001.0',
    '29.97': '30000.0/1001.0',
    '59.94': '60000.0/1001.0',
}


def _vsfilter_source(name: str) -> str:
    """在打包资源根目录或源码目录的 bin 子目录里查找渲染组件。"""
    for candidate in (resource_path(name), resource_path(os.path.join('bin', name))):
        if os.path.isfile(candidate):
            return candidate
    return ''


def vsfilter_render_dir():
    """把随包附带的 VSFilterMod 渲染组件释放到工具目录，返回目录（不可用则空串）。"""
    target = os.path.join(BDN_TOOL_ROOT, 'vsfilter')
    for name in VS_BUNDLE_FILES:
        src = _vsfilter_source(name)
        dst = os.path.join(target, name)
        try:
            if not src:
                continue
            if os.path.isfile(dst) and os.path.getsize(dst) == os.path.getsize(src):
                continue
            os.makedirs(target, exist_ok=True)
            shutil.copy2(src, dst)
        except OSError:
            pass
    required = ('avs2bdnxml.exe', 'VSFilterMod.dll', 'AviSynth.dll')
    if all(os.path.isfile(os.path.join(target, name)) for name in required):
        return target
    return ''


def vsfilter_available() -> bool:
    return bool(vsfilter_render_dir())


def read_ass_text(path: str) -> str:
    """按 BOM / UTF-8 / GBK 依次读取 ASS 文本。"""
    try:
        with open(path, 'rb') as handle:
            data = handle.read()
    except OSError:
        return ''
    if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        try:
            return data.decode('utf-16')
        except UnicodeDecodeError:
            pass
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('cp1252', errors='replace')


def _ass_last_time_ms(ass_path: str) -> int:
    """取 ASS 里最后一条对白的结束时间（毫秒）。"""
    last = 0
    text = read_ass_text(ass_path)
    for line in text.splitlines():
        if not line.startswith('Dialogue:'):
            continue
        parts = line.split(',')
        if len(parts) < 3:
            continue
        end = parse_ass_time(parts[2])
        if end and end > last:
            last = end
    return last


def _ass_intervals_ms(ass_path: str):
    """读取 ASS 对白的起止时间（毫秒）。"""
    intervals = []
    for line in read_ass_text(ass_path).splitlines():
        if not line.startswith('Dialogue:'):
            continue
        parts = line.split(',')
        if len(parts) < 3:
            continue
        start = parse_ass_time(parts[1])
        end = parse_ass_time(parts[2])
        if start is not None and end is not None and end > start:
            intervals.append((start, end))
    return intervals


def _merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _vsfilter_segments(intervals, fps_value, first_frame, last_frame, parts, min_frames):
    """按对白空档把 [first_frame, last_frame) 切成若干段，避免切断事件。"""
    total = last_frame - first_frame
    if parts <= 1 or total < min_frames * 2:
        return [(first_frame, total)]
    merged = _merge_intervals(intervals)
    gaps = [(merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)]
    gaps = [(start, end) for start, end in gaps if end - start >= 120]
    if not gaps:
        return [(first_frame, total)]
    span_ms = total / fps_value * 1000.0
    base_ms = first_frame / fps_value * 1000.0
    targets = [base_ms + span_ms * i / parts for i in range(1, parts)]
    cuts = []
    for target in targets:
        best = None
        for gap_start, gap_end in gaps:
            mid = (gap_start + gap_end) / 2.0
            if mid <= 0:
                continue
            distance = abs(mid - target)
            if best is None or distance < best[0]:
                best = (distance, mid)
        if best is None:
            continue
        frame = int(round(best[1] / 1000.0 * fps_value))
        if frame - first_frame < min_frames or last_frame - frame < min_frames:
            continue
        if any(abs(frame - cut) < min_frames for cut in cuts):
            continue
        cuts.append(frame)
    cuts = sorted(set(cuts))
    points = [first_frame] + cuts + [last_frame]
    return [(points[i], points[i + 1] - points[i]) for i in range(len(points) - 1)]


def _merge_bdn_parts(xml_paths, out_path):
    """合并多段 avs2bdnxml 输出（PNG 名按绝对帧号，天然不冲突）。"""
    blocks = []
    head = {}
    for path in xml_paths:
        try:
            with open(path, 'rb') as handle:
                data = handle.read()
        except OSError:
            return False
        if not head:
            for key, pattern in (
                ('name', rb'<Name\b[^>]*?/>'),
                ('language', rb'<Language\b[^>]*?/>'),
                ('format', rb'<Format\b[^>]*?/>'),
            ):
                match = re.search(pattern, data, re.S)
                if match:
                    head[key] = match.group(0)
        blocks.extend(re.findall(rb'<Event\b.*?</Event>', data, re.S))
    if not blocks:
        return False
    first = re.search(rb'InTC="([^"]+)"', blocks[0])
    last = re.search(rb'OutTC="([^"]+)"', blocks[-1])
    first_tc = first.group(1).decode('ascii') if first else '00:00:00:00'
    last_tc = last.group(1).decode('ascii') if last else first_tc
    header = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<BDN Version="0.93" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        b'xsi:noNamespaceSchemaLocation="BD-03-006-0093b BDN File Format.xsd">\n'
        b'<Description>\n'
        + head.get('name', b'<Name Title="Undefined" Content=""/>') + b'\n'
        + head.get('language', b'<Language Code="und"/>') + b'\n'
        + head.get('format', b'<Format VideoFormat="1080p" FrameRate="23.976" DropFrame="false"/>') + b'\n'
        + (
            f'<Events LastEventOutTC="{last_tc}" FirstEventInTC="{first_tc}"\n'
            f'ContentInTC="{first_tc}" ContentOutTC="{last_tc}" '
            f'NumberofEvents="{len(blocks)}" Type="Graphic"/>\n'
        ).encode('ascii')
        + b'</Description>\n<Events>\n'
    )
    payload = header + b'\n'.join(blocks) + b'\n</Events>\n</BDN>\n'
    with open(out_path, 'wb') as handle:
        handle.write(payload)
    return True


def render_bdn_with_vsfilter(ass_path: str, out_dir: str, fmt: str, fps: str,
                             language: str, track_name: str,
                             log=None, progress=None):
    """用 avs2bdnxml + VSFilterMod 渲染 BDN XML + PNG（支持 \\fsvp 等 Mod 标签）。"""
    def report(value):
        if progress:
            progress(value)

    runtime = vsfilter_render_dir()
    if not runtime:
        return False, '未找到 VSFilterMod 渲染组件（avs2bdnxml / VSFilterMod.dll）'
    width, height = VS_VIDEO_SIZE.get(fmt, (1920, 1080))
    try:
        fps_value = float(fps)
    except ValueError:
        return False, '帧率无效：' + str(fps)

    end_ms = _ass_last_time_ms(ass_path)
    if end_ms <= 0:
        return False, '字幕里没有可渲染的对白'
    frames = int(math.ceil(end_ms / 1000.0 * fps_value)) + 2
    frames = max(1, min(frames, 500000))

    intervals = _ass_intervals_ms(ass_path)
    first_ms = min((start for start, _ in intervals), default=0)
    first_frame = max(0, int((first_ms - 1000) / 1000.0 * fps_value))

    cpu = os.cpu_count() or 4
    duration_s = (frames - first_frame) / fps_value
    parts = 1
    if duration_s >= 120 and cpu >= 4:
        parts = min(4, max(2, cpu // 2), max(1, int(duration_s // 45)))
    segments = _vsfilter_segments(
        intervals, fps_value, first_frame, frames, parts,
        min_frames=int(30 * fps_value),
    )

    work = os.path.join(runtime, 'work')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    try:
        try:
            text = read_ass_text(ass_path)
            if not text:
                raise OSError('文件为空或无法读取')
            with open(os.path.join(work, 'sub.ass'), 'w', encoding='utf-16', newline='') as handle:
                handle.write(text)
        except OSError as exc:
            return False, '读取 ASS 失败：' + str(exc)

        fps_expr = VS_FPS_EXPR.get(str(fps), str(fps))
        script = (
            'LoadPlugin("..\\VSFilterMod.dll")\n'
            f'MaskSubMod("sub.ass", {width}, {height}, {fps_expr}, {frames})\n'
        )
        try:
            payload = script.encode('mbcs')
        except (UnicodeEncodeError, LookupError):
            payload = script.encode('utf-8')
        try:
            with open(os.path.join(work, 'sub.avs'), 'wb') as handle:
                handle.write(payload)
        except OSError as exc:
            return False, '写入渲染脚本失败：' + str(exc)

        exe = os.path.join(runtime, 'avs2bdnxml.exe')
        base_args = [
            exe, '-o', 'bdn.xml',
            '-v', fmt, '-f', str(fps), '-l', language or 'und',
            '-t', (track_name.strip() or 'Undefined'),
            '-a', '1', '-p', '0', '-e', '0',
        ]

        def segment_args(index, start, count, single=False):
            args = base_args[:]
            if not single:
                args[2] = f'bdn_{index}.xml'
            args += ['-j', str(start), '-c', str(count), 'sub.avs']
            return args

        def run_args(args):
            try:
                return subprocess.run(
                    args, cwd=work, capture_output=True, text=True, encoding='utf-8',
                    errors='replace', timeout=10800, creationflags=_no_window_flag(),
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return exc

        def clean_work():
            for name in os.listdir(work):
                if name.endswith('.png') or name.endswith('.xml'):
                    try:
                        os.remove(os.path.join(work, name))
                    except OSError:
                        pass

        def render_single():
            if log:
                log('正在用 VSFilterMod 渲染字幕帧…')
            report(20)
            result = run_args(segment_args(0, first_frame, frames - first_frame, single=True))
            if isinstance(result, Exception):
                return False, 'VSFilterMod 渲染失败：' + str(result)
            if result.returncode != 0 or not os.path.isfile(os.path.join(work, 'bdn.xml')):
                tail = (result.stderr or result.stdout or '').strip().splitlines()[-4:]
                return False, 'VSFilterMod 渲染失败：' + (' / '.join(tail) or '未知错误')
            return True, ''

        rendered = False
        if len(segments) > 1:
            if log:
                log(f'正在用 VSFilterMod 并行渲染字幕帧（{len(segments)} 段）…')
            report(20)
            lock = threading.Lock()
            errors = []
            done = 0

            def worker(index, start, count):
                nonlocal done
                result = run_args(segment_args(index, start, count))
                with lock:
                    if isinstance(result, Exception):
                        errors.append(str(result))
                    elif result.returncode != 0 or not os.path.isfile(
                            os.path.join(work, f'bdn_{index}.xml')):
                        tail = (result.stderr or result.stdout or '').strip().splitlines()[-3:]
                        errors.append(' / '.join(tail) or '未知错误')
                    done += 1
                    report(20 + 22 * done / len(segments))

            threads = [
                threading.Thread(target=worker, args=(index, start, count), daemon=True)
                for index, (start, count) in enumerate(segments)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            if errors:
                if log:
                    log('并行渲染失败，改用单进程渲染…')
                clean_work()
            else:
                xml_paths = [os.path.join(work, f'bdn_{index}.xml') for index in range(len(segments))]
                if _merge_bdn_parts(xml_paths, os.path.join(work, 'bdn.xml')):
                    rendered = True
                    for path in xml_paths:
                        try:
                            os.remove(path)
                        except OSError:
                            pass

        if not rendered:
            ok, message = render_single()
            if not ok:
                return False, message

        os.makedirs(out_dir, exist_ok=True)
        for name in os.listdir(work):
            if name == 'bdn.xml' or re.fullmatch(r'\d{8}_\d+\.png', name):
                src = os.path.join(work, name)
                dst = os.path.join(out_dir, name)
                if os.path.exists(dst):
                    try:
                        os.remove(dst)
                    except OSError:
                        pass
                shutil.move(src, dst)
        report(45)
        return True, ''
    finally:
        shutil.rmtree(work, ignore_errors=True)


def generate_bdn_sup(ass_path: str, out_dir: str, fmt: str = '1080p', fps: str = '23.976',
                     language: str = 'chi', track_name: str = '', font_dir: str = '',
                     make_sup: bool = True, make_pes: bool = False,
                     params: dict = None, log=None, progress=None):
    """用 ass2bdnxml 生成 BDN XML，再用 SUPer 生成 SUP / PES+MUI。"""
    def report(value):
        if progress:
            progress(value)

    report(3)
    ok, info = ensure_bdn_tools(log)
    if not ok:
        return False, info, []
    if not os.path.isfile(ass_path):
        return False, '找不到 ASS 字幕文件', []
    os.makedirs(out_dir, exist_ok=True)
    report(10)

    for name in os.listdir(out_dir):
        if name == 'bdn.xml' or re.fullmatch(r'\d{8}(?:_\d+)?\.png', name):
            try:
                os.remove(os.path.join(out_dir, name))
            except OSError:
                pass

    bdn_path = os.path.join(out_dir, 'bdn.xml')
    use_vsfilter = str(fps) in VS_RENDER_FPS and vsfilter_available()
    if use_vsfilter:
        if font_dir and os.path.isdir(font_dir) and log:
            log('提示：VSFilterMod 只能使用系统已安装字体，字体目录仅在回退渲染时生效。')
        ok, message = render_bdn_with_vsfilter(
            ass_path, out_dir, fmt, str(fps), language, track_name,
            log=log, progress=progress)
        if not ok:
            if log:
                log(message + '，改用 libass 渲染…')
            use_vsfilter = False

    if not use_vsfilter:
        args = [bdn_tool_exe('ass2bdnxml'), '-v', fmt, '-f', str(fps), '-l', language]
        if track_name.strip():
            args += ['-t', track_name.strip()]
        if font_dir and os.path.isdir(font_dir):
            args += ['-a', font_dir]
        args.append(ass_path)

        if log:
            log('正在生成 BDN XML 与 PNG…')
        report(20)
        result = subprocess.run(
            args, cwd=out_dir, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=3600, creationflags=_no_window_flag(),
        )
        if result.returncode != 0 or not os.path.isfile(bdn_path):
            tail = (result.stderr or result.stdout or '').strip().splitlines()[-6:]
            return False, 'ass2bdnxml 失败：' + (' / '.join(tail) or '未知错误'), []
    _normalize_bdn_xml(bdn_path)
    outputs = [bdn_path]
    report(45)

    if make_sup or make_pes:
        stem = os.path.splitext(os.path.basename(ass_path))[0]
        sup_path = os.path.join(out_dir, stem + '.sup')
        if log:
            log('正在生成 SUP' + (' 与 PES+MUI' if make_pes else '') + '，复杂特效可能需要几分钟…')
        report(50)
        sup_args = build_super_args(params, sup_path, make_pes=make_pes)
        sup_result = subprocess.run(
            sup_args, cwd=out_dir, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=7200, creationflags=_no_window_flag(),
        )
        expected = [sup_path]
        if make_pes:
            expected += [
                os.path.join(out_dir, stem + '.pes'),
                os.path.join(out_dir, stem + '.pes.mui'),
                os.path.join(out_dir, stem + '.mui'),
            ]
        produced = [item for item in expected if os.path.isfile(item)]
        if sup_result.returncode != 0 or not produced:
            tail = (sup_result.stderr or sup_result.stdout or '').strip().splitlines()[-6:]
            return False, 'SUPer 失败：' + (' / '.join(tail) or '未知错误'), outputs + produced
        outputs.extend(produced)
    report(100)
    return True, '', outputs


def add_combo_arrow(combo, arrow_width: int = 13):
    """给 Combobox 覆盖一个单线分隔的自绘下拉箭头（不遮挡原生边框）。"""
    bar = tk.Frame(combo, bg=UI_FIELD_BORDER, width=1, bd=0, highlightthickness=0)
    right_bar = tk.Frame(combo, bg=UI_FIELD_BORDER, width=1, bd=0, highlightthickness=0)
    arrow = tk.Label(
        combo, text='\u25BE', bg='#ffffff', fg=UI_MUTED,
        font=(UI_FONT, 10), cursor='hand2', padx=1,
    )

    def post(event=None):
        if 'disabled' not in combo.state():
            combo.tk.call('ttk::combobox::Post', combo._w)

    for widget in (bar, arrow, right_bar):
        widget.bind('<Button-1>', post)

    def sync(event=None):
        width = combo.winfo_width()
        height = combo.winfo_height()
        if width <= 1 or height <= 1:
            return
        top = 2
        inner_height = max(1, height - 4)
        bar.place(x=max(1, width - arrow_width), y=top, width=1, height=inner_height)
        arrow.place(x=max(2, width - arrow_width + 1), y=top,
                    width=max(1, arrow_width - 2), height=inner_height)
        right_bar.place(x=max(2, width - 1), y=1, width=1, height=max(1, height - 2))

    combo.bind('<Configure>', sync, add='+')
    combo.after_idle(sync)
    return combo


def prepare_combobox(combo):
    """下拉关闭后清除选中状态，避免文字因选中配色显示为空白。"""
    def clear_selection(event=None):
        try:
            combo.selection_clear()
        except tk.TclError:
            pass

    for sequence in ('<FocusIn>', '<FocusOut>', '<<ComboboxSelected>>', '<ButtonRelease-1>'):
        combo.bind(sequence, clear_selection, add='+')
    return combo


class ToolTip:
    """鼠标悬停时显示说明文字。"""
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<Leave>', self.hide, add='+')
        widget.bind('<ButtonPress>', self.hide, add='+')

    def show(self, event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 14
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f'+{x}+{y}')
        tk.Label(
            self.tip, text=self.text, justify='left', background='#fffbe6',
            foreground='#243b53', relief='solid', borderwidth=1, wraplength=380,
            font=(UI_FONT, UI_SMALL_SIZE), padx=9, pady=7,
        ).pack()

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


BDN_PARAM_DEFAULTS = {
    'compression': '80',
    'acqrate': '100',
    'color': 'bt709',
    'quantizer': '3',
    'threads': 'auto',
    'allow_normal': False,
    'prefer_normal': False,
    'buffer': False,
    'full_palette': False,
    'extra_acq': '2',
    'redraw_period': '0',
    'ssim_tol': '0',
    'max_kbps': '',
    'log_level': 'off',
}

BDN_PARAM_HELP = {
    'compression': '压缩率 0-100。两次事件之间至少要间隔多少时间才做一次刷新（acquisition）。\n'
                   '数值越高越稳定、事件保留越多，码率也越高；越低越省码率，但可能丢事件或出现残留。\n'
                   '建议：普通对白 80-85，复杂特效 90-100。',
    'acqrate': '采集率 0-100。影响压缩因子的衰减速度，进而影响刷新次数。\n'
               '100 表示不再额外压缩；数值越低越省码率但画质下降。\n'
               '建议保持 100，码率超标时再降到 80-90。',
    'color': '目标色彩矩阵。\n'
             'bt709：1080p / 高清常用；bt601：576i/480i 标清；bt2020：UHD / HDR。\n'
             '选错会导致字幕颜色偏色。',
    'quantizer': '调色板量化器，决定每张图的颜色数量与选色方式。\n'
                 'libimagequant：质量最好；Qtzr：质量高但体积大；HexTree：均衡；Pillow：最快但质量最低。',
    'threads': '并行编码线程数。auto 自动选择（最多 8）。\n'
               '机器性能好可设 4-6 提速，过高收益递减。',
    'allow_normal': '允许“普通情况对象重定义”：解码时间不够时只更新两个图形中的一个，减少丢事件。\n'
                    '特效复杂、发现事件缺失时开启。',
    'prefer_normal': '优先“普通情况对象重定义”：即使时间足够也只更新一个对象，可明显降低码率，\n'
                     '但两个图形不再共用调色板，画质可能略降。',
    'buffer': '允许调色板更新缓冲（提前解码显示集），减少丢事件。\n'
              '复杂动画、事件频繁时建议开启。',
    'full_palette': '每次都写入完整调色板，兼容性更好但码率更高。\n'
                    'Authoring 软件或播放器出现调色板异常时开启；普通 SUP 不必。',
    'extra_acq': '调色板更新 N 次后插入一次采集（刷新）。0 关闭，建议 2-5。\n'
                 '可消除调色板动画之后的残影，代价是码率略增。',
    'redraw_period': '锚点间隔（秒）：给长时间不变的字幕定期插入刷新，方便解码器追赶。\n'
                     '0 关闭；最小 1 秒；数值越小码率越高。',
    'ssim_tol': '图像相似度容差偏移 -100~100。\n'
                '正值更容易把两张图判定为相同（省码率，可能丢细节）；负值更保守（更清晰，码率更高）。\n'
                '一般保持 0，闪烁/残影时试 +10~20。',
    'max_kbps': '最大码率检测（Kbps）。只用于检查输出是否超标，不会限制实际码流。\n'
                '0 或留空表示关闭。按目标码率填写，例如 1600。',
    'log_level': '日志写入文件。默认关闭；排查丢事件、码率、兼容性问题时开启。\n'
                 '精简(-10) 只记录关键决策；标准(20)/极简(25)/仅警告(30)/调试(10)。',
}


class BdnAdvancedDialog(tk.Toplevel):
    """SUPer 高级参数设置窗口，所有参数均带悬停说明。"""

    LOG_OPTIONS = (
        ('关闭', 'off'),
        ('精简 (-10)', '-10'),
        ('标准 (20)', '20'),
        ('极简 (25)', '25'),
        ('仅警告/错误 (30)', '30'),
        ('调试 (10)', '10'),
        ('最大调试 (5)', '5'),
    )

    def __init__(self, master, params: dict):
        super().__init__(master)
        self.title('高级参数（SUPer）')
        self.resizable(False, False)
        self.result = None
        self.vars = {}
        self.transient(master.winfo_toplevel())
        self.configure(bg=UI_CARD)
        self.geometry('640x730')

        tk.Label(
            self, text='鼠标移到参数名称或输入框上可查看说明',
            bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE),
        ).pack(anchor='w', padx=18, pady=(14, 0))

        body = tk.Frame(self, bg=UI_CARD, padx=16, pady=12)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)

        row = 0
        self.add_entry(body, row, '压缩率 [0-100]', 'compression', params)
        row += 1
        self.add_entry(body, row, '采集率 [0-100]', 'acqrate', params)
        row += 1
        self.add_combo(body, row, '色彩空间', 'color', ('bt709', 'bt601', 'bt2020'), params,
                       display={'bt709': 'bt709（高清）', 'bt601': 'bt601（标清）', 'bt2020': 'bt2020（UHD/HDR）'})
        row += 1
        self.add_combo(body, row, '量化器', 'quantizer', [item[1] for item in BDN_QUANTIZERS], params,
                       display={item[1]: item[0] for item in BDN_QUANTIZERS})
        row += 1
        self.add_combo(body, row, '线程数', 'threads', ['auto', '1', '2', '3', '4', '5', '6', '7', '8'], params)
        row += 1
        for key, label in (
            ('allow_normal', '允许普通情况对象重定义'),
            ('prefer_normal', '优先普通情况对象重定义'),
            ('buffer', '允许调色板更新缓冲'),
            ('full_palette', '写入完整调色板'),
        ):
            self.add_check(body, row, label, key, params)
            row += 1
        self.add_entry(body, row, '调色板更新后插入采集 [0 关闭]', 'extra_acq', params)
        row += 1
        self.add_entry(body, row, '锚点间隔（秒）[0 关闭]', 'redraw_period', params)
        row += 1
        self.add_entry(body, row, 'SSIM 容差偏移 [-100~100]', 'ssim_tol', params)
        row += 1
        self.add_entry(body, row, '最大码率测试（Kbps，留空关闭）', 'max_kbps', params)
        row += 1
        self.add_combo(body, row, '日志级别', 'log_level',
                       [item[1] for item in self.LOG_OPTIONS], params,
                       display={item[1]: item[0] for item in self.LOG_OPTIONS})

        buttons = ttk.Frame(body, style='Card.TFrame')
        buttons.grid(row=row + 1, column=0, columnspan=2, sticky='e', pady=(16, 0))
        ttk.Button(buttons, text='恢复默认', command=self.reset_defaults, style='Secondary.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(buttons, text='取消', command=self.destroy, style='Secondary.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(buttons, text='确定', command=self.apply, style='Accent.TButton').pack(side='left')

        self.bind('<Escape>', lambda event: self.destroy())
        self.update_idletasks()
        self.grab_set()
        center_window(self, master)

    def add_label(self, parent, row, text, key):
        label = ttk.Label(parent, text=text, style='Card.TLabel')
        label.grid(row=row, column=0, sticky='w', padx=(0, 12), pady=5)
        ToolTip(label, BDN_PARAM_HELP.get(key, ''))
        return label

    def add_entry(self, parent, row, text, key, params):
        self.add_label(parent, row, text, key)
        var = tk.StringVar(value=str(params.get(key, '')))
        entry = ttk.Entry(parent, textvariable=var, width=14, justify='center')
        entry.grid(row=row, column=1, sticky='w', pady=5)
        ToolTip(entry, BDN_PARAM_HELP.get(key, ''))
        self.vars[key] = (var, 'entry')

    def add_combo(self, parent, row, text, key, values, params, display=None):
        self.add_label(parent, row, text, key)
        raw = str(params.get(key, values[0]))
        shown = (display or {}).get(raw, raw)
        var = tk.StringVar(value=shown)
        combo = add_combo_arrow(prepare_combobox(ttk.Combobox(parent, textvariable=var, values=[(display or {}).get(v, v) for v in values],
                             state='readonly', width=28)))
        combo.grid(row=row, column=1, sticky='w', pady=5)
        ToolTip(combo, BDN_PARAM_HELP.get(key, ''))
        self.vars[key] = (var, 'combo', values, display or {})

    def add_check(self, parent, row, text, key, params):
        var = tk.BooleanVar(value=bool(params.get(key)))
        check = tk.Checkbutton(
            parent, text=text, variable=var, bg='#ffffff', fg='#243b53',
            activebackground='#ffffff', activeforeground='#243b53', selectcolor='#ffffff',
            font=(UI_FONT, UI_BODY_SIZE), highlightthickness=0, bd=0, padx=0, cursor='hand2',
        )
        check.grid(row=row, column=0, columnspan=2, sticky='w', pady=4)
        ToolTip(check, BDN_PARAM_HELP.get(key, ''))
        self.vars[key] = (var, 'check')

    def reset_defaults(self):
        for key, item in self.vars.items():
            kind = item[1]
            default = BDN_PARAM_DEFAULTS[key]
            if kind == 'check':
                item[0].set(bool(default))
            elif kind == 'combo':
                display = item[3]
                item[0].set(display.get(str(default), str(default)))
            else:
                item[0].set(str(default))

    def collect(self) -> dict:
        result = {}
        for key, item in self.vars.items():
            kind = item[1]
            if kind == 'check':
                result[key] = bool(item[0].get())
            elif kind == 'combo':
                shown = item[0].get()
                reverse = {v: k for k, v in item[3].items()}
                result[key] = reverse.get(shown, shown)
            else:
                result[key] = item[0].get().strip()

        def as_int(key, minimum, maximum, label):
            value = result[key]
            try:
                number = int(value)
            except ValueError:
                raise ValueError(f'{label} 需要填写整数')
            if not minimum <= number <= maximum:
                raise ValueError(f'{label} 超出范围（{minimum}-{maximum}）')
            result[key] = str(number)

        as_int('compression', 0, 100, '压缩率')
        as_int('acqrate', 0, 100, '采集率')
        as_int('extra_acq', 0, 99, '调色板更新后插入采集')
        as_int('ssim_tol', -100, 100, 'SSIM 容差偏移')

        try:
            redraw = float(result['redraw_period'] or 0)
        except ValueError:
            raise ValueError('锚点间隔需要填写数字')
        if redraw != 0 and not 1.0 <= redraw <= 3600:
            raise ValueError('锚点间隔需为 0，或 1-3600 秒')
        result['redraw_period'] = f'{redraw:g}'

        max_kbps = result['max_kbps']
        if max_kbps:
            as_int('max_kbps', 0, 48000, '最大码率测试')
        return result

    def apply(self):
        try:
            self.result = self.collect()
        except ValueError as exc:
            messagebox.showinfo('参数有误', str(exc), parent=self)
            return
        self.destroy()


class BdnSupPanel(ttk.Frame):
    """SUP 生成页：调用 ass2bdnxml + SUPer，工具在线更新。"""

    def __init__(self, master):
        super().__init__(master, style='App.TFrame')
        self.queue = queue.Queue()
        self.running = False
        self.params = dict(BDN_PARAM_DEFAULTS)
        self.build_ui()

    def build_ui(self):
        create_hero(
            self, '图形字幕',
            '由 ASS 生成 BDN XML + PNG，并编码 SUP、PES + MUI。',
        ).pack(fill='x', pady=(0, 12))

        file_outer, file_body = create_card(self, '字幕与输出')
        file_outer.pack(fill='x', pady=(0, 10))
        file_body.columnconfigure(1, weight=1)

        self.ass_var = tk.StringVar(value='')
        self.out_var = tk.StringVar(value='')

        def file_label(text, row):
            tk.Label(
                file_body, text=text, bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
            ).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=4)

        file_label('字幕文件', 0)
        ttk.Entry(file_body, textvariable=self.ass_var).grid(row=0, column=1, sticky='ew', pady=4)
        ttk.Button(file_body, text='选择', command=self.choose_ass, style='Secondary.TButton').grid(
            row=0, column=2, padx=(10, 0), pady=4)
        file_label('输出文件夹', 1)
        ttk.Entry(file_body, textvariable=self.out_var).grid(row=1, column=1, sticky='ew', pady=4)
        ttk.Button(file_body, text='选择', command=self.choose_out, style='Secondary.TButton').grid(
            row=1, column=2, padx=(10, 0), pady=4)

        option_outer, option_card = create_card(self, '生成选项')
        option_outer.pack(fill='x', pady=(0, 10))
        for column in range(3):
            option_card.columnconfigure(column, weight=1)

        self.fmt_var = tk.StringVar(value='1080p')
        self.fps_var = tk.StringVar(value='23.976')
        self.lang_var = tk.StringVar(value='chi')
        self.font_var = tk.StringVar(value='')
        self.make_sup_var = tk.BooleanVar(value=True)
        self.make_pes_var = tk.BooleanVar(value=False)

        def option_label(text, row, column, padx=(0, 0)):
            tk.Label(
                option_card, text=text, bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
            ).grid(row=row, column=column, sticky='w', padx=padx, pady=(0, 3))

        option_label('视频格式', 0, 0)
        self.fmt_combo = add_combo_arrow(prepare_combobox(ttk.Combobox(option_card, textvariable=self.fmt_var, values=BDN_FORMATS, state='readonly', width=12)))
        self.fmt_combo.grid(row=1, column=0, sticky='w', pady=(0, 8))
        ToolTip(self.fmt_combo, 'BDN 视频格式：1080p / 1080i / 720p / 576i / 480i。\n'
                           '普通蓝光电影选 1080p；720p 片源选 720p；标清 DVD 源选 576i/480i。')
        option_label('帧率', 0, 1, padx=(14, 0))
        self.fps_combo = add_combo_arrow(prepare_combobox(ttk.Combobox(option_card, textvariable=self.fps_var, values=BDN_FPS, state='readonly', width=10)))
        self.fps_combo.grid(row=1, column=1, sticky='w', padx=(14, 0), pady=(0, 8))
        ToolTip(self.fps_combo, 'BDN 帧率，必须与视频一致：23.976 / 24 / 25 / 29.97 / 50 / 59.94。\n'
                           '23.976 最常见；25 用于欧洲片源；59.94 仅 UHD 可用。')
        option_label('语言代码', 0, 2, padx=(14, 0))
        lang_entry = ttk.Entry(option_card, textvariable=self.lang_var, width=10)
        lang_entry.grid(row=1, column=2, sticky='w', padx=(14, 0), pady=(0, 8))
        ToolTip(lang_entry, 'BDN 元数据语言代码（ISO 639-2）：chi/zho 中文、eng 英文、jpn 日文。\n'
                            '只写入 bdn.xml 的 <Language Code>，不影响 SUP/PES 码流；\n'
                            '封装 MKV 或 Authoring 蓝光时需在对应软件里再设置轨道语言。')

        option_label('字体目录（选填）', 2, 0)
        font_frame = tk.Frame(option_card, bg=UI_CARD)
        font_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=(0, 2))
        font_frame.columnconfigure(0, weight=1)
        font_entry = ttk.Entry(font_frame, textvariable=self.font_var)
        font_entry.grid(row=0, column=0, sticky='ew')
        ttk.Button(font_frame, text='选择', command=self.choose_font, style='Secondary.TButton').grid(
            row=0, column=1, padx=(10, 0))
        ToolTip(font_entry, '额外字体目录。ASS 使用的字体若未安装在系统里，可在这里指定字体文件夹，\n'
                            'ass2bdnxml 会通过 libass 加载。')

        toggle_frame = tk.Frame(option_card, bg=UI_CARD)
        toggle_frame.grid(row=4, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self.make_sup_check = tk.Checkbutton(
            toggle_frame, text='同时生成 SUP', variable=self.make_sup_var,
            bg=UI_CARD, fg=UI_TEXT, activebackground=UI_CARD, activeforeground=UI_TEXT,
            selectcolor=UI_CARD, font=(UI_FONT, UI_BODY_SIZE),
            highlightthickness=0, bd=0, padx=0, cursor='hand2',
        )
        self.make_sup_check.pack(side='left')
        ToolTip(self.make_sup_check, '勾选后用 SUPer 把 BDN 编码为 SUP（PGS），输出 <字幕名>.sup。\n'
                                     '取消则只生成 bdn.xml 和 PNG。')
        self.make_pes_check = tk.Checkbutton(
            toggle_frame, text='同时生成 PES', variable=self.make_pes_var,
            bg=UI_CARD, fg=UI_TEXT, activebackground=UI_CARD, activeforeground=UI_TEXT,
            selectcolor=UI_CARD, font=(UI_FONT, UI_BODY_SIZE),
            highlightthickness=0, bd=0, padx=0, cursor='hand2',
        )
        self.make_pes_check.pack(side='left', padx=(18, 0))
        ToolTip(self.make_pes_check, '勾选后除 SUP 外同时生成 PES + MUI 文件。\n'
                                     'PES+MUI 用于 Scenarist 等蓝光 Authoring 软件；普通播放只用 SUP 即可。')
        ttk.Button(toggle_frame, text='高级参数', command=self.open_advanced, style='Secondary.TButton').pack(
            side='left', padx=(18, 0))

        self.progress = ttk.Progressbar(
            option_card, style='Blue.Horizontal.TProgressbar', orient='horizontal', mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(12, 0))

        action = tk.Frame(self, bg=UI_BG)
        action.pack(side='bottom', fill='x', pady=(10, 10))
        self.btn_start = ttk.Button(action, text='开始生成', command=self.start, style='Accent.TButton')
        self.btn_start.pack(side='left')
        self.btn_open = ttk.Button(action, text='打开输出文件夹', command=self.open_output, style='Secondary.TButton')
        self.btn_open.pack(side='left', padx=(10, 0))
        self.status_var = tk.StringVar(value='')
        tk.Label(
            action, textvariable=self.status_var, bg=UI_BG, fg=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE),
        ).pack(side='left', padx=(14, 0))

    def open_advanced(self):
        dialog = BdnAdvancedDialog(self, self.params)
        self.wait_window(dialog)
        if dialog.result:
            self.params = dialog.result
            self.status_var.set('高级参数已更新')

    def ingest_log(self, text: str):
        self.queue.put(('log', text))
        match = re.search(r'下载中 (\d+)%', text)
        if match:
            self.queue.put(('progress', int(match.group(1)) * 0.9))

    def choose_ass(self):
        path = filedialog.askopenfilename(
            title='选择 ASS 字幕', parent=self.winfo_toplevel(),
            filetypes=[('ASS 字幕', '*.ass'), ('所有文件', '*.*')],
        )
        if not path:
            return
        self.ass_var.set(path)
        if not self.out_var.get().strip():
            stem = os.path.splitext(os.path.basename(path))[0]
            self.out_var.set(os.path.join(os.path.dirname(path), f'{stem}_BDN'))

    def choose_out(self):
        path = filedialog.askdirectory(title='选择输出文件夹', parent=self.winfo_toplevel())
        if path:
            self.out_var.set(path)

    def choose_font(self):
        path = filedialog.askdirectory(title='选择字体目录', parent=self.winfo_toplevel())
        if path:
            self.font_var.set(path)

    def open_output(self):
        path = self.out_var.get().strip()
        if path and os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showinfo('提示', '输出文件夹还不存在', parent=self.winfo_toplevel())

    def _set_running(self, running: bool):
        self.running = running
        state = 'disabled' if running else 'normal'
        self.btn_start.config(state=state, text='生成中…' if running else '开始生成')
        self.status_var.set('正在处理，请稍候…' if running else '')
        try:
            self.winfo_toplevel().focus_set()
        except tk.TclError:
            pass

    def start(self):
        if self.running:
            return
        ass_path = self.ass_var.get().strip()
        out_dir = self.out_var.get().strip()
        if not os.path.isfile(ass_path):
            messagebox.showinfo('提示', '请先选择 ASS 字幕文件', parent=self.winfo_toplevel())
            return
        if not out_dir:
            messagebox.showinfo('提示', '请选择输出文件夹', parent=self.winfo_toplevel())
            return

        self._set_running(True)
        self.progress.configure(mode='determinate')
        self.progress['value'] = 0
        self.status_var.set('开始生成…')

        params = dict(self.params)

        def worker():
            try:
                ok, message, outputs = generate_bdn_sup(
                    ass_path, out_dir,
                    fmt=self.fmt_var.get(),
                    fps=self.fps_var.get(),
                    language=self.lang_var.get().strip() or 'und',
                    track_name='',
                    font_dir=self.font_var.get().strip(),
                    make_sup=bool(self.make_sup_var.get()),
                    make_pes=bool(self.make_pes_var.get()),
                    params=params,
                    log=self.ingest_log,
                    progress=lambda value: self.queue.put(('progress', value)),
                )
            except Exception as exc:
                ok, message, outputs = False, str(exc), []
            self.queue.put(('done', ok, message, outputs))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll)

    def _poll(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]
                if kind == 'log':
                    self.status_var.set(item[1])
                elif kind == 'progress':
                    self.progress.configure(mode='determinate')
                    self.progress['value'] = max(0, min(100, int(item[1])))
                elif kind == 'done':
                    ok, message, outputs = item[1], item[2], item[3]
                    self.progress.configure(mode='determinate')
                    self.progress['value'] = 100 if ok else 0
                    self._set_running(False)
                    if ok:
                        self.status_var.set('生成完成')
                        messagebox.showinfo('生成完成', '已生成：\n' + '\n'.join(outputs),
                                            parent=self.winfo_toplevel())
                    else:
                        self.status_var.set('生成失败')
                        messagebox.showerror('生成失败', message, parent=self.winfo_toplevel())
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)


def format_ass_time(ms: int) -> str:
    ms = max(0, int(round(ms)))
    hours = ms // 3600000
    minutes = ms % 3600000 // 60000
    seconds = ms % 60000 // 1000
    centis = (ms % 1000) // 10
    return f'{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}'


class IssueFixerPanel(ttk.Frame):
    """问题修复页：针对报告中的「请处理 / 请验证」逐条修改并重新生成字幕。"""

    def __init__(self, master):
        super().__init__(master, style='App.TFrame')
        self.data = None
        self.output_dir = ''
        self.source_path = ''
        self.dialogues = []
        self.source_lines = []
        self.styles = []
        self.entries = {}
        self.edits = {}
        self.dirty = False
        self.running = False
        self.save_queue = queue.Queue()
        self.build_ui()

    def build_ui(self):
        create_hero(
            self, '问题修复',
            '按「请处理 / 请验证」逐条修改，并重新生成全部字幕。',
        ).pack(fill='x', pady=(0, 10))

        file_outer, file_body = create_card(self, '问题数据')
        file_outer.pack(fill='x', pady=(0, 10))
        file_body.columnconfigure(1, weight=1)
        tk.Label(
            file_body, text='数据文件', bg=UI_CARD, fg=UI_TEXT,
            font=(UI_FONT, UI_BODY_SIZE),
        ).grid(row=0, column=0, sticky='w', padx=(0, 12), pady=4)
        self.path_var = tk.StringVar(value='')
        ttk.Entry(
            file_body, textvariable=self.path_var, state='readonly', style='Readonly.TEntry',
        ).grid(row=0, column=1, sticky='ew', pady=4)
        choose_button = ttk.Button(
            file_body, text='选择', command=self.choose_file, style='Secondary.TButton',
        )
        choose_button.grid(row=0, column=2, padx=(10, 0), pady=4)
        ToolTip(
            choose_button,
            '选择输出文件夹里的「字幕问题数据.json」，或直接选择字幕问题检查报告.html。')

        list_outer, list_body = create_card(self, '待处理字幕')
        list_outer.pack(fill='both', expand=True)
        list_body.columnconfigure(0, weight=1)
        list_body.rowconfigure(0, weight=1)

        tree_border = tk.Frame(list_body, bg=UI_FIELD_BORDER)
        tree_border.grid(row=0, column=0, sticky='nsew')
        tree_frame = tk.Frame(tree_border, bg='#ffffff')
        tree_frame.pack(fill='both', expand=True, padx=1, pady=1)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            tree_frame, columns=('idx', 'need', 'problem', 'text'), show='headings',
            style='Editor.Treeview', height=5, selectmode='browse',
        )
        for column, title, width, anchor in (
            ('idx', '#', 46, 'center'),
            ('need', '类型', 70, 'center'),
            ('problem', '问题', 170, 'w'),
            ('text', '文本', 360, 'w'),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor=anchor, stretch=column == 'text')
        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.tag_configure('process', foreground='#b91c1c')
        self.tree.tag_configure('verify', foreground='#b45309')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        bottom = tk.Frame(list_body, bg=UI_CARD)
        bottom.grid(row=1, column=0, sticky='ew', pady=(8, 0))
        bottom.columnconfigure(1, weight=1)

        form = tk.Frame(bottom, bg=UI_CARD)
        form.grid(row=0, column=0, sticky='nw')
        form.columnconfigure(1, weight=1)

        self.start_var = tk.StringVar(value='')
        self.end_var = tk.StringVar(value='')
        self.style_var = tk.StringVar(value='')

        tk.Label(
            form, text='样式', bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
        ).grid(row=0, column=0, sticky='w', padx=(0, 10), pady=(0, 4))
        self.style_combo = add_combo_arrow(prepare_combobox(ttk.Combobox(
            form, textvariable=self.style_var, state='readonly', width=16)))
        self.style_combo.grid(row=0, column=1, sticky='ew', pady=(0, 4))

        tk.Label(
            form, text='开始', bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
        ).grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(0, 4))
        ttk.Entry(form, textvariable=self.start_var, width=16).grid(
            row=1, column=1, sticky='ew', pady=(0, 4))
        tk.Label(
            form, text='结束', bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
        ).grid(row=2, column=0, sticky='w', padx=(0, 10), pady=(0, 4))
        ttk.Entry(form, textvariable=self.end_var, width=16).grid(
            row=2, column=1, sticky='ew', pady=(0, 4))

        text_frame = tk.Frame(bottom, bg=UI_CARD)
        text_frame.grid(row=0, column=1, sticky='nsew', padx=(16, 0))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        text_border = tk.Frame(text_frame, bg=UI_FIELD_BORDER)
        text_border.grid(row=0, column=0, sticky='nsew')
        text_border.rowconfigure(0, weight=1)
        text_border.columnconfigure(0, weight=1)
        self.text_edit = tk.Text(
            text_border, height=4, width=24, wrap='word', undo=True,
            font=(UI_FONT, UI_BODY_SIZE), bg='#ffffff', fg=UI_TEXT,
            insertbackground=UI_TEXT, relief='flat', bd=0,
            highlightthickness=0, padx=8, pady=6,
        )
        self.text_edit.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        self.text_edit.bind(
            '<FocusIn>', lambda event: text_border.configure(bg=UI_ACCENT))
        self.text_edit.bind(
            '<FocusOut>', lambda event: text_border.configure(bg=UI_FIELD_BORDER))
        tk.Label(
            bottom,
            text='保存会重新生成整个输出文件夹；繁体中文会重新经过繁化姬。原字幕文件不会被修改。',
            bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE),
        ).grid(row=1, column=0, columnspan=2, sticky='w', pady=(6, 0))

        action = tk.Frame(self, bg=UI_BG)
        action.pack(side='bottom', fill='x', pady=(10, 10))
        self.btn_apply = ttk.Button(
            action, text='应用修改', command=self.apply_current,
            style='Secondary.TButton', state='disabled')
        self.btn_apply.pack(side='right', padx=(0, 20))
        self.btn_save = ttk.Button(
            action, text='保存并重新生成', command=self.save_and_regenerate,
            style='Accent.TButton', state='disabled')
        self.btn_save.pack(side='left')
        self.btn_reload = ttk.Button(
            action, text='重新载入', command=self.reload,
            style='Secondary.TButton', state='disabled')
        self.btn_reload.pack(side='left', padx=(10, 0))

        self.status_var = tk.StringVar(value='请选择问题数据文件')
        ttk.Label(action, textvariable=self.status_var, style='Status.TLabel').pack(
            side='left', padx=(16, 0))

    def _buttons(self, enabled: bool):
        state = 'normal' if enabled else 'disabled'
        for button in (self.btn_apply, self.btn_save, self.btn_reload):
            button.config(state=state)

    def _status(self, text: str):
        self.status_var.set(text)

    def choose_file(self):
        if self.running:
            return
        if self.dirty and not messagebox.askyesno(
                '未保存', '当前修改尚未保存，仍要打开其他文件吗？', parent=self.winfo_toplevel()):
            return
        path = filedialog.askopenfilename(
            title='选择问题数据',
            filetypes=[
                ('问题数据 / 报告', '*.json *.html'),
                ('问题数据', '*.json'),
                ('问题报告', '*.html'),
                ('所有文件', '*.*'),
            ],
            parent=self.winfo_toplevel(),
        )
        if path:
            self.load(path)

    def reload(self):
        if not self.data:
            return
        self.load(os.path.join(self.output_dir, NOTICES_DATA_NAME))

    def load(self, path: str, silent: bool = False):
        if path.lower().endswith('.html'):
            path = os.path.join(os.path.dirname(path), NOTICES_DATA_NAME)
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            if not silent:
                messagebox.showerror(
                    '无法读取',
                    f'{exc}\n\n请先用当前版本重新生成一次字幕，输出文件夹里会生成「{NOTICES_DATA_NAME}」。',
                    parent=self.winfo_toplevel())
            return
        source_path = data.get('source', '')
        if not os.path.isfile(source_path):
            if not silent:
                messagebox.showerror(
                    '找不到源字幕', f'源文件不存在：\n{source_path}', parent=self.winfo_toplevel())
            return
        text = read_ass_text(source_path)
        if not text:
            if not silent:
                messagebox.showerror(
                    '无法读取源字幕', '源字幕为空或无法识别编码', parent=self.winfo_toplevel())
            return
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        dialogues = []
        in_events = False
        styles = []
        in_styles = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('['):
                in_events = stripped.lower() == '[events]'
                in_styles = stripped.lower() in ('[v4+ styles]', '[v4 styles]')
                continue
            if in_styles and line.lower().startswith('style:'):
                name = line.split(':', 1)[1].split(',', 1)[0].strip()
                if name and name not in styles:
                    styles.append(name)
                continue
            if not in_events or not line.lower().startswith('dialogue:'):
                continue
            if len(line.split(',', 9)) >= 10:
                dialogues.append(index)

        entries = {}
        for notice in data.get('notices') or []:
            need = str(notice.get('need', ''))
            if '请处理' not in need and '请验证' not in need:
                continue
            try:
                index = int(notice.get('index'))
            except (TypeError, ValueError):
                continue
            if not 1 <= index <= len(dialogues):
                continue
            item = entries.setdefault(index, {
                'need': need if '请处理' in need else '请验证',
                'problems': [],
            })
            if '请处理' in need:
                item['need'] = '请处理'
            if notice.get('problem'):
                item['problems'].append(str(notice['problem']))

        self.data = data
        self.output_dir = data.get('output_dir') or os.path.dirname(path)
        self.source_path = source_path
        self.dialogues = dialogues
        self.source_lines = lines
        self.styles = styles
        self.style_combo.configure(values=styles)
        self.entries = entries
        self.edits = {}
        self.dirty = False
        self.path_var.set(path)
        self._buttons(True)
        self.refresh_tree(select=next(iter(sorted(entries)), None))
        process_count = sum(1 for item in entries.values() if item['need'] == '请处理')
        verify_count = len(entries) - process_count
        self._status(f'待处理 {len(entries)} 条（请处理 {process_count} / 请验证 {verify_count}）')

    def _entry_values(self, index):
        edit = self.edits.get(index)
        if edit:
            start, end, style, text = edit['start'], edit['end'], edit['style'], edit['text']
        else:
            fields = self.source_lines[self.dialogues[index - 1]].split(',', 9)
            start = parse_ass_time(fields[1]) or 0
            end = parse_ass_time(fields[2]) or 0
            style = fields[3].strip()
            text = fields[9]
        preview = text.replace('\\N', ' / ').replace('\n', ' / ')
        return start, end, style, text, preview

    def refresh_tree(self, select=None):
        self.tree.delete(*self.tree.get_children())
        for index in sorted(self.entries):
            item = self.entries[index]
            _, _, _, _, preview = self._entry_values(index)
            tag = 'process' if item['need'] == '请处理' else 'verify'
            self.tree.insert('', 'end', iid=str(index), values=(
                index, item['need'], '；'.join(item['problems']), preview), tags=(tag,))
        if select is not None and str(select) in self.tree.get_children():
            iid = str(select)
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)
            self.on_select()

    def on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if index not in self.entries:
            return
        start, end, style, text, _ = self._entry_values(index)
        self.start_var.set(format_ass_time(start))
        self.end_var.set(format_ass_time(end))
        self.style_var.set(style)
        self.text_edit.delete('1.0', 'end')
        self.text_edit.insert('1.0', text)

    def _current_edit(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo('提示', '请先在上方列表选择一条字幕', parent=self.winfo_toplevel())
            return None
        index = int(selection[0])
        start = parse_ass_time(self.start_var.get())
        end = parse_ass_time(self.end_var.get())
        if start is None or end is None:
            messagebox.showinfo('时间格式有误', '请使用 0:00:01.00 这样的时间格式', parent=self.winfo_toplevel())
            return None
        if end <= start:
            messagebox.showinfo('时间有误', '结束时间必须晚于开始时间', parent=self.winfo_toplevel())
            return None
        text = self.text_edit.get('1.0', 'end-1c')
        text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\N')
        style = self.style_var.get().strip()
        return index, {'start': start, 'end': end, 'style': style, 'text': text}

    def apply_current(self):
        result = self._current_edit()
        if not result:
            return
        index, edit = result
        self.edits[index] = edit
        self.dirty = True
        self.refresh_tree(select=index)
        self._status(f'已修改 {len(self.edits)} 条 · 点「保存并重新生成」写入字幕')

    def save_and_regenerate(self):
        if self.running or not self.data:
            return
        selection = self.tree.selection()
        if selection:
            index = int(selection[0])
            start, end, style, text, _ = self._entry_values(index)
            current = (
                self.start_var.get().strip(), self.end_var.get().strip(),
                self.style_var.get().strip(),
                self.text_edit.get('1.0', 'end-1c'),
            )
            if current != (
                    format_ass_time(start), format_ass_time(end), style, text):
                result = self._current_edit()
                if not result:
                    return
                self.edits[result[0]] = result[1]

        text = read_ass_text(self.source_path)
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        for index, edit in self.edits.items():
            if not 1 <= index <= len(self.dialogues):
                continue
            line_index = self.dialogues[index - 1]
            fields = lines[line_index].split(',', 9)
            if len(fields) < 10:
                continue
            fields[1] = format_ass_time(edit['start'])
            fields[2] = format_ass_time(edit['end'])
            if edit.get('style'):
                fields[3] = edit['style']
            fields[9] = edit['text']
            lines[line_index] = ','.join(fields)

        output_dir = self.output_dir or self.data.get('output_dir', '')
        if not output_dir:
            messagebox.showerror('缺少输出目录', '问题数据里没有输出目录信息', parent=self.winfo_toplevel())
            return
        extension = os.path.splitext(self.source_path)[1] or '.ass'
        working = os.path.join(output_dir, f'{EDIT_SOURCE_PREFIX}{extension}')
        if os.path.abspath(self.source_path) == os.path.abspath(working):
            working = self.source_path
        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(working, 'w', encoding='utf-8-sig', newline='') as handle:
                handle.write('\n'.join(lines))
        except OSError as exc:
            messagebox.showerror('保存失败', str(exc), parent=self.winfo_toplevel())
            return

        meta = dict(self.data.get('meta') or {})
        meta['title'] = self.data.get('title', '')
        meta['output_root'] = os.path.dirname(output_dir)
        meta['source_label'] = self.data.get('source_label') or os.path.basename(self.source_path)

        self.running = True
        self._buttons(False)
        self._status('正在重新生成字幕…')
        self.save_queue = queue.Queue()
        is_hdr = bool(self.data.get('is_hdr'))
        is_mid_black = bool(self.data.get('is_mid_black'))

        def worker():
            try:
                _, outdir, _ = process_file(working, is_hdr, is_mid_black, meta)
                self.save_queue.put(('done', outdir))
            except Exception as exc:
                self.save_queue.put(('error', str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(150, self._poll_save)

    def _poll_save(self):
        try:
            item = self.save_queue.get_nowait()
        except queue.Empty:
            self.after(150, self._poll_save)
            return
        self.running = False
        self._buttons(True)
        if item[0] == 'error':
            self._status('重新生成失败')
            messagebox.showerror('重新生成失败', item[1], parent=self.winfo_toplevel())
            return
        outdir = item[1]
        self.dirty = False
        self.load(os.path.join(outdir, NOTICES_DATA_NAME))
        messagebox.showinfo(
            '已更新',
            '字幕与问题报告已重新生成。\n繁体中文已重新经过繁化姬处理。',
            parent=self.winfo_toplevel(),
        )


class App:
    def __init__(self, root):
        self.root = root
        register_bundled_fonts()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1000x800")
        self.root.minsize(940, 780)
        self._restore_window_position(load_config())
        try:
            self.root.iconbitmap(default=resource_path('ohMyAss Noto.ico'))
        except tk.TclError:
            pass
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.detector_window = None
        self.processing = False
        self.result_queue = queue.Queue()
        self.nav_photo_cache = {}
        self.initWidgets()
        config = load_config()
        self.title.set_value(config.get('title', ''))
        self.script_updated_by.set_value(config.get('script_updated_by', ''))
        self.use_taiwan.set(bool(config.get('taiwan', True)))
        self.hdr_brightness.set(str(config.get('hdr_brightness', int(HDR_SUB_BRIGHTNESS))))
        self.update_brightness_state()

    def _virtual_screen_bounds(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            left = user32.GetSystemMetrics(76)
            top = user32.GetSystemMetrics(77)
            width = user32.GetSystemMetrics(78)
            height = user32.GetSystemMetrics(79)
            if width > 0 and height > 0:
                return left, top, left + width, top + height
        except Exception:
            pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _work_area_for(self, x: int, y: int, width: int, height: int):
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                            ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', RECT),
                            ('rcWork', RECT), ('dwFlags', wintypes.DWORD)]

            user32 = ctypes.windll.user32
            rect = RECT(x, y, x + width, y + height)
            user32.MonitorFromRect.restype = wintypes.HMONITOR
            monitor = user32.MonitorFromRect(ctypes.byref(rect), 2)
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return (info.rcWork.left, info.rcWork.top,
                        info.rcWork.right, info.rcWork.bottom)
        except Exception:
            pass
        return self._virtual_screen_bounds()

    def _restore_window_position(self, config):
        try:
            x = int(config.get('window_x'))
            y = int(config.get('window_y'))
        except (TypeError, ValueError):
            return
        width, height = 1000, 800
        left, top, right, bottom = self._work_area_for(x, y, width, height)
        max_x = max(left, right - width)
        max_y = max(top, bottom - height)
        x = min(max(x, left), max_x)
        y = min(max(y, top), max_y)
        self.root.geometry(f"+{x}+{y}")

    def on_close(self):
        if getattr(self, 'sup_panel', None) and self.sup_panel.running:
            if not messagebox.askyesno('正在生成', 'SUP 正在生成中，确定要退出吗？', parent=self.root):
                return
        if getattr(self, 'fixer_panel', None) and self.fixer_panel.running:
            if not messagebox.askyesno('正在生成', '问题修复正在重新生成字幕，确定要退出吗？', parent=self.root):
                return
        if getattr(self, 'fixer_panel', None) and self.fixer_panel.dirty:
            if not messagebox.askyesno('未保存', '问题修复的修改尚未生成，确定要退出吗？', parent=self.root):
                return
        config = load_config()
        config.update({
            'title': self.title.get_value(),
            'script_updated_by': self.script_updated_by.get_value(),
            'taiwan': self.use_taiwan.get(),
            'hdr_brightness': self.hdr_brightness.get(),
        })
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        if x > -10000 and y > -10000:
            config['window_x'] = x
            config['window_y'] = y
        save_config(config)
        self.root.destroy()

    def setup_styles(self):
        pick_ui_fonts()
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        self.root.configure(bg=UI_BG)
        style.configure('.', font=(UI_FONT, UI_BODY_SIZE), background=UI_BG, foreground=UI_TEXT)
        style.configure('App.TFrame', background=UI_BG)
        style.configure('Card.TFrame', background=UI_CARD)
        style.configure('Card.TLabel', background=UI_CARD, foreground=UI_TEXT)
        style.configure('CardMuted.TLabel', background=UI_CARD, foreground=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE))
        style.configure('Status.TLabel', background=UI_BG, foreground=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE))
        style.configure('Hint.TLabel', background=UI_BG, foreground=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE))
        style.configure(
            'Accent.TButton', background=UI_ACCENT, foreground='#ffffff',
            bordercolor=UI_ACCENT, lightcolor=UI_ACCENT,
            darkcolor=UI_ACCENT, borderwidth=0,
            focusthickness=0, padding=(18, 11),
            font=(UI_DISPLAY_FONT, UI_BUTTON_SIZE, 'bold'), relief='groove',
        )
        style.map(
            'Accent.TButton',
            background=[('active', UI_ACCENT_DARK), ('disabled', '#b9cfe8')],
            foreground=[('disabled', '#f4f8fc')],
        )
        style.configure(
            'Secondary.TButton', background='#ffffff', foreground=UI_TEXT,
            bordercolor=UI_FIELD_BORDER, lightcolor='#ffffff',
            darkcolor='#ffffff', borderwidth=1, padding=(14, 9), relief='groove',
        )
        style.map(
            'Secondary.TButton',
            background=[('active', '#f5f7fa'), ('pressed', '#eef1f5')],
        )
        style.configure(
            'TEntry', fieldbackground='#ffffff', foreground=UI_TEXT,
            bordercolor=UI_FIELD_BORDER, lightcolor='#ffffff',
            darkcolor='#ffffff', borderwidth=1, padding=7,
        )
        style.map(
            'TEntry',
            bordercolor=[('focus', UI_ACCENT)],
            lightcolor=[('focus', UI_ACCENT)],
            darkcolor=[('focus', UI_ACCENT)],
        )
        style.configure(
            'Readonly.TEntry', fieldbackground='#fafbfc', foreground=UI_TEXT,
            bordercolor=UI_FIELD_BORDER, lightcolor='#fafbfc',
            darkcolor='#fafbfc', borderwidth=1, padding=7,
        )
        style.configure(
            'Placeholder.TEntry', fieldbackground='#ffffff', foreground=UI_MUTED,
            bordercolor=UI_FIELD_BORDER, lightcolor='#ffffff',
            darkcolor='#ffffff', borderwidth=1, padding=7,
        )
        style.configure(
            'TCombobox', fieldbackground='#ffffff', background='#ffffff',
            foreground=UI_TEXT, bordercolor=UI_FIELD_BORDER,
            lightcolor='#ffffff', darkcolor='#ffffff',
            arrowcolor=UI_MUTED, borderwidth=1, padding=5,
        )
        style.map(
            'TCombobox',
            fieldbackground=[('readonly', '#ffffff')],
            foreground=[('readonly', UI_TEXT)],
            selectbackground=[('readonly', '#ffffff'), ('focus', '#ffffff'), ('!focus', '#ffffff')],
            selectforeground=[('readonly', UI_TEXT), ('focus', UI_TEXT), ('!focus', UI_TEXT)],
            bordercolor=[('focus', UI_ACCENT)],
            lightcolor=[('focus', UI_ACCENT)],
            darkcolor=[('focus', UI_ACCENT)],
        )
        style.layout('TCombobox', [
            ('Combobox.field', {'sticky': 'nswe', 'children': [
                ('Combobox.padding', {'expand': '1', 'sticky': 'nswe', 'children': [
                    ('Combobox.textarea', {'sticky': 'nswe'}),
                ]}),
            ]}),
        ])
        style.configure('TCombobox', padding=(7, 7, 14, 7))
        style.configure(
            'Blue.Horizontal.TProgressbar', troughcolor='#eceff4', background=UI_ACCENT,
            bordercolor='#eceff4', lightcolor=UI_ACCENT, darkcolor=UI_ACCENT,
            borderwidth=0, thickness=8,
        )
        style.configure(
            'Editor.Treeview', background='#ffffff', fieldbackground='#ffffff',
            foreground=UI_TEXT, rowheight=23, borderwidth=0,
            font=(UI_FONT, UI_BODY_SIZE),
        )
        style.configure(
            'Editor.Treeview.Heading', background='#f4f6fa', foreground=UI_MUTED,
            font=(UI_FONT, UI_SMALL_SIZE), relief='flat', borderwidth=0,
        )
        style.map(
            'Editor.Treeview',
            background=[('selected', UI_ACCENT_SOFT)],
            foreground=[('selected', UI_TEXT)],
        )
        # 去掉 ttk 按钮的虚线焦点框
        button_layout = [
            ('Button.border', {'sticky': 'nswe', 'border': '1', 'children': [
                ('Button.padding', {'sticky': 'nswe', 'children': [
                    ('Button.label', {'sticky': 'nswe'}),
                ]}),
            ]}),
        ]
        style.layout('Accent.TButton', button_layout)
        style.layout('Secondary.TButton', button_layout)

    def initWidgets(self):
        self.setup_styles()
        shell = tk.Frame(self.root, bg=UI_BG)
        shell.pack(fill='both', expand=True)

        nav = tk.Frame(shell, bg=UI_BG, width=64)
        nav.pack(side='left', fill='y', padx=(10, 4), pady=14)
        nav.pack_propagate(False)
        self.nav_icons = {}

        def add_nav(key, label, side='top'):
            canvas = tk.Canvas(nav, width=48, height=44, bg=UI_BG,
                               highlightthickness=0, bd=0, cursor='hand2')
            canvas.pack(side=side, pady=(0, 6))
            canvas.bind('<Button-1>', lambda event, name=key: self.switch_tab(name))
            canvas.bind('<Enter>', lambda event, name=key: self.redraw_nav(hover=name))
            canvas.bind('<Leave>', lambda event: self.redraw_nav())
            ToolTip(canvas, label)
            self.nav_icons[key] = canvas

        for key, label in (('home', '主页'), ('ass', '文本字幕'),
                           ('fix', '问题修复'), ('sup', '图形字幕')):
            add_nav(key, label)
        tk.Frame(nav, bg=UI_BG).pack(fill='y', expand=True)
        add_nav('settings', '设置', side='bottom')

        container = tk.Frame(shell, bg=UI_BG)
        container.pack(side='left', fill='both', expand=True, padx=(6, 24), pady=12)

        self.pages = {
            'home': tk.Frame(container, bg=UI_BG),
            'ass': tk.Frame(container, bg=UI_BG),
            'fix': tk.Frame(container, bg=UI_BG),
            'sup': tk.Frame(container, bg=UI_BG),
            'settings': tk.Frame(container, bg=UI_BG),
        }
        self.build_home_page(self.pages['home'])
        self.build_ass_page(self.pages['ass'])
        self.fixer_panel = IssueFixerPanel(self.pages['fix'])
        self.fixer_panel.pack(fill='both', expand=True)
        self.sup_panel = BdnSupPanel(self.pages['sup'])
        self.sup_panel.pack(fill='both', expand=True)
        self.build_settings_page(self.pages['settings'])
        self.active_page = 'home'
        self.switch_tab('home')

    def switch_tab(self, key):
        self.active_page = key
        for name, page in self.pages.items():
            if name == key:
                page.pack(fill='both', expand=True)
            else:
                page.pack_forget()
        self.redraw_nav()

    def redraw_nav(self, hover=None):
        glyphs = {'home': ICON_HOME, 'ass': ICON_PENCIL,
                  'fix': ICON_FIX, 'sup': ICON_VIDEO, 'settings': ICON_SETTINGS}
        icon_kinds = {'home': 'home', 'ass': 'pencil', 'fix': 'fix',
                      'sup': 'frame', 'settings': 'settings'}
        for key, canvas in self.nav_icons.items():
            active = key == self.active_page
            canvas.delete('all')
            if active:
                _rounded_rect(canvas, 7, 4, 46, 40, 8, '#e4e8ee')
                canvas.create_rectangle(0, 12, 3, 32, fill=UI_ACCENT, outline='')
                color = UI_TEXT
            elif key == hover:
                _rounded_rect(canvas, 7, 4, 46, 40, 8, '#eceff4')
                color = UI_TEXT
            else:
                color = UI_MUTED
            photo = self._nav_photo(icon_kinds[key], color)
            if photo is not None:
                canvas.create_image(25, 22, image=photo)
            else:
                canvas.create_text(25, 22, text=glyphs[key],
                                   font=(UI_ICON_FONT, UI_ICON_NAV_SIZE), fill=color)

    def _nav_photo(self, kind: str, color: str):
        if ImageTk is None:
            return None
        cache_key = (kind, color)
        if cache_key in self.nav_photo_cache:
            return self.nav_photo_cache[cache_key]
        renderer = ICON_RENDERERS.get(kind)
        if renderer is None:
            return None
        icon = renderer(20, _hex_to_rgb(color), weight=1.3)
        if icon is None:
            return None
        photo = ImageTk.PhotoImage(icon)
        self.nav_photo_cache[cache_key] = photo
        return photo

    def build_home_page(self, main):
        create_hero(main, APP_NAME, APP_VERSION).pack(fill='x', pady=(0, 12))
        cards = tk.Frame(main, bg=UI_BG)
        cards.pack(fill='both', expand=True)
        for column in range(2):
            cards.columnconfigure(column, weight=1, uniform='modules')
        self.build_module_card(
            cards, 0, 0, 'pencil', '文本字幕',
            '字幕样式、标点、HDR 与繁简台湾化处理', 'ass')
        self.build_module_card(
            cards, 0, 1, 'fix', '问题修复',
            '按字幕问题报告快速修改并重新生成字幕', 'fix')
        self.build_module_card(
            cards, 1, 0, 'frame', '图形字幕',
            '由 ASS 生成 BDN XML + PNG，并编码 SUP、PES + MUI。', 'sup')
        self.build_module_card(
            cards, 1, 1, 'settings', '设置',
            '工具版本、字体安装与在线更新', 'settings')

    def build_module_card(self, parent, row, column, kind, title, description, target):
        card = RoundedFrame(parent, radius=8)
        card.configure(cursor='hand2')
        padx = (0, 12) if column == 0 else (12, 0)
        pady = (0, 12) if row == 0 else (0, 0)
        card.grid(row=row, column=column, sticky='nsew', padx=padx, pady=pady)
        inner = tk.Frame(card.body, bg=UI_CARD, padx=20, pady=18)
        inner.pack(fill='both', expand=True)

        glyph = {'pencil': ICON_PENCIL, 'frame': ICON_VIDEO, 'fix': ICON_FIX,
                 'settings': ICON_SETTINGS}.get(kind, ICON_PENCIL)
        renderer = {'pencil': render_pencil_icon, 'fix': render_wrench_icon,
                    'frame': render_camera_icon,
                    'settings': render_gear_icon}.get(kind)
        photo = None
        if renderer is not None and ImageTk is not None:
            icon = renderer(34)
            if icon is not None:
                photo = ImageTk.PhotoImage(icon)
        if photo is not None:
            icon_label = tk.Label(inner, image=photo, bg=UI_CARD)
            icon_label.image = photo
            icon_label.pack(anchor='w')
        else:
            tk.Label(
                inner, text=glyph, bg=UI_CARD, fg=UI_TEXT,
                font=(UI_ICON_FONT, UI_ICON_CARD_SIZE),
            ).pack(anchor='w')

        tk.Label(inner, text=title, bg=UI_CARD, fg=UI_TEXT,
                 font=(UI_DISPLAY_FONT, UI_MODULE_TITLE_SIZE, 'bold')).pack(anchor='w', pady=(10, 6))
        tk.Label(inner, text=description, bg=UI_CARD, fg=UI_MUTED,
                 font=(UI_FONT, UI_BODY_SIZE), wraplength=380, justify='left').pack(anchor='w')

        footer = tk.Frame(inner, bg=UI_CARD)
        footer.pack(fill='x', pady=(18, 0))
        tk.Label(footer, text='进入模块', bg=UI_CARD, fg=UI_TEXT,
                 font=(UI_FONT, UI_BODY_SIZE, 'bold')).pack(side='left')
        tk.Label(footer, text='\u2192', bg=UI_CARD, fg=UI_TEXT,
                 font=(UI_FONT, UI_BODY_SIZE, 'bold')).pack(side='right')

        def bind_click(widget):
            widget.bind('<Button-1>', lambda event, name=target: self.switch_tab(name))
            for child in widget.winfo_children():
                bind_click(child)

        bind_click(card)

    def build_ass_page(self, main):
        create_hero(main, '文本字幕', '字幕样式、标点、HDR 与繁简台湾化处理').pack(fill='x', pady=(0, 10))

        file_outer, file_body = create_card(main, '字幕与输出')
        file_outer.pack(fill='x', pady=(0, 10))
        file_body.columnconfigure(1, weight=1)

        def file_label(text, row):
            tk.Label(
                file_body, text=text, bg=UI_CARD, fg=UI_TEXT,
                font=(UI_FONT, UI_BODY_SIZE),
            ).grid(row=row, column=0, sticky='w', padx=(0, 12), pady=6)

        file_label('字幕文件', 0)
        self.file_entry = PlaceholderEntry(
            file_body, placeholder='支持 .ass / .srt，自动识别 UTF-8 / UTF-16 / GBK')
        self.file_entry.grid(row=0, column=1, sticky='ew', pady=6)
        self.btn_open = ttk.Button(file_body, text='选择', command=self.openFile, style='Secondary.TButton')
        self.btn_open.grid(row=0, column=2, sticky='e', padx=(12, 0), pady=6)

        file_label('输出文件夹', 1)
        self.output_root_entry = PlaceholderEntry(
            file_body, placeholder='留空则输出到源字幕所在目录下的 <片名> 文件夹')
        self.output_root_entry.grid(row=1, column=1, sticky='ew', pady=6)
        ttk.Button(file_body, text='选择', command=self.choose_output_root,
                   style='Secondary.TButton').grid(row=1, column=2, sticky='e', padx=(12, 0), pady=6)

        options_outer, options_card = create_card(main, '片源选项')
        options_outer.pack(fill='x', pady=(0, 10))
        self.is_HDR = tk.BooleanVar()
        self.option_is_HDR = self.make_option_check(options_card, 'HDR 高动态', self.is_HDR)
        self.option_is_HDR.grid(row=0, column=0, sticky='w')
        tk.Label(
            options_card, text='亮度', bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
        ).grid(row=0, column=1, sticky='w', padx=(20, 0))
        self.hdr_brightness = tk.StringVar(value=str(int(HDR_SUB_BRIGHTNESS)))
        self.hdr_brightness_entry = ttk.Entry(
            options_card, textvariable=self.hdr_brightness, width=6, justify='center')
        self.hdr_brightness_entry.grid(row=0, column=2, sticky='w', padx=(6, 0))
        tk.Label(
            options_card, text='nit', bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE),
        ).grid(row=0, column=3, sticky='w', padx=(4, 0))
        self.is_mid_black = tk.BooleanVar()
        self.option_is_mid_black = self.make_option_check(options_card, '中黑边视频', self.is_mid_black)
        self.option_is_mid_black.grid(row=0, column=5, sticky='w', padx=(20, 0))
        self.use_taiwan = tk.BooleanVar(value=True)
        self.option_use_taiwan = self.make_option_check(options_card, '繁体台湾化（繁化姬）', self.use_taiwan)
        self.option_use_taiwan.grid(row=0, column=4, sticky='w', padx=(20, 0))
        self.btn_black = ttk.Button(options_card, text='黑边检测', command=self.open_black_detector, style='Secondary.TButton')
        self.btn_black.grid(row=0, column=6, sticky='e', padx=(20, 0))
        options_card.columnconfigure(6, weight=1)
        self.is_HDR.trace_add('write', self.update_brightness_state)
        self.update_brightness_state()

        info_outer, info_card = create_card(main, '字幕信息')
        info_outer.pack(fill='x', pady=(0, 10))
        info_card.columnconfigure(1, weight=1)
        info_card.columnconfigure(3, weight=1)

        self.title = PlaceholderEntry(info_card, placeholder='必填')
        self.script_updated_by = PlaceholderEntry(info_card, placeholder='必填')
        self.original_script = PlaceholderEntry(info_card, placeholder='选填')
        self.original_translation = PlaceholderEntry(info_card, placeholder='选填')
        self.original_timing = PlaceholderEntry(info_card, placeholder='选填')
        self.original_editing = PlaceholderEntry(info_card, placeholder='选填')

        def field_label(text):
            return tk.Label(info_card, text=text, bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE))

        field_label('片名 *').grid(row=0, column=0, sticky='w', padx=(0, 8), pady=7)
        self.title.grid(row=0, column=1, sticky='ew', padx=(0, 20), pady=7)
        field_label('字幕员 *').grid(row=0, column=2, sticky='w', padx=(0, 8), pady=7)
        self.script_updated_by.grid(row=0, column=3, sticky='ew', pady=7)

        field_label('原作者').grid(row=1, column=0, sticky='w', padx=(0, 8), pady=7)
        self.original_script.grid(row=1, column=1, sticky='ew', padx=(0, 20), pady=7)
        field_label('翻译').grid(row=1, column=2, sticky='w', padx=(0, 8), pady=7)
        self.original_translation.grid(row=1, column=3, sticky='ew', pady=7)

        field_label('校对').grid(row=2, column=0, sticky='w', padx=(0, 8), pady=7)
        self.original_timing.grid(row=2, column=1, sticky='ew', padx=(0, 20), pady=7)
        field_label('时间轴').grid(row=2, column=2, sticky='w', padx=(0, 8), pady=7)
        self.original_editing.grid(row=2, column=3, sticky='ew', pady=7)

        action = tk.Frame(main, bg=UI_BG)
        action.pack(side='bottom', fill='x', pady=(10, 10))
        self.btn_process = ttk.Button(action, text='开始生成', command=self.start_process, style='Accent.TButton')
        self.btn_process.pack(side='left')
        self.btn_output_open = ttk.Button(
            action, text='打开输出文件夹', command=self.open_output_folder, style='Secondary.TButton')
        self.btn_output_open.pack(side='left', padx=(10, 0))
        self.status_var = tk.StringVar(value='')
        ttk.Label(action, textvariable=self.status_var, style='Status.TLabel').pack(side='left', padx=(16, 0))

    def open_output_folder(self):
        path = getattr(self, 'last_output_dir', None)
        if path and os.path.isdir(path):
            os.startfile(path)
            return
        path = self.output_root_entry.get_value()
        if path and os.path.isdir(path):
            os.startfile(path)
            return
        source = self.file_entry.get_value()
        if source and os.path.isfile(source):
            os.startfile(os.path.dirname(os.path.abspath(source)))
            return
        messagebox.showinfo('提示', '还没有可打开的输出文件夹', parent=self.root)

    def choose_output_root(self):
        path = filedialog.askdirectory(title='选择输出文件夹', parent=self.root)
        if path:
            self.output_root_entry.set_value(path)

    def build_settings_page(self, main):
        create_hero(main, '设置', '工具、字体与在线更新').pack(fill='x', pady=(0, 10))

        card_outer, card = create_card(main, '工具（在线更新）')
        card_outer.pack(fill='x')
        card.columnconfigure(0, weight=1)

        self.tool_label = tk.StringVar(value=bdn_tool_version_text())
        tk.Label(
            card, textvariable=self.tool_label, bg=UI_CARD, fg=UI_TEXT,
            font=(UI_FONT, UI_BODY_SIZE),
        ).grid(row=0, column=0, sticky='w')
        self.btn_update = ttk.Button(card, text='检查更新', command=self.update_tools, style='Secondary.TButton')
        self.btn_update.grid(row=0, column=1, sticky='e')

        tk.Label(
            card, text='工具安装位置：' + BDN_TOOL_ROOT,
            bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE), wraplength=680, justify='left',
        ).grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 0))

        self.settings_status = tk.StringVar(value='')
        tk.Label(
            card, textvariable=self.settings_status, bg=UI_CARD, fg=UI_MUTED,
            font=(UI_FONT, UI_SMALL_SIZE), wraplength=680, justify='left',
        ).grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 0))

        self.settings_progress = ttk.Progressbar(
            card, style='Blue.Horizontal.TProgressbar', orient='horizontal', mode='determinate')
        self.settings_progress.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(8, 0))

        font_outer, font_card = create_card(main, '字体')
        font_outer.pack(fill='x', pady=(10, 0))
        font_card.columnconfigure(0, weight=1)

        font_title = tk.Frame(font_card, bg=UI_CARD)
        font_title.grid(row=0, column=0, columnspan=2, sticky='ew')
        tk.Label(
            font_title, text='思源黑体 Medium（Source Han Sans SC Medium）',
            bg=UI_CARD, fg=UI_TEXT, font=(UI_FONT, UI_BODY_SIZE),
        ).pack(side='left')
        self.font_state_label = tk.Label(
            font_title, text='', bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_BODY_SIZE))
        self.font_state_label.pack(side='left', padx=(10, 0))

        self.btn_font = ttk.Button(
            font_card, text='检查并安装', command=self.install_font, style='Secondary.TButton')
        self.btn_font.grid(row=0, column=1, sticky='e')

        self.font_status = tk.StringVar(value='')
        tk.Label(
            font_card, textvariable=self.font_status, bg=UI_CARD, fg=UI_MUTED,
            font=(UI_FONT, UI_SMALL_SIZE), wraplength=680, justify='left',
        ).grid(row=1, column=0, columnspan=2, sticky='w', pady=(6, 0))

        tk.Label(
            font_card,
            text='字幕渲染使用的默认字体；未安装时自动下载 SourceHanSansSC-Medium.otf 并安装到当前用户。',
            bg=UI_CARD, fg=UI_MUTED, font=(UI_FONT, UI_SMALL_SIZE),
            wraplength=680, justify='left',
        ).grid(row=2, column=0, columnspan=2, sticky='w', pady=(4, 0))

        self.font_progress = ttk.Progressbar(
            font_card, style='Blue.Horizontal.TProgressbar', orient='horizontal', mode='determinate')
        self.font_progress.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(8, 0))

        self.refresh_font_status()

    def refresh_font_status(self):
        installed = source_han_medium_installed()
        self.font_state_label.config(
            text='已安装' if installed else '未安装',
            fg='#15803d' if installed else '#b45309',
        )

    def install_font(self):
        if getattr(self, 'font_installing', False):
            return
        self.font_installing = True
        self.btn_font.config(state='disabled', text='处理中…')
        self.font_progress['value'] = 0
        self.font_status.set('正在检查字体…')
        self.font_queue = queue.Queue()

        def worker():
            def log(text):
                self.font_queue.put(('log', text))
            try:
                ok, message = ensure_source_han_font(log)
            except Exception as exc:
                ok, message = False, str(exc)
            self.font_queue.put(('done', ok, message))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_font()

    def _poll_font(self):
        try:
            while True:
                item = self.font_queue.get_nowait()
                if item[0] == 'log':
                    self.font_status.set(item[1])
                    match = re.search(r'下载中 (\d+)%', item[1])
                    if match:
                        self.font_progress['value'] = int(match.group(1))
                else:
                    ok, message = item[1], item[2]
                    self.font_installing = False
                    self.btn_font.config(state='normal', text='检查并安装')
                    self.font_progress['value'] = 100 if ok else 0
                    self.font_status.set(message)
                    self.refresh_font_status()
                    if not ok:
                        messagebox.showerror('字体安装失败', message, parent=self.root)
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_font)

    def update_tools(self):
        if getattr(self, 'sup_panel', None) and self.sup_panel.running:
            messagebox.showinfo('提示', '正在生成字幕，请稍候再更新工具', parent=self.root)
            return
        self.btn_update.config(state='disabled', text='检查中…')
        self.settings_progress['value'] = 0
        self.settings_status.set('开始检查更新…')
        self.update_queue = queue.Queue()

        def worker():
            def log(text):
                self.update_queue.put(('log', text))
            try:
                ok, message = install_all_bdn_tools(log, force=True)
            except Exception as exc:
                ok, message = False, str(exc)
            self.update_queue.put(('done', ok, message))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_update()

    def _poll_update(self):
        try:
            while True:
                item = self.update_queue.get_nowait()
                if item[0] == 'log':
                    self.settings_status.set(item[1])
                    match = re.search(r'下载中 (\d+)%', item[1])
                    if match:
                        self.settings_progress['value'] = int(match.group(1)) * 0.9
                else:
                    ok, message = item[1], item[2]
                    self.settings_progress['value'] = 100 if ok else 0
                    self.btn_update.config(state='normal', text='检查更新')
                    self.tool_label.set(bdn_tool_version_text())
                    self.settings_status.set('工具已是最新版本' if ok else f'更新失败：{message}')
                    if not ok:
                        messagebox.showerror('更新失败', message, parent=self.root)
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_update)

    def open_black_detector(self):
        if Image is None:
            messagebox.showerror(
                "缺少依赖",
                "黑边检测需要 Pillow，请先运行：pip install pillow",
            )
            return
        try:
            if self.detector_window and self.detector_window.window.winfo_exists():
                self.detector_window.window.lift()
                self.detector_window.window.focus_force()
                return
        except tk.TclError:
            pass
        self.detector_window = BlackBarDetectorWindow(self.root, on_mid_black=self.is_mid_black.set)

    def make_option_check(self, parent, text, variable):
        return tk.Checkbutton(
            parent, text=text, variable=variable,
            bg=UI_CARD, fg=UI_TEXT, activebackground=UI_CARD, activeforeground=UI_TEXT,
            selectcolor=UI_CARD, font=(UI_FONT, UI_BODY_SIZE),
            highlightthickness=0, bd=0, padx=0, cursor='hand2',
        )

    def update_brightness_state(self, *args):
        enabled = bool(self.is_HDR.get()) and not self.processing
        self.hdr_brightness_entry.config(state='normal' if enabled else 'disabled')

    def openFile(self):
        file_path = filedialog.askopenfilename(filetypes=[
            ("字幕文件", "*.ass *.srt"),
            ("ASS 字幕", "*.ass"),
            ("SRT 字幕", "*.srt"),
            ("所有文件", "*.*"),
        ])
        if file_path:
            self.file_entry.set_value(file_path)

    def _set_processing_state(self, processing: bool):
        self.processing = processing
        state = 'disabled' if processing else 'normal'
        self.btn_process.config(state=state, text='生成中...' if processing else '开始生成')
        self.btn_output_open.config(state=state)
        self.btn_black.config(state=state)
        self.btn_open.config(state=state)
        self.option_is_HDR.config(state=state)
        self.option_is_mid_black.config(state=state)
        self.option_use_taiwan.config(state=state)
        self.update_brightness_state()
        self.status_var.set('正在生成字幕，请稍候...' if processing else '')

    def _process_worker(self, file_name, is_hdr, is_mid_black, meta):
        try:
            result = process_file(file_name, is_hdr, is_mid_black, meta)
            error = None
        except Exception as exc:
            log_path = os.path.join(os.path.dirname(os.path.abspath(file_name)), 'style_adjustment_error.log')
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(traceback.format_exc())
            except Exception:
                pass
            result = None
            error = str(exc)
        self.result_queue.put((result, error, is_hdr))

    def _poll_process_result(self):
        try:
            result, error, is_hdr = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_process_result)
            return
        self._process_finished(result, error, is_hdr)

    def _process_finished(self, result, error, is_hdr):
        self._set_processing_state(False)
        if error:
            messagebox.showerror(
                "生成失败",
                f"生成失败：{error}\n\n详细信息请查看源文件目录下的 style_adjustment_error.log",
                parent=self.root,
            )
            return
        html_path, output_dir, chinese_only = result
        self.last_output_dir = output_dir
        auto_loaded = False
        fixer = getattr(self, 'fixer_panel', None)
        json_path = os.path.join(output_dir, NOTICES_DATA_NAME)
        if (fixer and not fixer.running and not fixer.dirty
                and os.path.isfile(json_path)):
            fixer.load(json_path, silent=True)
            auto_loaded = bool(fixer.entries)
        message = build_success_message(html_path, output_dir, chinese_only, is_hdr)
        if auto_loaded:
            message += f'\n\n问题数据已自动载入「问题修复」页面（{len(fixer.entries)} 条）。'
        messagebox.showinfo("生成完成", message, parent=self.root)
        self.status_var.set('生成完成')

    def start_process(self):
        if self.processing:
            return
        file_name = self.file_entry.get_value()
        if not re.search(r'^/|^[a-z]:', file_name, re.IGNORECASE):
            tk.messagebox.showinfo("提示", "未选择文件")
            return

        meta = {
            'title': self.title.get_value(),
            'original_script': self.original_script.get_value(),
            'original_translation': self.original_translation.get_value(),
            'original_timing': self.original_timing.get_value(),
            'original_editing': self.original_editing.get_value(),
            'script_updated_by': self.script_updated_by.get_value(),
            'taiwan': self.use_taiwan.get(),
            'output_root': self.output_root_entry.get_value(),
        }
        try:
            brightness = float(self.hdr_brightness.get().strip())
        except ValueError:
            brightness = 0.0
        if not 1 <= brightness <= 1000:
            messagebox.showinfo("提示", "字幕亮度请填写 1 到 1000 之间的数字（单位 nit）", parent=self.root)
            return
        meta['hdr_brightness'] = brightness

        title = meta['title']
        updated_by = meta['script_updated_by']
        if not title:
            messagebox.showinfo("提示", "片名为必填项，请填写后再生成", parent=self.root)
            return
        if not updated_by:
            messagebox.showinfo("提示", "字幕员为必填项，请填写后再生成", parent=self.root)
            return

        save_config({
            'title': title,
            'script_updated_by': updated_by,
            'taiwan': self.use_taiwan.get(),
            'hdr_brightness': self.hdr_brightness.get(),
        })

        output_dir = get_output_dir(file_name, title, meta['output_root'])
        if output_dir is None:
            messagebox.showinfo("提示", "片名不能用于文件夹名，请修改", parent=self.root)
            return

        if self.is_HDR.get():
            expected = [
                '1-简英双语-HDR-zh.ass',
                '2-简英双语-SDR-zh.ass',
                '3-简体中文-HDR-zh.ass',
                '4-繁体中文-HDR-zh.ass',
                '5-英文-HDR-en.ass',
                '1-简体中文-HDR-zh.ass',
                '2-简体中文-SDR-zh.ass',
                '3-繁体中文-HDR-zh.ass',
            ]
        else:
            expected = [
                '1-简英双语-zh.ass',
                '2-简体中文-zh.ass',
                '3-繁体中文-zh.ass',
                '4-英文-en.ass',
                '1-简体中文-zh.ass',
                '2-繁体中文-zh.ass',
            ]
        expected += [
            NOTICES_REPORT_NAME,
            TAIWAN_REPORT_NAME,
        ]
        existing = [
            name for name in expected
            if os.path.exists(os.path.join(output_dir, name))
        ]
        if existing:
            preview = '\n'.join(existing)
            if not messagebox.askyesno(
                "确认覆盖",
                f"输出文件夹中已存在以下文件：\n{preview}\n\n"
                f"继续生成可能覆盖同名文件，是否继续？",
                parent=self.root,
            ):
                return

        self._set_processing_state(True)
        thread = threading.Thread(
            target=self._process_worker,
            args=(file_name, self.is_HDR.get(), self.is_mid_black.get(), meta),
            daemon=True,
        )
        thread.start()
        self.root.after(100, self._poll_process_result)

if __name__ == '__main__':
    root = None
    if DND_AVAILABLE:
        try:
            root = TkinterDnD.Tk()
        except Exception:
            DND_AVAILABLE = False
    if root is None:
        root = tk.Tk()
    app = App(root)
    root.mainloop()

    # if len(sys.argv) > 1:
    #    input_file = sys.argv[1]
    # else:
    #     input_file = input('输入文件名：')   

    # black = input('是否中黑边 [n]：')
    # is_mid_black = (black.lower() == 'y')

    # i = input('1. SDR  2. HDR  请选择 [1]：')
    # is_HDR = (i == "2")

    #  # input_file = '到也门钓鲑鱼-华文.ass'
    # start_process(input_file, is_HDR, is_mid_black)

