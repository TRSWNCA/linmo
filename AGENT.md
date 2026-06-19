# AGENT.md

## 项目定位

Linmo 是一个本地书法临摹制帖工具，不再只是 CLI。当前项目由两部分组成：

- `src/linmo/`：核心图像处理和 CLI。
- `src/linmo_app/` + `frontend/`：React + Fluent UI + pywebview 本地 GUI。

目标是把 PDF 或图片书帖转换成可练习的临摹页面：识别原帖行/栏，提取字迹/线条，插入练习区，导出 PDF 或 PNG。

## 重要约定

- 项目名和命令是 `linmo`，不是 `linmu`。
- 使用 `uv` 管理 Python 依赖。
- 前端使用 Vite + React + TypeScript + Fluent UI。
- GUI 使用 `pywebview`，Linux 默认走 Qt 后端。
- 回答和提交说明尽量使用中文，保持准确、结构化，避免过度夸赞。

## 当前功能状态

CLI：

- 支持 PDF 和图片输入。
- 支持 `row` 横排行模式和 `col` 竖排栏模式。
- 支持自动检测行/列，也支持手动指定 `--rows` / `--columns`。
- 支持前景提取，把字迹/线条统一重绘到纯色或背景图上。
- 支持输出 PDF 或 PNG。

GUI：

- 首页显示应用图标、藏帖数量、已导出页数。
- 藏帖阁以封面墙展示书帖。
- 导入时复制文件到应用库，并显示中央阻塞提示。
- 右键书帖封面可编辑名称、作者、展示封面。
- 双击书帖封面进入所有页缩略图预览。
- 预览页可选择页面并加入制作队列。
- 制作队列每次启动应用时清空，属于一次会话内的临时队列。
- 生成帖页面顶部是参数栏，中间是原图/预览图，底部是可拖拽排序的缩略图队列。
- 原图和预览图默认填满宽度，可用鼠标滚轮缩放、拖动查看位置、双击复位。
- 可导出队列为 PDF，并记录导出页数。
- 练帖阁保存已生成的 PDF，使用封面墙展示。
- 练帖阁单帖可通过 WebDAV 同步，远端每帖一个目录，包含 `original.pdf` 和 `results/*.pdf`。
- 预设和设置页面已有 MVP 实现。

## 目录结构

```text
src/linmo/
  cli.py              CLI 入口
  processing.py       可复用处理函数
  image_pipeline.py   核心图像处理：检测、裁切、前景提取、排版组合
  pages.py            页码解析

src/linmo_app/
  launcher.py         pywebview 启动器
  api.py              暴露给前端的本地 API
  repository.py       SQLite schema、迁移和 CRUD
  services.py         导入、缩略图、预览、导出服务
  paths.py            数据目录

frontend/
  src/App.tsx         React 主界面
  src/styles.css      样式
  src/types.ts        pywebview API 类型
  public/             favicon 和应用图标
```

## 数据目录

正式默认数据目录：

```text
~/.local/share/linmo
```

开发可用：

```bash
LINMO_APP_DATA=/tmp/linmo-app uv run linmo-app
```

导入文件必须复制到应用库，不要只保存原始路径。大致结构：

```text
library/{copybook_id}/source.pdf
library/{copybook_id}/pages/{page_no}.{ext}
cache/thumbs/{page_id}.jpg
cache/previews/*.jpg
exports/{timestamp}-linmo.pdf
generated/{post_id}/original.pdf
generated/{post_id}/results/*.pdf
linmo.sqlite3
```

## 开发命令

安装 Python 依赖：

```bash
uv sync
```

安装并构建前端：

```bash
cd frontend
npm install
npm run build
cd ..
```

启动 GUI：

```bash
uv run linmo-app
```

运行 CLI 示例：

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --mode col \
  --out outputs/page41-copy.pdf
```

后端测试：

```bash
.venv/bin/python -m unittest discover -s tests
```

前端构建验证：

```bash
cd frontend
npm run build
```

## GUI 设计约定

- 使用 Fluent UI 组件，避免回到手写原生控件风格，除非 Fluent 没有合适控件。
- 左侧导航固定在整个 APP 左侧，设置入口在导航栏最底部。
- 藏帖阁保持简约：只展示封面、名称、作者；不要常驻展示导入路径或元数据表单。
- 右键封面编辑元数据；元数据至少包括展示封面、作者、名称。
- 导入过程中必须显示中央阻塞提示，避免用户切换或重复操作。
- 生成帖页面：
  - 顶部只放操作参数，不放页面标题。
  - 参数栏保持两行布局。
  - 字色用取色器，不让用户手填颜色字符串。
  - 中间查看区默认填满宽度，默认位置从顶部开始。
  - 查看区支持鼠标滚轮缩放、拖动平移、双击复位。
  - 底部缩略图队列支持拖拽排序。

## 图像处理原则

- 首选确定性的传统图像处理：灰度、阈值、投影、区域检测、裁切、组合。
- 不做 OCR，不识别字符语义。
- 前景提取后可以统一重绘为纯黑或用户指定颜色。
- 不需要保留原始背景色；GUI/CLI 都应支持换成统一背景或背景图。
- 横版书帖的标题和作者如果是手写内容，应尽量作为帖的一部分保留。
- 自动检测优先，`rows/columns` 只作为纠错参数，不应要求普通用户手动指定。

## 后端/API 约定

- 前端只通过 `window.pywebview.api` 调用后端。
- 新功能优先放到 `LinmoServices`，再由 `LinmoApi` 暴露给前端。
- SQLite schema 变更要在 `Repository.init_schema()` 中加入兼容已有库的迁移逻辑。
- 需要展示图片给前端时，后端返回 data URL。
- 制作队列启动时清空：`LinmoApi.__init__()` 会调用 `clear_queue_items()`。
- WebDAV 凭据当前保存在本机 settings；同步以单帖为单位，远端同名 `original.pdf` 覆盖本地。

## Linux/pywebview 注意事项

- Linux 默认 GUI 后端是 Qt。
- `PySide6` 和 `qtpy` 是项目依赖。
- Manjaro/Arch 如果缺 XCB cursor 库，用户可能需要：

```bash
sudo pacman -S xcb-util-cursor
```

- 默认禁用 Chromium GPU 合成以规避 X11/i3wm 下的 `dma_buf` 问题。
- 默认关闭 pywebview debug，避免每次弹出 `Inspectable pages`。
- 需要调试时使用：

```bash
LINMO_WEBVIEW_DEBUG=1 uv run linmo-app
```

## 非目标

- 不做账号系统、插件系统或后台全库自动同步。
- 不做 OCR 或字符识别。
- 不做通用 PDF 编辑器。
- 不追求一次性完美处理所有版式；优先保证已有样例和常见书帖路径稳定。
