"""软件自身在线更新。"""


import os
import sys
import re
import json
import subprocess
import tempfile
import urllib.request
import urllib.parse

from config_store import log_exception
from download_utils import TOOLS_USER_AGENT, html_latest_tag, tools_request, download_file


APP_UPDATE_REPO = 'cmct/ohMyAss'
APP_UPDATE_ASSET = 'ohMyAss Noto.exe'


def _app_assets_from_page(repo: str, tag: str):
    page = tools_request(
        f'https://github.com/{repo}/releases/expanded_assets/{urllib.parse.quote(tag)}',
        timeout=60,
    ).read().decode('utf-8', 'replace')
    assets = []
    seen = set()
    for href in re.findall(r'href="(/[^"]+/releases/download/[^"]+)"', page):
        url = 'https://github.com' + href
        name = urllib.parse.unquote(url.rsplit('/', 1)[-1])
        lower = name.lower()
        if lower.endswith('.exe') and 'ohmyass' in lower and url not in seen:
            seen.add(url)
            assets.append((name, url))
    return assets


def fetch_app_update():
    """返回 (最新版本号, 下载地址, 资源文件名)。"""
    repo = APP_UPDATE_REPO
    tag = ''
    assets = []
    try:
        request = urllib.request.Request(
            f'https://api.github.com/repos/{repo}/releases/latest',
            headers={'User-Agent': TOOLS_USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        tag = str(data.get('tag_name') or '')
        for asset in data.get('assets') or []:
            name = str(asset.get('name') or '')
            url = str(asset.get('browser_download_url') or '')
            lower = name.lower()
            if lower.endswith('.exe') and 'ohmyass' in lower and url:
                assets.append((name, url))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # 接口不可用时退回发布页解析，仍失败则用固定下载地址
        tag = ''
        log_exception('检查软件更新', exc)
    if not tag:
        tag = html_latest_tag(repo)
    if not assets:
        assets = _app_assets_from_page(repo, tag)
    if not assets:
        name = APP_UPDATE_ASSET
        url = (f'https://github.com/{repo}/releases/latest/download/'
               f'{urllib.parse.quote(name)}')
        assets = [(name, url)]
    for name, url in assets:
        if name.lower() == APP_UPDATE_ASSET.lower():
            return tag, url, name
    return tag, assets[0][1], assets[0][0]


def download_app_update(url: str, log=None, timeout: int = 900):
    folder = tempfile.mkdtemp(prefix='oma_update_')
    destination = os.path.join(folder, APP_UPDATE_ASSET)
    download_file(url, destination, log=log, timeout=timeout)
    return destination


def build_app_update_script() -> str:
    """生成更新批处理内容（纯 ASCII，路径全部通过环境变量传入）。"""
    lines = [
        '@echo off',
        'setlocal EnableExtensions',
        'echo [%date% %time%] update start>>"%LOG%"',
        'echo pid %PID%>>"%LOG%"',
        'echo target "%TARGET%">>"%LOG%"',
        'echo source "%SOURCE%">>"%LOG%"',
        'if not exist "%SOURCE%" goto missing',
        'set /a tries=0',
        ':wait',
        'tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul',
        'if errorlevel 1 goto copy',
        'ping -n 2 127.0.0.1 >nul',
        'set /a tries+=1',
        'if %tries% GEQ 60 goto copy',
        'goto wait',
        ':copy',
        'attrib -R "%TARGET%" >nul 2>&1',
        'set /a copies=0',
        ':copytry',
        'copy /Y "%SOURCE%" "%TARGET%" >nul 2>&1',
        'if not errorlevel 1 goto copied',
        'ping -n 2 127.0.0.1 >nul',
        'set /a copies+=1',
        'if %copies% GEQ 90 goto failed',
        'goto copytry',
        ':copied',
        'echo [%date% %time%] copied>>"%LOG%"',
        'cd /d "%TARGETDIR%"',
        'start "" "%TARGET%"',
        'if errorlevel 1 echo start failed>>"%LOG%"',
        'echo [%date% %time%] started>>"%LOG%"',
        'rd /s /q "%SOURCEDIR%" >nul 2>&1',
        'goto done',
        ':missing',
        'echo [%date% %time%] source missing>>"%LOG%"',
        'goto done',
        ':failed',
        'echo [%date% %time%] copy failed>>"%LOG%"',
        ':done',
        'del /f /q "%~f0" >nul 2>&1',
    ]
    return '\r\n'.join(lines) + '\r\n'


def apply_app_update(new_exe: str):
    """用批处理等待当前进程退出后替换 EXE 并重启。"""
    if not getattr(sys, 'frozen', False):
        return False, '源码运行模式无法自动替换'
    current = os.path.abspath(sys.executable)
    folder = os.path.dirname(current)
    try:
        if not os.access(folder, os.W_OK):
            return False, '程序目录没有写入权限，请手动下载替换'
    except OSError:
        return False, '无法访问程序目录'
    if not os.path.isfile(new_exe):
        return False, '更新文件不存在，请重新下载'
    try:
        if os.path.getsize(new_exe) < 1024 * 1024:
            return False, '更新文件不完整，请重新下载'
    except OSError:
        return False, '无法读取更新文件'
    log_path = os.path.join(folder, 'ohMyAssNoto_update.log')
    script = os.path.join(tempfile.gettempdir(), f'oma_update_{os.getpid()}.bat')
    content = build_app_update_script()
    env = dict(os.environ)
    env.update({
        'PID': str(os.getpid()),
        'TARGET': current,
        'TARGETDIR': folder,
        'SOURCE': new_exe,
        'SOURCEDIR': os.path.dirname(new_exe),
        'LOG': log_path,
    })
    try:
        with open(script, 'wb') as handle:
            handle.write(content.encode('ascii'))
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        # 路径通过环境变量传递，脚本内容保持纯 ASCII；
        # 双引号包裹可兼容带空格的临时目录。
        subprocess.Popen(
            f'cmd /c ""{script}""', env=env, creationflags=flags, close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, str(exc)
    return True, ''
