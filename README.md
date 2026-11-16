# ohMyAss Noto

面向字幕组的 **ASS 字幕批处理工具**（Windows 桌面应用），覆盖「文本字幕规范化 → HDR 映射 → 繁体台湾化 → 图形字幕 SUP 生成」的完整流程。

![ohMyAss Noto](ohMyAss%20Noto.png)

> 当前版本：**v0.5.8** ｜ 平台：Windows 10 / 11（x64）

---

## 功能模块

| 模块 | 说明 |
|---|---|
| **文本字幕** | 读取 `.ass` / `.srt`，按 CMCT 样式规范重排，处理标点、断句、行内标签、双语对齐，可选 HDR 颜色映射与繁体台湾化，输出多语种字幕并生成问题报告 |
| **问题修复** | 打开「文本字幕」生成的问题数据（JSON），按「请处理 / 请确认」逐条修改时间轴和文本，一键重新生成全部字幕 |
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

# 注意文件名带空格，必须加引号
python "ohMyAss Noto v0.5.8.py"
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
ohMyAss Noto v0.5.8.py   主程序（单文件）
ohMyAss Noto.ico         应用图标
ohMyAss Noto.png         展示图
version_info.txt         PyInstaller 版本资源
bin/                     图形字幕运行时依赖
  AviSynth.dll            脚本帧服务
  VSFilterMod.dll         字幕渲染滤镜
  DevIL.dll               图像编解码
  avs2bdnxml.exe          ASS → BDN XML
```

## 本地数据位置

| 内容 | 路径 |
|---|---|
| 界面配置、上次填写的片名等 | `%USERPROFILE%\ohMyAssNoto.json` |
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

### v0.5.8

- 修复自动更新点击重启后没有反应：更新批处理不再写入错误的换行（此前每行变成 CR CR LF，导致路径变量带上多余字符，复制失败）
- 更新批处理改为二进制写入，路径优先使用 8.3 短路径，避免中文和空格路径受代码页影响
- 更新流程增加替换重试、写入权限检查与 `ohMyAssNoto_update.log` 日志，成功复制后再启动新版本
- 更新完成后自动清理下载的临时文件
- 图形字幕：ASS 文本按文件缓存、队列进度合并重绘、渐变颜色与表头重绘优化

### v0.5.7

- 样式库重构为 10 个固定类别，新增 Default 兜底样式，支持粘贴样式文本识别、恢复默认和即时预览
- 样式修改现在会写入生成字幕；新增行间距缩进（`\fsvp`），双语中英文样式成对同步
- 新增术语表页面与术语一致性检查，支持导入/导出 CSV
- 问题修复页支持术语问题、样式选择与更完整的重新生成流程
- 新增深色主题（跟随系统 / 浅色 / 深色），适配高 DPI 缩放
- 问题报告更名为「字幕问题报告.html」，「请验证」统一改为「请确认」
- 新增闪轴检查（相邻字幕间隔低于 200ms），特效字幕不参与过短轴、闪轴和重叠检查
- 图形字幕队列进度刷新、ASS 读取和字体检查缓存优化

---

## 反馈

问题与建议请提交 [Issues](https://github.com/cmct/ohMyAss/issues)。
