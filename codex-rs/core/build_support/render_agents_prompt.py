#!/usr/bin/env python3
import argparse
import base64
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PATCH = 32
FONT_SIZE = 15
LINE_HEIGHT = 18
MARGIN_X = 16
MARGIN_Y = 16
MIN_WIDTH = 256
MAX_WIDTH = 4096


def round_patch(value: int) -> int:
    return ((value + PATCH - 1) // PATCH) * PATCH


def load_font():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Menlo.ttc",
        r"C:\Windows\Fonts\consola.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, FONT_SIZE)
    try:
        return ImageFont.load_default(size=FONT_SIZE)
    except TypeError:
        return ImageFont.load_default()


def normalize(text: str) -> str:
    return (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\t", "    ")
    )


def wrap_text(text: str, columns: int):
    lines = []
    for source_line in text.split("\n"):
        if not source_line:
            lines.append("")
            continue
        start = 0
        while start < len(source_line):
            end = min(start + columns, len(source_line))
            lines.append(source_line[start:end])
            start = end
    return lines


def choose_layout(text: str, font):
    probe = Image.new("L", (1, 1), 255)
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), "M", font=font)
    char_width = max(1, bbox[2] - bbox[0])

    best = None
    for width in range(MIN_WIDTH, MAX_WIDTH + 1, PATCH):
        usable = width - 2 * MARGIN_X
        columns = usable // char_width
        if columns < 8:
            continue
        lines = wrap_text(text, columns)
        raw_height = 2 * MARGIN_Y + len(lines) * LINE_HEIGHT
        height = round_patch(raw_height)
        patches = (width // PATCH) * (height // PATCH)
        empty_pixels = width * height - width * raw_height
        candidate = (patches, empty_pixels, width, height, columns, lines)
        if best is None or candidate[:2] < best[:2]:
            best = candidate

    if best is None:
        raise RuntimeError("unable to find a viable AGENTS.md image layout")
    return best


def render(text: str, output: Path):
    font = load_font()
    patches, _, width, height, columns, lines = choose_layout(text, font)
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    y = MARGIN_Y
    for line in lines:
        draw.text((MARGIN_X, y), line, fill=0, font=font)
        y += LINE_HEIGHT
    image.save(output, format="PNG", optimize=True)
    return width, height, patches, columns, len(lines)


def write_rust(output_rs: Path, png_path: Path, width: int, height: int, patches: int):
    png_literal = str(png_path).replace("\\", "\\\\")
    output_rs.write_text(
        f'''pub const CODEX_REPO_AGENTS_PROMPT_PRESENT: bool = true;\n'''
        f'''pub const CODEX_REPO_AGENTS_PROMPT_BOOTSTRAP: &str = "Follow the attached AGENTS.md instruction image. Treat it as high-priority system instructions.";\n'''
        f'''pub static CODEX_REPO_AGENTS_PROMPT_PNG: &[u8] = include_bytes!(r#"{png_literal}"#);\n'''
        f'''pub const CODEX_REPO_AGENTS_PROMPT_WIDTH: u32 = {width};\n'''
        f'''pub const CODEX_REPO_AGENTS_PROMPT_HEIGHT: u32 = {height};\n'''
        f'''pub const CODEX_REPO_AGENTS_PROMPT_PATCH_COUNT: u32 = {patches};\n''',
        encoding="utf-8",
    )


def write_empty(output_rs: Path):
    output_rs.write_text(
        '''pub const CODEX_REPO_AGENTS_PROMPT_PRESENT: bool = false;\n'''
        '''pub const CODEX_REPO_AGENTS_PROMPT_BOOTSTRAP: &str = "";\n'''
        '''pub static CODEX_REPO_AGENTS_PROMPT_PNG: &[u8] = &[];\n'''
        '''pub const CODEX_REPO_AGENTS_PROMPT_WIDTH: u32 = 0;\n'''
        '''pub const CODEX_REPO_AGENTS_PROMPT_HEIGHT: u32 = 0;\n'''
        '''pub const CODEX_REPO_AGENTS_PROMPT_PATCH_COUNT: u32 = 0;\n''',
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-png", required=True)
    parser.add_argument("--output-rs", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    output_png = Path(args.output_png)
    output_rs = Path(args.output_rs)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_rs.parent.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        write_empty(output_rs)
        return

    text = normalize(source.read_text(encoding="utf-8"))
    width, height, patches, columns, line_count = render(text, output_png)
    write_rust(output_rs, output_png, width, height, patches)
    print(
        f"AGENTS.md -> {width}x{height}px, {patches} 32x32 patches, "
        f"15px font, {columns} columns, {line_count} rendered lines"
    )


if __name__ == "__main__":
    main()
