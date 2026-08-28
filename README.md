# 🌊 Waterfall Media Viewer (瀑布流媒体查看器)

<div align="center">

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D4?logo=windows)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)
![Qt](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt%206-41CD52?logo=qt)
![License](https://img.shields.io/badge/license-MIT-blue)
![Offline](https://img.shields.io/badge/privacy-100%25%20Offline-success)

**一款专为 Windows 打造的轻量级、极速现代本地图片与视频瀑布流查看器。**  
告别传统单图软件来回切图的繁琐，以现代化瀑布流卡片尽览整个文件夹的美图与短视频。

[✨ 核心亮点](#-核心亮点) • [📸 界面预览](#-界面预览) • [🚀 快速使用](#-快速使用) • [⌨️ 快捷键指南](#️-快捷键指南) • [🛠️ 本地构建](#️-本地构建)

</div>

---

## ✨ 核心亮点

- ⚡ **超流畅虚拟瀑布流**：数万张图片与视频瞬间秒开，基于可视区域动态渲染，内存占用始终极低。
- 🖼️ **全格式全面支持**：
  - **静态图片**：JPG, JPEG, JFIF, PNG, WebP, BMP, ICO, TIFF...
  - **动态动图**：GIF 逐帧原速流畅播放。
  - **高清视频**：MP4, MKV, WebM, MOV, AVI, WMV, M4V（基于内置 libVLC 高清解码与硬件加速）。
- 🔍 **专业看图体验**：
  - 高质量平滑抗锯齿缩放与智能 100% 像素对齐。
  - 类似 Honeyview 的高效手势：**鼠标右键 + 滚轮实时缩放**、纯滚轮快速切图。
  - 界面两侧悬浮半透明箭头，鼠标轻轻一点随心切换。
- 🎬 **轻量视频播放器**：
  - 瀑布流中实时显示视频时长徽章与提取的高清首帧封面。
  - 单击无缝进入播放模式，支持进度条即点即跳（JumpSlider）、音量调节、滚轮切集。
- 🎨 **现代化 Windows 11 Fluent 视觉**：
  - 原生级精雕细琢的浅色 Modern UI、精致微投影、圆角卡片。
  - 极简图标化工具栏，纯净无广告，100% 离线保护隐私。

---

## 📸 界面预览

<div align="center">
  <img src="docs/ui-preview-fluent.png" alt="瀑布流媒体查看器界面" width="880"/>
</div>

---

## 🚀 快速使用

### 1. 免安装即开即用（推荐）
直接运行 `dist\WaterfallMediaViewer\WaterfallMediaViewer.exe` 即可启动，无需安装任何 Python 环境与第三方依赖。

### 2. 双击便捷启动
- **`启动查看器.vbs`**：静默在后台启动软件，无任何黑框命令行打扰。
- **`调试启动.bat`**：带控制台窗口启动，方便排查开发错误。

---

## ⌨️ 快捷键指南

| 按键 / 手势 | 操作功能 |
| :--- | :--- |
| **鼠标左键双击/单击** | 在瀑布流中快速打开大图/播放视频 |
| **鼠标滚轮** | 图片/视频查看模式下切换 上一张 / 下一张 |
| **鼠标右键 + 滚轮** | 以鼠标为中心进行平滑连续放大 / 缩小 |
| **`←` / `→` 方向键** | 切换 上一张 / 下一张 |
| **`F`** | 适应窗口大小 |
| **`1`** | 切换为 100% 原始像素比例 |
| **`F11`** | 进入 / 退出全屏模式 |
| **`Esc`** | 退出全屏或从大图模式返回瀑布流列表 |
| **`空格键 (Space)`** | 视频播放 / 暂停 |
| **`Ctrl + O`** | 打开媒体文件 |
| **`Ctrl + Shift + O`** | 打开并扫描新文件夹 |

---

## 🛠️ 本地开发与构建

### 环境要求
- Windows 10 / 11
- Python 3.12+

### 安装运行
```powershell
# 1. 创建并激活虚拟环境
py -3.12 -m venv .venv
.\.venv\Scripts\activate

# 2. 安装项目及开发依赖
pip install -e ".[dev]"

# 3. 启动应用
python -m waterfall_viewer
```

### 一键独立打包（PyInstaller）
项目内置自动化打包脚本 `build.ps1`，会自动提取依赖库、libVLC 二进制运行库与 FFmpeg/FFprobe 组件：
```powershell
.\build.ps1
```
打包产物将自动生成于 `dist\WaterfallMediaViewer\` 目录。

---

## 🛡️ 隐私与开源协议

- **隐私承诺**：100% 本地运行，绝不收集、分析或向任何远端服务器上传您的媒体文件与隐私数据。
- **开源协议**：本项目基于 [MIT License](LICENSE) 协议开源。
