"""PDF text/image pulls and battle-map grid measurement for Foundry prep.

A small toolbox, not a pipeline: each command gets Dan ~95% there and a human
eyeball finishes (especially grids). Run via uv so nothing needs installing:

    uv run --with pymupdf --with pillow --with numpy python pdf_assets.py text <pdf> [<out.txt>]
    uv run --with pymupdf --with pillow --with numpy python pdf_assets.py images <pdf> <scratch_dir>
    uv run --with pymupdf --with pillow --with numpy python pdf_assets.py grid [--preview <dir>] <image> [...]

text:   page-delimited text via PyMuPDF (pypdf splits DMsGuild PDFs one word per line).
        Prints to stdout unless an output file is given.
images: every embedded image >= 400 px on a side -> <scratch_dir>/p<page>_img<n>.<ext>.
        Use this only when a map isn't supplied as a separate download. Write to a
        scratch dir, not the Foundry folder; rename/convert the keepers afterwards.
grid:   estimates grid size and offset per axis independently (X and Y can differ)
        from drawn grid lines, via high-pass + autocorrelation. --preview writes
        <name>.grid-preview.png with the estimate overlaid in red, to check by eye.
"""

import sys
from pathlib import Path


def text(pdf: Path, out: Path | None) -> None:
    import pymupdf

    doc = pymupdf.open(pdf)
    body = "\n".join(f"=== PAGE {i + 1} ===\n{p.get_text()}" for i, p in enumerate(doc))
    if out:
        out.write_text(body, encoding="utf-8")
        print(f"{out} ({len(doc)} pages)")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(body)


def images(pdf: Path, out: Path) -> None:
    import pymupdf

    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    for pno, page in enumerate(doc, start=1):
        for n, img in enumerate(page.get_images(full=True), start=1):
            info = doc.extract_image(img[0])
            if min(info["width"], info["height"]) < 400:
                continue  # logos, dividers, trade dress
            name = f"p{pno}_img{n}.{info['ext']}"
            (out / name).write_bytes(info["image"])
            print(f"page {pno}: {out / name}  {info['width']}x{info['height']}")


def _period(profile):
    """Grid period along one axis. Returns (period_px, offset_px, strength 0-1).

    Median line-spacing is fooled by map features (walls, stalls, streets);
    autocorrelation keys on what repeats.
    """
    import numpy as np

    # High-pass: darkness relative to a 15 px neighbourhood, so thin grid lines
    # stand out and broad shading/painted texture drops away.
    local = np.convolve(profile, np.ones(15) / 15, mode="same")
    sig = np.clip(local - profile, 0, None)
    sig = sig - sig.mean()
    n = len(sig)
    ac = np.correlate(sig, sig, mode="full")[n - 1:]
    ac = ac / ac[0]
    lo, hi = 20, min(300, n // 3)
    lags = np.arange(lo, hi)
    vals = ac[lo:hi]
    best = vals.max()
    # First local peak near the best: avoids picking 2x/3x harmonics.
    for lag, v in zip(lags, vals):
        if v >= 0.8 * best and ac[lag] >= ac[lag - 1] and ac[lag] >= ac[lag + 1]:
            period = int(lag)
            break
    else:
        period = int(lags[vals.argmax()])
    # Refine to sub-pixel using the peak ~k periods out.
    k = max(1, (n // period) - 1)
    near = [i for i in range(k * period - k, k * period + k + 1) if i < n]
    period_f = max(near, key=lambda i: ac[i]) / k
    offset = max(range(period), key=lambda o: sig[o::period].sum())
    return period_f, offset, float(best)


def grid(paths: list[Path], preview: Path | None) -> None:
    import numpy as np
    from PIL import Image, ImageDraw

    for path in paths:
        im = Image.open(path)
        a = np.asarray(im.convert("L")).astype(float)
        h, w = a.shape
        print(f"{path.name}: {w} x {h}")
        est = {}
        for axis, label, size in ((0, "x", w), (1, "y", h)):
            period, offset, strength = _period(a.mean(axis=axis))
            est[label] = (period, offset)
            confidence = "clear" if strength > 0.3 else "WEAK: painted/gridless? use filename NxM or credits"
            print(f"  {label}: ~{period:.2f} px/square, offset {offset} px, "
                  f"{size / period:.2f} squares (signal {strength:.2f}, {confidence})")
        if preview:
            preview.mkdir(parents=True, exist_ok=True)
            ov = im.convert("RGB")
            dr = ImageDraw.Draw(ov)
            (px, ox), (py, oy) = est["x"], est["y"]
            x = ox
            while x < w:
                dr.line([(round(x), 0), (round(x), h)], fill=(255, 0, 0), width=1)
                x += px
            y = oy
            while y < h:
                dr.line([(0, round(y)), (w, round(y))], fill=(255, 0, 0), width=1)
                y += py
            dst = preview / f"{path.stem}.grid-preview.png"
            ov.save(dst)
            print(f"  preview: {dst}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "text":
        text(Path(args[1]), Path(args[2]) if len(args) > 2 else None)
    elif len(args) == 3 and args[0] == "images":
        images(Path(args[1]), Path(args[2]))
    elif len(args) >= 2 and args[0] == "grid":
        rest, prev = args[1:], None
        if rest[0] == "--preview":
            prev, rest = Path(rest[1]), rest[2:]
        grid([Path(p) for p in rest], prev)
    else:
        sys.exit(__doc__)
