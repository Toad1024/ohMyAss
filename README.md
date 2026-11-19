# ohMyAss Noto

面向字幕组的 **ASS 字幕批处理工具**（Windows 桌面应用），覆盖「文本字幕规范化 → HDR 映射 → 繁体台湾化 → 图形字幕 SUP 生成」的完整流程。

![ohMyAss Noto](ohMyAss%20Noto.png)

> 当前版本：**v0.6.1** ｜ 平台：Windows 10 / 11（x64）

---

## 功能模块

| 模块 | 说明 |
|---|---|
| **文本字幕** | 读取 `.ass` / `.srt`，按 CMCT 样式规范重排，处理标点、断句、行内标签、双语对齐，可选 HDR 颜色映射与繁体台湾化，输出多语种字幕并生成问题报告 |
| **问题修复** | 打开「文本字幕」生成的问题数据（JSON），逐条修改时间轴和文本；保存时自动同步全部语言字幕并重新分析，支持撤回和右键删除字幕条 |
| **图形字幕** | 由 ASS 生成 BDN XML + PNG，再编码为 SUP / PES + MUI，支持多种分辨率与帧率 |
| **设置** | 外部工具版本检查与在线更新、思源黑体（Source Han Sans Medium）安装、应用更新 |

### 文本字幕

- **输入格式**：`.ass`、`.srt`，自动识别 UTF-8 / UTF-16 / GBK 编码
- **多语种输出**：简英双语、简体中文、繁体中文、英文
- **HDR 处理**：按 ssaHdrify 的映射算法把 SDR 样式颜色转换为 BT.2020 + PQ，亮度默认 100 nit，可填 1–1000
- **繁体台湾化**：调用[繁化姬](https://zhconvert.org)在线接口，并生成「普通繁体 ↔ 台湾化」逐条对比报告
- **黑边检测**：载入电影截图自动识别上下 / 中黑边比例
- **问题报告**：生成 HTML 报告，标出超长行、疑似单语行、格式异常等需要人工确认的条目

### 图形字幕

- 内置 AviSynth / VSFilterMod / avs2bdnxml 运行环境，按时间轴切片渲染
- 支持 **1080p / 1080i / 720p / 576i / 480i**，帧率支持 **23.976 / 24 / 25 / 29.97 / 50 / 59.94**
- 可选量化器：libimagequant（质量最好）、Qtzr（质量高、体积大）、HexTree（均衡）、Pillow（最快）
- 输出 SUP，可同时产出 PES + MUI

---

## 环境要求

| 使用方式 | 依赖 |
|---|---|
| 运行打包版 `.exe` | 无需安装 Python |
| 源码运行 | Python 3.9+（含 tkinter）、`Pillow`、`zhconv`，可选 `tkinterdnd2` |

`tkinterdnd2` 仅用于拖拽文件，缺失时自动降级，不影响其他功能。

---

## 快速开始

### 方式一：下载发布版

到 [Releases](https://github.com/cmct/ohMyAss/releases) 下载最新的发布版，双击运行。

### 方式二：从源码运行

```powershell
pip install pillow zhconv tkinterdnd2

# 入口文件名带空格，必须加引号
python "ohMyAss Noto.py"
```

---

## 使用流程

### 1. 文本字幕

1. 选择字幕文件（可拖入）
2. 按需勾选 **HDR 高动态**（并填亮度）、**中黑边视频**、**繁体台湾化（繁化姬）**
3. 填写字幕信息：

   | 字段 | 必填 | 说明 |
   |---|---|---|
   | 片名 | ✅ | 同时用于生成输出文件夹名，不能包含非法字符 |
   | 字幕员 | ✅ | 写入 `Script Updated By` |
   | 原作者 / 翻译 / 校对 / 时间轴 | — | 写入 ASS Script Info 的对应字段 |

4. 点击 **开始生成**，完成后可直接 **打开输出文件夹**

### 2. 问题修复（可选）

处理完成后如报告里有需要人工确认的条目，进入 **问题修复**，选择生成的 JSON 数据文件，逐条修改后重新生成。

### 3. 图形字幕

选择 ASS 与输出文件夹 → 设置分辨率、帧率、量化器 → 生成。首次使用需联网下载 `ass2bdnxml` 与 `SUPer`（在 **设置 → 检查更新** 中完成）。

---

## 输出说明

输出目录默认为「源字幕所在目录 / 片名」，也可手动指定。

双语片源典型输出：

```
1-简英双语-zh.ass        简英双语
2-简体中文-zh.ass        简体中文
3-繁体中文-zh.ass        繁体中文（可选台湾化）
4-英文-en.ass            英文
```

HDR 模式额外产出 SDR 对照版本（如 `2-简英双语-SDR-zh.ass`），并生成：

- `字幕问题报告.html` —— 需人工确认的条目
- `繁体台湾化对比.html` —— 开启台湾化时生成

---

## 目录结构

```
ohMyAss Noto.py          入口：单实例检查、主窗口启动
app_info.py              版本号与资源路径
config_store.py          配置、错误日志、路径工具
download_utils.py        下载与发布页解析
theme_ui.py              主题令牌、DPI、字体、图标、通用控件
reports.py               HTML 报告与问题数据解析
subtitle_core.py         ASS/SRT 解析、HDR、术语、文本规则、生成流程
fonts.py                 字体注册与思源黑体安装
bdn_sup.py               BDN/SUP/PES 生成与 VSFilterMod 渲染
app_update.py            软件自身在线更新
app_ui.py                主窗口与面板组装
ui_widgets.py            拖放与占位输入框
ui_blackbar.py           黑边检测窗口
ui_style.py              样式编辑器与预览
ui_fixer.py              术语表与问题修复面板
ui_bdn.py                图形字幕面板与任务队列
tests/                   单元测试
ohMyAss Noto.ico         应用图标
ohMyAss Noto.png         展示图
version_info.txt         PyInstaller 版本资源
bin/                     图形字幕运行时依赖
  AviSynth.dll            脚本帧服务
  VSFilterMod.dll         字幕渲染滤镜
  DevIL.dll               图像编解码
  avs2bdnxml.exe          ASS → BDN XML
```

## 源码结构与测试

源码按职责拆分，依赖方向为「基础工具 → 字幕核心 → 渲染/更新 → UI」，没有循环导入：

```text
app_info / config_store / download_utils
        ↓
theme_ui / reports / fonts
        ↓
subtitle_core
        ↓
app_update / bdn_sup
        ↓
ui_widgets → ui_blackbar / ui_style / ui_fixer / ui_bdn
        ↓
app_ui → 入口
```

运行单元测试（时间轴、样式、术语、报告解析、配置、更新脚本）：

```powershell
python -m unittest discover -s tests -v
```

### 打包（Windows）

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name "ohMyAss Noto" `
  --icon "ohMyAss Noto.ico" --version-file version_info.txt `
  --add-data "ohMyAss Noto.ico;." --add-data "ohMyAss Noto.png;." `
  --add-data "bin\*;." --collect-all tkinterdnd2 --collect-data zhconv `
  "ohMyAss Noto.py"
```

> `--collect-data zhconv` 必须保留：zhconv 的 `zhcdict.json` 不随模块自动打包，缺失时生成文本字幕会报 `FileNotFoundError`。

## 本地数据位置

| 内容 | 路径 |
|---|---|
| 界面配置、上次填写的片名等 | `%USERPROFILE%\ohMyAssNoto.json` |
| 错误日志（异常兜底记录） | `%USERPROFILE%\ohMyAssNoto_error.log` |
| 自动下载的外部工具 | `%LOCALAPPDATA%\ohMyAssNoto\tools` |

---

## 外部依赖与许可声明

本仓库 `bin/` 下为运行时所需的三方二进制，**版权归各自作者所有**，遵循其原始许可：

| 组件 | 来源 | 许可 |
|---|---|---|
| AviSynth | [AviSynth/AviSynthPlus](https://github.com/AviSynth/AviSynthPlus) | GPL-2.0 |
| VSFilterMod | 上游 VSFilter 分支 | GPL 系（以项目页面为准） |
| DevIL | [DentonW/DevIL](https://github.com/DentonW/DevIL) | LGPL-2.1 |
| ass2bdnxml | [cubicibo/ass2bdnxml](https://github.com/cubicibo/ass2bdnxml) | 见项目页面 |
| SUPer | [cubicibo/SUPer](https://github.com/cubicibo/SUPer) | 见项目页面 |
| 7zr | [7-zip.org](https://www.7-zip.org/) | LGPL |
| 繁化姬 API | [zhconvert.org](https://zhconvert.org) | 在线服务，需联网 |
| zhconv | PyPI | MIT |
| Pillow | PyPI | HPND |
| tkinterdnd2 | PyPI | MIT |

这些组件仅按原样打包以方便使用，本项目不对其做修改。如需分发衍生版本，请自行确认各上游许可的合规要求。

## 许可

本项目自身代码以 [MIT License](LICENSE) 发布 —— 可自由使用、修改、分发，保留版权声明即可。

⚠️ `bin/` 下的三方二进制**不在** MIT 许可范围内，仍遵循各自的上游许可（见上表）。若你二次分发，请自行确认合规。

---

## 已知限制

- 仅支持 Windows（依赖 Win32 注册表、`os.startfile`、`ctypes.windll`）
- 繁体台湾化需要联网访问繁化姬接口
- 图形字幕首次使用需要联网下载 `ass2bdnxml` / `SUPer`
- BDN 渲染按时间轴切片，长片耗时较长，建议预留磁盘空间

---

## 更新日志

### v0.6.1

- **问题修复页**
  - 直接编辑生成后的主字幕：双语以简英双语为基础，单语以简体中文为基础
  - 保存时把文本与时间同步到简体 / 繁体 / 英文及对应 HDR / SDR 文件，并重新分析、刷新问题报告
  - 保存、同步、重新分析改为后台线程执行，点击后界面保持响应
  - 新增「撤回」按钮：可撤回上一步「应用修改」，也可从备份恢复误删的字幕条并重新分析
  - 问题列表支持右键删除字幕条，按语言同步删除
  - 编辑栏边框与开始 / 结束输入框统一为 `TEntry` 主题边框，聚焦时同样显示 2px 强调色
  - 问题列表预览显示真实 `\N`
- **备份**
  - 修改或删除前自动备份到 `%LOCALAPPDATA%\ohMyAssNoto\backups\<时间戳>`
  - 只保留最近 10 批备份，并自动清理输出目录中旧版留下的 `.bak`
- **图形字幕**
  - 字幕队列支持右键「从队列移除」，生成中禁用
  - 生成中锁定输出文件夹输入框与「选择」按钮
  - 单文件与多文件队列的完成弹窗统一简化，只突出成功 / 失败；校验问题改写入错误日志
- **主页**
  - 修复「设置」卡片与上方卡片间距过小
- **其他**
  - `process_file` 支持只分析不写文件（`write_outputs=False`）
  - 修复 `Dialogue` 匹配误伤样式名的问题
  - 移除旧样式名、旧报告级别与旧版文件名兼容逻辑

### v0.6.0

- **在线更新**：启动自动检查与设置页手动检查，下载后校验 SHA-256，关闭软件、替换 EXE 并自动启动新版本
- **术语表**：新增术语表页面，支持导入/导出 CSV，并在生成时检查译文与术语表是否一致
- **样式修改与预览**：10 类固定样式可编辑、恢复默认，支持行间距缩进，并可打开 1080p 样式预览
- **图形字幕生成队列**：支持多 ASS 排队渲染，显示逐条进度、完成/失败状态，可取消，输出 BDN XML + PNG + SUP（可选 PES/MUI）
- 问题报告与问题修复页：生成 `字幕问题报告.html` / `字幕问题数据.json`，按「请处理 / 请确认」逐条修改并重新生成
- 其他：深色主题与高 DPI、HDR 颜色映射、繁化姬台湾化、黑边检测、模块化源码与单元测试
- 文件名统一为 `ohMyAss Noto`，不再带版本号；旧版本样式名/报告级别不再兼容

---

## 反馈

问题与建议请提交 [Issues](https://github.com/cmct/ohMyAss/issues)。
