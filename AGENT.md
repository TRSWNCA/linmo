# AGENT.md

## Project

This project is a command-line tool for processing calligraphy copybook PDFs.

The goal is simple: take a scanned or digital PDF page, split the original copybook content into rows or columns, insert blank practice space between them, and export a new PDF or PNG that is easier to practice from.

No GUI is required.

Use uv as project mamager.

## Core Features

The tool should support:

1. Read a PDF file.
2. Select page ranges.
3. Split each page by rows or columns.
4. Insert blank space after each row or column.
5. Export the result as PDF or PNG.

Optional features:

1. Auto-rotate or deskew scanned pages.
2. Remove noisy backgrounds.
3. Extract dark ink strokes and place them on a clean background.

## Design Principles

Keep the tool simple.

Prefer a clear image-processing pipeline over complex AI methods. Most pages can be handled with traditional methods such as grayscale conversion, thresholding, projection, cropping, and image composition.

Do not try to make everything fully automatic at the beginning. Auto-detection should work when possible, but users should be able to provide parameters such as crop area, row count, column count, gap size, and rotation angle.

## Expected CLI Style

Example:

```bash
linmo input.pdf \
  --pages 1-5 \
  --mode row \
  --dpi 500 \
  --blank-ratio 1.0 \
  --out output.pdf
```

Column mode:

```bash
linmo input.pdf \
  --pages 3-8 \
  --mode col \
  --dpi 500 \
  --blank-ratio 1.2 \
  --out output.png
```

## Implementation Notes

A reasonable pipeline is:

1. Render selected PDF pages into high-resolution images.
2. Optionally crop page margins.
3. Optionally deskew the image.
4. Convert the image to grayscale.
5. Detect ink-heavy regions.
6. Split the page into rows or columns.
7. Add blank practice areas.
8. Export the final pages.

Useful libraries may include:

* PyMuPDF or pypdfium2 for PDF rendering.
* OpenCV or scikit-image for image processing.
* Pillow for image composition.
* img2pdf or PyMuPDF for PDF export.

## What Matters Most

The most important part is reliable row/column splitting.

The second most important part is keeping parameters easy to adjust.

The tool does not need OCR. It does not need to understand the characters. It only needs to detect layout and preserve the visual content well enough for calligraphy practice.

## Non-Goals

This project is not a general PDF editor.

It is not a handwriting recognition tool.

It is not meant to perfectly restore damaged scans.

It should focus on making existing calligraphy PDFs easier to use for practice.
