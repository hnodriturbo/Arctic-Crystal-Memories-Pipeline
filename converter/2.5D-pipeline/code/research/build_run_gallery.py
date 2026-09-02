"""
File: code/research/build_run_gallery.py
Purpose:
 - Build a consistent artifact gallery for every visual 2.5D research run.
 - Preserve full-resolution viewed images and generate a contact sheet plus HTML/Markdown indexes.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def parse_item(value: str) -> tuple[str, Path]:
    try:
        label, path = value.split("=", maxsplit=1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Gallery item must use LABEL=PATH") from error
    if not label.strip() or not path.strip():
        raise argparse.ArgumentTypeError("Gallery item must use non-empty LABEL=PATH")
    return label.strip(), Path(path)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--status", choices=["accepted", "candidate", "rejected"], required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--item", action="append", required=True, type=parse_item)
    parser.add_argument("--note", action="append", default=[])
    return parser.parse_args()


def safe_name(index: int, label: str, suffix: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "image"
    return f"{index:02d}-{slug}{suffix.lower()}"


def make_contact_sheet(title: str, status: str, items: list[tuple[str, Path]], output: Path) -> None:
    columns = 2
    cell_width = 660
    image_height = 500
    caption_height = 44
    header_height = 86
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, header_height + rows * (image_height + caption_height)), "#111722")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    caption_font = ImageFont.load_default(size=16)
    status_color = {"accepted": "#5EE58A", "candidate": "#FFD35A", "rejected": "#FF6B7A"}[status]
    draw.text((24, 18), title, fill="white", font=font)
    draw.text((24, 50), f"STATUS: {status.upper()}", fill=status_color, font=caption_font)

    for index, (label, path) in enumerate(items):
        row, column = divmod(index, columns)
        left = column * cell_width
        top = header_height + row * (image_height + caption_height)
        with Image.open(path) as source:
            preview = ImageOps.contain(source.convert("RGB"), (cell_width - 24, image_height - 24))
        x = left + (cell_width - preview.width) // 2
        y = top + (image_height - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((left + 16, top + image_height + 10), label, fill="white", font=caption_font)
    sheet.save(output, quality=94, optimize=True)


def main() -> None:
    args = parse_arguments()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    copied_items = []
    for index, (label, source_path) in enumerate(args.item, start=1):
        source_path = source_path.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        destination = output_dir / safe_name(index, label, source_path.suffix)
        shutil.copy2(source_path, destination)
        copied_items.append((label, destination))

    contact_sheet = output_dir / "00-contact-sheet.jpg"
    make_contact_sheet(args.title, args.status, copied_items, contact_sheet)
    notes_markdown = "\n".join(f"- {note}" for note in args.note) or "- No additional notes."
    image_markdown = "\n\n".join(
        f"## {label}\n\n![{label}]({path.name})" for label, path in copied_items
    )
    (output_dir / "README.md").write_text(
        f"# {args.title}\n\nStatus: **{args.status.upper()}**\n\n"
        f"![Contact sheet]({contact_sheet.name})\n\n## Notes\n\n{notes_markdown}\n\n{image_markdown}\n",
        encoding="utf-8",
    )

    cards = "\n".join(
        f'<figure><a href="{html.escape(path.name)}"><img src="{html.escape(path.name)}" '
        f'alt="{html.escape(label)}"></a><figcaption>{html.escape(label)}</figcaption></figure>'
        for label, path in copied_items
    )
    notes_html = "".join(f"<li>{html.escape(note)}</li>" for note in args.note)
    (output_dir / "index.html").write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
        "content=\"width=device-width,initial-scale=1\"><title>"
        + html.escape(args.title)
        + "</title><style>body{margin:0;background:#0b1018;color:#eef4ff;font:16px system-ui}"
        "header{padding:24px 32px;border-bottom:1px solid #283347}main{padding:24px;display:grid;"
        "grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:22px}figure{margin:0;background:#151d2a;"
        "border-radius:12px;overflow:hidden}img{display:block;width:100%;height:420px;object-fit:contain;"
        "background:#05070b}figcaption{padding:12px 16px}.status{font-weight:700}</style></head><body><header><h1>"
        + html.escape(args.title)
        + f'</h1><p class="status">Status: {html.escape(args.status.upper())}</p><ul>{notes_html}</ul>'
        f'</header><main><figure><a href="{contact_sheet.name}"><img src="{contact_sheet.name}" '
        f'alt="Contact sheet"></a><figcaption>Contact sheet</figcaption></figure>{cards}</main></body></html>',
        encoding="utf-8",
    )
    print(f"[gallery] {args.status}: {len(copied_items)} images -> {output_dir}")


if __name__ == "__main__":
    main()
