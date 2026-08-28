# 🌊 CascadePic (流瀑看图)

<div align="center">

<img src="docs/app_logo.png" alt="CascadePic Logo" width="128" height="128"/>

### **流瀑看图 • 专为 Windows 打造的极速现代化媒体画廊**
*A high-performance, minimalist Windows waterfall image & video viewer.*

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D4?logo=windows&logoColor=white)](https://github.com/BEIJUUUUU/CascadePic)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Qt](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt%206-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Release](https://img.shields.io/github/v/release/BEIJUUUUU/CascadePic?color=orange&logo=github)](https://github.com/BEIJUUUUU/CascadePic/releases)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](#)

[✨ 核心特性](#-核心特性) • [📸 界面预览](#-界面预览) • [📥 下载与安装](#-下载与安装) • [⌨️ 快捷键指南](#️-快捷键指南) • [🛠️ 本地构建](#️-本地构建)

</div>

---

## ✨ 核心特性

- ⚡ **超流畅虚拟化瀑布流**：面对上万张图片与视频目录瞬间加载，仅按需动态渲染可见卡片，内存占用始终极低。
- 🖼️ **全格式无缝支持**：
  - **静态图像**：JPG, JPEG, JFIF, PNG, WebP, BMP, ICO, TIFF...
  - **动态动图**：GIF 逐帧原速流畅播放，支持逐帧查看。
  - **高清视频**：MP4, MKV, WebM, MOV, AVI, WMV, M4V（内置完整 libVLC 解码器与硬件加速）。
- 🔍 **专业看图体验**：
  - 高质量平滑抗锯齿缩放与智能 100% 像素吸附对齐（告别模糊与锯齿）。
  - 类似 Honeyview 的高效手势：**鼠标右键 + 滚轮平滑缩放**、滚轮快速切图。
  - 界面两侧智能浮动导航箭头，鼠标轻点轻松切换。
- 🎬 **轻量一体化视频播放**：
  - 瀑布流中实时显示视频时长徽章与提取的高清首帧封面。
  - 单击即可无缝播放，支持 JumpSlider 进度条即点即跳、音量控制、滚轮直接切集。
- 🎨 **现代化 Windows 11 Fluent 视觉**：
  - 原生级精雕细琢的浅色 Modern UI、精致微投影、圆角卡片。
  - 极简图标化工具栏，纯净无广告，100% 离线保护隐私。

---

## 📸 界面预览

<div align="center">
  <img src="docs/ui-preview-fluent.png" alt="CascadePic 流瀑看图界面预览" width="880"/>
</div>

---

## 📥 下载与安装

### 方式一：下载免安装便携版（推荐）
前往 [GitHub Releases 页面](https://github.com/BEIJUUUUU/CascadePic/releases) 下载最新的 `CascadePic-v1.0.0-windows-x64.zip`。  
解压后直接双击 **`CascadePic.exe`** 即可使用，无需安装 Python 或任何额外运行库。

### 方式二：源码双击运行
如果你已克隆本项目源码：
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
打包产物将自动生成于 `dist\CascadePic\` 目录。

---

## 🛡️ 隐私与开源协议

- **隐私承诺**：100% 本地运行，绝不收集、分析或向任何远端服务器上传您的媒体文件与隐私数据。
- **开源协议**：本项目基于 [MIT License](LICENSE) 协议开源。
