# Linmo

Linmo 是一个本地书法临摹制帖工具，用来把 PDF 或图片书帖转换成更适合练习的临摹页。

它使用本地 OCR 识别书帖正文和每个字的位置，过滤纸张背景后把原字放入田字格或米字格，并为每排范字生成一排空练习格。

## 核心功能

- 导入 PDF、单张图片或图片目录。
- 使用 PP-OCRv6 在本机识别横排、竖排正文及单字位置。
- 提供识别选字，可在单页中拖框或点选单字，并按选择顺序生成练字页。
- 在单字范围内估计并过滤背景，保留原字的灰度、笔锋和边缘层次。
- 生成 A4 田字格或米字格，每排范字下方对应一排空格。
- 默认格宽 15 mm，可调整格宽和页面边距。
- 支持 PDF 和 PNG 导出；多页 PNG 会拆成多张图片。
- 提供本地 GUI：藏帖、练帖阁、封面管理、页面预览、单页制帖、导出预览、预设和设置。
- 所有数据默认保存在本机；练帖阁可按单帖通过 WebDAV 同步。

## 安装

当前项目暂未提供打包好的安装器，需要从源码运行。

需要：

- Python 3.12+
- uv
- Node.js / npm

安装 Python 依赖：

```bash
uv sync
```

`uv sync` 会安装本地 OCR 运行时。OCR 模型在第一次识别时下载到 Linmo 数据目录的 `models/`，以后无需联网；书帖图片不会上传。

安装并构建前端：

```bash
cd frontend
npm install
npm run build
cd ..
```

## 启动 GUI

```bash
uv run linmo-app
```

默认窗口大小为 `1480x960`，最小大小为 `980x640`。

默认数据目录：

```text
~/.local/share/linmo
```

可以通过环境变量指定其它数据目录：

```bash
LINMO_APP_DATA=/tmp/linmo-app uv run linmo-app
```

## GUI 使用方式

### 首页

显示应用图标、已收藏书帖数量和已导出页数。

### 藏帖阁

- 点击“导入”导入 PDF、图片或图片目录。
- 导入文件会复制到 Linmo 的本地应用库。
- 书帖以封面墙展示。
- 双击封面进入该帖所有页面的缩略图预览。
- 双击单页进入页级裁切预览，可先裁上下左右四边，再进入制帖。
- 右键封面可编辑名称、作者、展示封面和四边预裁切；预裁切会先裁掉页边，再进入识别和生成流程。

### 生成帖

- 顶部选择田字格/米字格并调整格宽和页边距。
- 点击“识别选字”后，可在单页原图上点选单字或拖框选字；拖框起点所在字为首字，并自动判断横竖顺序。
- 选中的字会直接在页面字框内显示可编辑输入框，可原位改字和删除。
- 中间查看导出预览；识别原图只在“识别选字”步骤中使用。
- 预览图支持鼠标滚轮缩放、拖动查看位置、双击复位。
- 点击“导出”时会确认名称和格式，默认名称使用“卷一、卷二……”。
- 一个来源页可自动分页为多张 A4 页面，预览区可逐页切换。
- 导出的 PDF 会保存到练帖阁。

### 练帖阁

- 练帖阁以封面墙展示已生成的 PDF。
- 每个缩略图右下角有同步按钮，可按单帖通过 WebDAV 同步。
- 远端按每帖一个目录组织，包含 `original.pdf` 和 `results/*.pdf`。
- 若远端已有同名 `original.pdf`，同步时以远端文件覆盖本地文件。

### 预设

用于保存常用格子类型、格宽和页面边距。

### 设置

用于配置本地数据目录、默认 DPI、默认导出目录和 WebDAV 信息。

## CLI 使用

除了 GUI，Linmo 也提供命令行工具。

田字格：

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --grid-style tian \
  --cell-size-mm 15 \
  --dpi 300 \
  --out outputs/page41-copy.pdf
```

米字格：

```bash
uv run linmo "resources/吴玉生行楷 优美诗歌.pdf" \
  --pages 12 \
  --grid-style mi \
  --cell-size-mm 15 \
  --margin-mm 15 \
  --dpi 300 \
  --out outputs/wuyusheng-page12-copy.pdf
```

图片书帖：

```bash
uv run linmo resources/3.jpg \
  --pages 1 \
  --grid-style tian \
  --out outputs/3-practice.pdf
```

常用参数：

- `--pages`：页码范围，例如 `41`、`1-3`、`1,3,5`。
- `--grid-style`：`tian`（田字格）或 `mi`（米字格）。
- `--cell-size-mm`：格子边长，范围 10–30 mm，默认 15 mm。
- `--margin-mm`：A4 页面边距，范围 5–30 mm，默认 15 mm。
- `--dpi`：PDF 渲染与输出 DPI，默认 300。
- `--out`：输出 `.pdf` 或 `.png`。

## Linux 运行说明

Linux 下 GUI 默认使用 Qt 后端。项目会通过 Python 依赖安装 `PySide6`、`qtpy` 和 `pywebview`。

Manjaro / Arch 如果启动时报 `Could not load the Qt platform plugin "xcb"` 或 `xcb-cursor0`，安装：

```bash
sudo pacman -S xcb-util-cursor
```

X11 / i3wm 下默认禁用 Chromium GPU 合成，以规避 `dma_buf` 纹理问题。需要强制启用硬件加速时：

```bash
LINMO_WEBVIEW_ACCELERATION=1 uv run linmo-app
```

pywebview 调试默认关闭。需要 Chromium 远程调试时：

```bash
LINMO_WEBVIEW_DEBUG=1 uv run linmo-app
```

## 运行日志与 OCR 排查

左侧导航的“运行日志”会显示前端和后端的 warning/error、OCR 当前阶段及完整异常堆栈。日志可以复制，也会持续写入数据目录下的：

```text
logs/linmo.log
```

日志面板顶部会显示实际文件路径。默认数据目录是 `~/.local/share/linmo`；如果设置了 `LINMO_APP_DATA`，则使用该目录。Windows 上遇到 PaddleOCR 未加载时，重点查看 `backend.ocr` 的 error 项，其中会保留缺失 DLL、Python 包导入失败或模型初始化失败的原始异常。

OCR 过程会依次显示“正在读取页面”“正在初始化模型”“正在识别”。命中已有缓存时显示“正在读取识别缓存”。

## 数据与隐私

Linmo 默认把导入的书帖、练帖阁 PDF、缩略图、预设、导出记录和设置保存在：

```text
~/.local/share/linmo
```

页面 OCR 结果和人工校对会保存在本地数据库中；模型文件保存在 `models/`。修改源文件或分析版本升级后，缓存会自动失效。

WebDAV 同步仅在用户配置并点击练帖阁单帖同步按钮时执行。WebDAV 地址、用户名和应用密码保存在本机设置中。

## License

Linmo 使用 MIT License。详见 [LICENSE](LICENSE)。
