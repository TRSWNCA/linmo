# Linmo

Linmo 是一个本地书法临摹制帖工具，用来把 PDF 或图片书帖转换成更适合练习的临摹页。

它可以识别书帖中的横排行或竖排栏，提取字迹和线条，插入练习空白区，并导出为 PDF 或 PNG。

## 核心功能

- 导入 PDF、单张图片或图片目录。
- 自动识别横排行或竖排栏。
- 为原帖内容生成对应练习区。
- 支持保留原图，也支持去除原背景后重新绘制字迹。
- 支持自定义字色、前景阈值、背景图。
- 支持 PDF 和 PNG 导出；多页 PNG 会拆成多张图片。
- 提供本地 GUI：藏帖、练帖阁、封面管理、页面预览、制作队列、导出预览、预设和设置。
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
- 右键封面可编辑名称、作者和展示封面。
- 在页面预览中选择页面后，可加入制作队列。

### 生成帖

- 顶部调整当前页面的生成参数。
- 中间查看原图和导出预览。
- 原图和预览图支持鼠标滚轮缩放、拖动查看位置、双击复位。
- 底部显示制作队列缩略图。
- 缩略图可拖拽排序，导出时按当前顺序生成 PDF 或 PNG。
- 点击“导出”时会确认名称和格式，默认名称使用“卷一、卷二……”。
- 导出的 PDF 会保存到练帖阁。
- 制作队列是一次性队列，每次打开应用时默认为空。

### 练帖阁

- 练帖阁以封面墙展示已生成的 PDF。
- 每个缩略图右下角有同步按钮，可按单帖通过 WebDAV 同步。
- 远端按每帖一个目录组织，包含 `original.pdf` 和 `results/*.pdf`。
- 若远端已有同名 `original.pdf`，同步时以远端文件覆盖本地文件。

### 预设

用于保存常用导出配置，例如背景图、字色、前景阈值、默认模式等。

### 设置

用于配置本地数据目录、默认 DPI、默认导出目录和 WebDAV 信息。

## CLI 使用

除了 GUI，Linmo 也提供命令行工具。

竖排书帖：

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --mode col \
  --blank-ratio 1.0 \
  --dpi 300 \
  --out outputs/page41-copy.pdf
```

横排书帖：

```bash
uv run linmo "resources/吴玉生行楷 优美诗歌.pdf" \
  --pages 12 \
  --mode row \
  --blank-ratio 1.0 \
  --dpi 300 \
  --out outputs/wuyusheng-page12-copy.pdf
```

图片书帖：

```bash
uv run linmo resources/3.jpg \
  --pages 1 \
  --mode col \
  --column-detection ink \
  --foreground-threshold 35 \
  --out outputs/3-auto-textured.pdf
```

去除原背景并使用背景图：

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --mode col \
  --background-image /home/cyc/Downloads/huaban-2932812013.jpg \
  --ink-color '#202020' \
  --out outputs/page41-copy-textured.pdf
```

常用参数：

- `--pages`：页码范围，例如 `41`、`1-3`、`1,3,5`。
- `--mode`：`row` 或 `col`。
- `--column-detection`：`gray` 或 `ink`。
- `--blank-ratio`：练习区相对原行/栏的比例。
- `--foreground-threshold`：前景提取阈值。
- `--ink-color`：重绘字迹颜色。
- `--background-image`：输出背景图。
- `--rows` / `--columns`：手动指定行数或列数；默认可不传。
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

## 数据与隐私

Linmo 默认把导入的书帖、练帖阁 PDF、缩略图、预设、导出记录和设置保存在：

```text
~/.local/share/linmo
```

WebDAV 同步仅在用户配置并点击练帖阁单帖同步按钮时执行。WebDAV 地址、用户名和应用密码保存在本机设置中。

## License

Linmo 使用 MIT License。详见 [LICENSE](LICENSE)。
