# Waterfall Media Viewer

一款面向 Windows 的本地图片与视频查看器，核心特色是以瀑布流方式浏览文件夹中的图片、动图和视频。

## 项目目标

- 简洁、快速、无账号、默认离线运行
- 支持单张图片查看和文件夹瀑布流浏览
- 图片支持平滑缩放、拖动及前后切换
- 视频支持封面、时长显示和基础播放控制
- 面向大量媒体文件进行异步加载、虚拟化和缓存优化

## 计划技术栈

- Python 3.12
- PySide6 / Qt 6
- Pillow
- VLC / python-vlc
- FFmpeg / ffprobe
- pytest
- PyInstaller，后期评估 Nuitka

## 当前状态

已完成图片查看、图片与视频混合瀑布流、两级缩略图缓存和基础视频播放。视频支持 FFprobe 元数据、FFmpeg 封面提取、时长标记，以及基于 libVLC 的播放、暂停、进度和音量控制。

## 本地开发

要求 Python 3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m waterfall_viewer
```

运行测试和静态检查：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## 文档

- [项目计划书](docs/项目计划书.md)
- [技术方案](docs/技术方案.md)
- [第一版功能范围](docs/第一版功能范围.md)

## 开发原则

1. 主线程只处理界面，不执行大图解码、目录扫描和视频探测。
2. 瀑布流必须采用虚拟化或等效的可见区域渲染机制。
3. 瀑布流只加载缩略图，不直接加载完整原图。
4. 缩略图同时使用有限内存缓存和本地磁盘缓存。
5. 先完成核心技术原型，再完善视觉样式和附加功能。

## 隐私

软件计划默认完全在本地运行，不上传用户的图片、视频、文件名或目录信息。
