# Linmo

Linmo is a command-line tool for creating calligraphy practice pages from copybook PDFs.

First-version target:

- read a PDF page;
- auto-detect the main rows or vertical copybook columns;
- crop away page headers and side labels;
- insert a white blank practice strip next to each source row or column;
- export PNG or PDF.

## Usage

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --mode col \
  --blank-style white \
  --blank-ratio 1.0 \
  --dpi 300 \
  --out outputs/page41-copy.pdf
```

PNG output is also supported:

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --mode col \
  --out outputs/page41-copy.png
```

Horizontal row mode is available for ruled pages:

```bash
uv run linmo "resources/吴玉生行楷 优美诗歌.pdf" \
  --pages 12 \
  --mode row \
  --blank-style white \
  --blank-ratio 1.0 \
  --dpi 300 \
  --out outputs/wuyusheng-page12-copy.pdf
```

To remove the original page background and redraw extracted text/lines on a
texture:

```bash
uv run linmo resources/硬笔行书红楼梦诗词.pdf \
  --pages 41 \
  --mode col \
  --background-image /home/cyc/Downloads/huaban-2932812013.jpg \
  --ink-color '#202020' \
  --out outputs/page41-copy-textured.pdf
```

Passing `--background-image` automatically enables foreground extraction. Use
`--foreground-threshold` when a scan is too faint or too noisy.

`--rows` and `--columns` are optional. Omit them for auto-detection; provide
them only when a page needs manual correction.

For old vertical JPG scans without gray column panels, use ink-based column
detection:

```bash
uv run linmo resources/3.jpg \
  --pages 1 \
  --mode col \
  --column-detection ink \
  --background-image /home/cyc/Downloads/huaban-2932812013.jpg \
  --ink-color '#000000' \
  --foreground-threshold 35 \
  --out outputs/3-auto-textured.pdf
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## GUI

Install Python and frontend dependencies, build the React app, then launch the
local desktop GUI:

```bash
uv sync
cd frontend
npm install
npm run build
cd ..
uv run linmo-app
```

The GUI stores imported copybooks, thumbnails, presets, queue state, and export
records under `~/.local/share/linmo` by default. During development you can use
another location:

```bash
LINMO_APP_DATA=/tmp/linmo-app uv run linmo-app
```

pywebview debugging is disabled by default. Enable it only when you need
Chromium remote inspection:

```bash
LINMO_WEBVIEW_DEBUG=1 uv run linmo-app
```

On Linux, Linmo starts pywebview with the Qt backend by default. The project
installs `PySide6` and `qtpy` through `uv sync`, so GTK/PyGObject is not
required for the default path. To force another pywebview backend:

```bash
LINMO_WEBVIEW_GUI=gtk uv run linmo-app
```

On Manjaro/Arch, Qt may also require the system XCB cursor library. If startup
fails with `Could not load the Qt platform plugin "xcb"` or mentions
`xcb-cursor0`, install:

```bash
sudo pacman -S xcb-util-cursor
```

For X11 window managers such as i3wm, Linmo disables Qt WebEngine GPU
composition by default to avoid Chromium `dma_buf` texture errors such as
`Compositor returned null texture`. It keeps Qt's XCB OpenGL integration
enabled, because Qt WebEngine still needs an OpenGL context even when Chromium
GPU compositing is disabled. To opt back into hardware acceleration:

```bash
LINMO_WEBVIEW_ACCELERATION=1 uv run linmo-app
```
