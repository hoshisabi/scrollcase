#!/usr/bin/env python3
"""Build an adventure's Foundry asset folder under D:\\FoundryVTT\\Data\\img\\adventures.

    <CODE> <Title>/
        <PDF>                       (copied, not moved)
        <Map>.png / .jpg            (original, untouched)
        <Map>.webp                  (Foundry-ready copy)
        !Cover.webp                 (cover art; ! sorts it to the top of the file picker)

Run via uv (nothing to install):
    uv run --with pymupdf --with pillow python prep_adventure.py --pdf <pdf> [options]

Folder name:
    --name "<CODE> <Title>"   explicit (use this for any non-PS-DC-PUB line)
    otherwise parsed from a PS-DC-PUB filename:
        1533714-PS-DC-PUB-15_Abyss_-_Spider_Hunt_v1_0.pdf -> "PS-DC-PUB-15 Spider Hunt"

Maps (any combination, or none):
    --zip <zip>        repeatable. Images inside are extracted flat. For PS-DC-PUB the
                       multi-adventure zip is filtered to this number's subfolder
                       automatically; otherwise use --zip-match <regex> to filter, or take all.
                       Pass the clean/player zip, not a "(DM_Copy)" zip.
    --maps <image>     repeatable. Loose image files (maps, VTT token assets).

Cover (--cover):
    pdf      render the PDF's front page (default; needs PyMuPDF)
    <path>   use a local image (e.g. one Dan saved from the DM's Guild product page)
    none     skip
The front page isn't always the cover. Look at the result and confirm it.

Idempotent (safe to re-run); --dry-run previews.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

ADVENTURES_ROOT = Path(r"D:\FoundryVTT\Data\img\adventures")
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_pub_name(pdf: Path):
    """Return (number, plane, title) from a PS-DC-PUB filename, or None."""
    m = re.search(r"PS-DC-PUB-(\d+)_(.+?)_-_(.+?)_v\d", pdf.stem, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1), m.group(2).replace("_", " ").strip(), m.group(3).replace("_", " ").strip()


def zip_members(zf: zipfile.ZipFile, pattern: re.Pattern | None):
    for name in zf.namelist():
        if name.endswith("/") or Path(name).suffix.lower() not in IMG_EXTS:
            continue
        if pattern is None or pattern.search(name):
            yield name


def to_webp(src: Path, quality: int) -> Path:
    dst = src.with_suffix(".webp")
    if dst == src:
        return src
    im = Image.open(src)
    # Keep alpha for PNGs (transparent margins, token assets); flatten otherwise.
    im = im.convert("RGBA") if src.suffix.lower() == ".png" else im.convert("RGB")
    im.save(dst, "WEBP", quality=quality, method=6)
    return dst


def cover_from_pdf(pdf: Path, dst: Path, quality: int, dpi: int = 150) -> Path:
    import io
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        zoom = dpi / 72.0
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB").save(dst, "WEBP", quality=quality, method=6)
    finally:
        doc.close()
    return dst


def cover_from_image(src: Path, dst: Path, quality: int) -> Path:
    im = Image.open(src)
    im = im.convert("RGBA") if src.suffix.lower() == ".png" else im.convert("RGB")
    im.save(dst, "WEBP", quality=quality, method=6)
    return dst


def report_map(out: Path, webp: Path) -> None:
    with Image.open(out) as im:
        w, h = im.size
    print(f"map  : {out.name}  ({out.stat().st_size // 1024} KB)  ->  "
          f"{webp.name}  ({webp.stat().st_size // 1024} KB, {w}x{h})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True, type=Path, help="Adventure PDF")
    ap.add_argument("--name", help='Folder name "<CODE> <Title>" (required unless PS-DC-PUB filename)')
    ap.add_argument("--zip", action="append", type=Path, default=[], help="Maps zip (repeatable)")
    ap.add_argument("--zip-match", help="Regex filter on zip member paths")
    ap.add_argument("--maps", action="append", type=Path, default=[], help="Loose map/token image (repeatable)")
    ap.add_argument("--quality", type=int, default=80, help="WebP quality 1-100 (default 80)")
    ap.add_argument("--root", type=Path, default=ADVENTURES_ROOT, help="Adventures root folder")
    ap.add_argument("--cover", default="pdf", help="'pdf' (default), a local image path, or 'none'")
    ap.add_argument("--dry-run", action="store_true", help="Report actions without writing")
    args = ap.parse_args()

    for p in [args.pdf, *args.zip, *args.maps]:
        if not p.is_file():
            print(f"ERROR: not found: {p}", file=sys.stderr)
            return 1

    pub = parse_pub_name(args.pdf)
    if args.name:
        folder = args.name
    elif pub:
        folder = f"PS-DC-PUB-{pub[0]} {pub[2]}"
    else:
        print('ERROR: not a PS-DC-PUB filename; pass --name "<CODE> <Title>" '
              "(code as printed in the PDF, title as printed)", file=sys.stderr)
        return 1

    if args.zip_match:
        pattern = re.compile(args.zip_match, re.IGNORECASE)
    elif pub:
        pattern = re.compile(rf"(^|/)PS-DC-PUB-0*{int(pub[0])}[ _].*?/", re.IGNORECASE)
    else:
        pattern = None

    dest = args.root / folder
    print(f"Folder    : {dest}")

    if args.dry_run:
        for z in args.zip:
            with zipfile.ZipFile(z) as zf:
                for name in zip_members(zf, pattern):
                    print(f"[dry-run] extract + webp: {name}  (from {z.name})")
        for m in args.maps:
            print(f"[dry-run] copy + webp: {m.name}")
        print(f"[dry-run] copy PDF: {args.pdf.name}")
        print(f"[dry-run] cover: {args.cover}")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    found = 0
    for z in args.zip:
        with zipfile.ZipFile(z) as zf:
            for name in zip_members(zf, pattern):
                out = dest / Path(name).name
                with zf.open(name) as src, open(out, "wb") as f:
                    shutil.copyfileobj(src, f)
                report_map(out, to_webp(out, args.quality))
                found += 1
    for m in args.maps:
        out = dest / m.name
        if m.resolve() != out.resolve():
            shutil.copy2(m, out)
        report_map(out, to_webp(out, args.quality))
        found += 1
    if (args.zip or args.maps) and not found:
        print("WARNING: no map images matched (check --zip-match)", file=sys.stderr)

    pdf_out = dest / args.pdf.name
    shutil.copy2(args.pdf, pdf_out)
    print(f"pdf  : {pdf_out.name}  ({pdf_out.stat().st_size // 1024} KB)")

    cover_out = dest / "!Cover.webp"
    if args.cover == "none":
        print("cover: skipped (--cover none)")
    else:
        if args.cover == "pdf":
            cover_from_pdf(args.pdf, cover_out, args.quality)
            src = "PDF front page"
        else:
            cover_from_image(Path(args.cover), cover_out, args.quality)
            src = Path(args.cover).name
        with Image.open(cover_out) as im:
            w, h = im.size
        print(f"cover: !Cover.webp from {src} ({cover_out.stat().st_size // 1024} KB, {w}x{h})"
              " -- CONFIRM it's the real cover")

    print("\nFolder contents:")
    for p in sorted(dest.iterdir()):
        print(f"  {p.name}  ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
