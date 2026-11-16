"""网络请求与文件下载工具。"""


import re
import urllib.request
import urllib.parse


TOOLS_USER_AGENT = 'ohMyAssNoto/1.0'


def tools_request(url: str, timeout: int = 60):
    request = urllib.request.Request(url, headers={'User-Agent': TOOLS_USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def download_file(url: str, dest: str, log=None, timeout: int = 120):
    with tools_request(url, timeout=timeout) as response, open(dest, 'wb') as out:
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


def html_latest_tag(repo: str) -> str:
    """通过 releases/latest 跳转拿到最新版本号（一次请求，不走 API）。"""
    response = tools_request(f'https://github.com/{repo}/releases/latest', timeout=60)
    final_url = response.geturl()
    match = re.search(r'/releases/tag/([^/?#]+)', final_url)
    if not match:
        raise RuntimeError('无法获取最新版本号')
    return urllib.parse.unquote(match.group(1))
