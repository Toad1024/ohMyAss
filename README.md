# ohMyAss Noto

面向字幕组的 **ASS 字幕批处理工具**（Windows 桌面应用），覆盖「文本字幕规范化 → HDR 映射 → 繁简 / 台湾化 → 图形字幕 SUP 生成」的完整流程。

![ohMyAss Noto](ohMyAss%20Noto.png)

> 当前版本：**v0.5.5** ｜ 平台：Windows 10 / 11（x64）

---

## 功能模块

| 模块 | 说明 |
|---|---|
| **文本字幕** | 读取 `.ass` / `.srt`，按 CMCT 样式规范重排，处理标点、断句、行内标签、双语对齐，可选 HDR 颜色映射与繁体台湾化，输出多语种字幕并生成问题报告 |
| **问题修复** | 打开「文本字幕」生成的问题数据（JSON），按「请处理 / 请验证」逐条修改时间轴和文本，一键重新生成全部字幕 |
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

到 [Releases](https://github.com/Toad1024/ohMyAss/releases) 下载 `ohMyAss Noto v0.5.5.exe`，双击运行。

### 方式二：从源码运行

```powershell
pip install pillow zhconv tkinterdnd2

# 注意文件名带空格，必须加引号
python "ohMyAss Noto v0.5.5.py"
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

- `问题报告.html` —— 需人工确认的条目
- `繁体台湾化对比.html` —— 开启台湾化时生成

---

## 目录结构

```
ohMyAss Noto v0.5.5.py   主程序（单文件）
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
| 界面配置、上次填写的片名等 | `%USERPROFILE%\.cmct_style_adjustment_v2.json` |
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

### v0.5.5

- 文本字幕：HDR 亮度可配置（1–1000 nit），默认 100
- 文本字幕：新增繁体台湾化对比报告
- 图形字幕：新增量化器选择与 PES / MUI 输出
- 问题修复：支持修改时间轴并批量重新生成
- 设置：外部工具支持在线检查更新

---

## 反馈

问题与建议请提交 [Issues](https://github.com/Toad1024/ohMyAss/issues)。
