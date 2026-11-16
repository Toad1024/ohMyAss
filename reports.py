"""HTML 报告与问题数据。"""


import os
import difflib
import html
from collections import Counter


TAIWAN_REPORT_NAME = '繁体台湾化对比.html'
NOTICES_REPORT_NAME = '字幕问题报告.html'
NOTICES_DATA_NAME = '字幕问题数据.json'


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


def parse_issue_entries(data: dict) -> dict:
    """把问题数据 JSON 的 notices 转成 {行号: {need, problems}}。

    级别只接受当前的「请处理 / 请确认」。
    """
    entries = {}
    if not isinstance(data, dict):
        return entries
    for notice in data.get('notices') or []:
        if not isinstance(notice, dict):
            continue
        need = str(notice.get('need', ''))
        if '请处理' not in need and '请确认' not in need:
            continue
        try:
            index = int(notice.get('index'))
        except (TypeError, ValueError):
            continue
        if index <= 0:
            continue
        item = entries.setdefault(index, {
            'need': '请处理' if '请处理' in need else '请确认',
            'problems': [],
        })
        if '请处理' in need:
            item['need'] = '请处理'
        if notice.get('problem'):
            item['problems'].append(str(notice['problem']))
    return entries


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
        line_label = '全文' if line_no.strip() in ('0', '') else line_no
        type_counts[problem] += 1
        if '请确认' in need:
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
            f'<td class="line">{html.escape(line_label)}</td>'
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
        f'<div class="stat verify">请确认<b>{verify_count}</b></div>'
        f'<div class="stat check">请检查<b>{check_count}</b></div>'
        f'<div class="stat process">请处理<b>{process_count}</b></div>'
    )
    title_text = html.escape(title or '未命名')
    source = html.escape(source_label or os.path.basename(filename))
    return render_report_page(
        f'字幕问题报告 - {title_text}',
        '字幕问题报告',
        f'影片名：{title_text}<br>源文件：{source}',
        summary,
        table,
        type_chips,
    )


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
        f'影片名：{title_text}<br>源文件：{source}',
        summary,
        table,
        chips,
    )
