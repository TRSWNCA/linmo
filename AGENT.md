# AGENT.md

## 项目定位

Linmo 是一个本地书法临摹制帖工具，不再只是 CLI。当前项目由两部分组成：

- `src/linmo/`：核心图像处理和 CLI。
- `src/linmo_app/` + `frontend/`：React + Fluent UI + pywebview 本地 GUI。

目标是把 PDF 或图片书帖转换成可练习的临摹页面：本地识别正文和单字位置，过滤背景，把范字放入田字格/米字格，并导出 A4 PDF 或 PNG。

## 重要约定

- 项目名和命令是 `linmo`，不是 `linmu`。
- 使用 `uv` 管理 Python 依赖。
- 前端使用 Vite + React + TypeScript + Fluent UI。
- GUI 使用 `pywebview`，Linux 默认走 Qt 后端。
- 回答和提交说明尽量使用中文，保持准确、结构化，避免过度夸赞。

## 当前功能状态

CLI：

- 支持 PDF 和图片输入。
- 使用本地 PP-OCRv6 自动识别横排、竖排正文和单字位置。
- 支持田字格、米字格以及格宽、页边距设置。
- 单字范围内过滤背景，保留字形灰度纹理。
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
- 可导出队列为 PDF 或 PNG，并记录导出页数；多页 PNG 拆成多张图片。
- 固定按 A4 纵向自动换行和分页。
- 练帖阁保存已生成的 PDF，使用封面墙展示。
- 练帖阁单帖可通过 WebDAV 同步，远端每帖一个目录，包含 `original.pdf` 和 `results/*.pdf`。
- 预设和设置页面已有 MVP 实现。

## 目录结构

```text
src/linmo/
  cli.py              CLI 入口
  processing.py       可复用处理函数
  glyph_pipeline.py   OCR 结果规范化、单字提取、田/米字格 A4 排版
  image_pipeline.py   PDF 渲染和旧图像处理兼容函数
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
  --grid-style tian \
  --cell-size-mm 15 \
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
  - 顶部只保留格子类型、格宽和边距等有效参数。
  - 提供识别校对界面，低置信度字符必须清晰标示。
  - 中间查看区默认填满宽度，默认位置从顶部开始。
  - 查看区支持鼠标滚轮缩放、拖动平移、双击复位。
  - 底部缩略图队列支持拖拽排序。

## 图像处理原则

- 页面结构和单字位置以本地 OCR 为主，不再依赖页面颜色、灰底或红线切分。
- 默认只选择主要书法正文，标题、页眉页脚和页码由几何与字号聚类排除，并允许人工校正。
- 去背景只在 OCR 单字框内进行，保留笔锋、浓淡和抗锯齿，不保留纸张及格线背景。
- 横排和竖排均规范化为横向练习行；正文标点保留但不占独立练习格。
- OCR 结果必须持久化并带模型/分析版本，源文件变化时自动失效。

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
- 不做通用 PDF 编辑器。
- 不训练自有像素级笔画分割模型；当前使用 OCR 框内局部背景估计。
- 不假设书法 OCR 一次完全正确，识别校对是正式工作流的一部分。
