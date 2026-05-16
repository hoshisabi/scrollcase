#!/usr/bin/env python3
"""Generate images for campaign wiki pages from frontmatter image_prompt fields.

Each markdown file may have an image_prompt in its frontmatter — either a string
(single image) or a list (multiple images, e.g. achievements). Output images are
written to an images/ subdirectory next to the markdown file, skipping any that
already exist.

Usage:
    uv run python generate_artwork.py public/npcs/clod.md
    uv run python generate_artwork.py --scan npcs
    uv run python generate_artwork.py --scan locations
    uv run python generate_artwork.py --scan characters
"""
import os
import time
import argparse
import pathlib
import yaml
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from google import genai
from google.genai import types

CAMPAIGN_DIR = (pathlib.Path(__file__).parent / os.environ["CAMPAIGN_DIR"]).resolve()

SCAN_DIRS = {
    "characters": CAMPAIGN_DIR / "public" / "characters",
    "npcs":       CAMPAIGN_DIR / "public" / "npcs",
    "locations":  CAMPAIGN_DIR / "public" / "locations",
    "sessions":   CAMPAIGN_DIR / "public" / "sessions",
}


def parse_frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    try:
        end = text.index("---", 3)
    except ValueError:
        return {}
    return yaml.safe_load(text[3:end]) or {}


def output_paths(md_path: pathlib.Path, count: int) -> list[pathlib.Path]:
    images_dir = md_path.parent / "images"
    stem = md_path.stem
    if count == 1:
        return [images_dir / f"{stem}.png"]
    return [images_dir / f"{stem}-{i + 1}.png" for i in range(count)]


def generate_one(client, prompt: str, out_path: pathlib.Path, model: str, force: bool = False) -> bool:
    """Generate a single image. Returns True if generated, False if skipped."""
    if out_path.exists() and not force:
        print(f"  skip (exists): {out_path.name}")
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  generating: {out_path.name}")
    print(f"  prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")

    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1),
    )
    response.generated_images[0].image.save(out_path)
    print(f"  saved: {out_path}")
    return True


def process_file(md_path: pathlib.Path, client, model: str, delay: float, force: bool = False) -> int:
    """Process one markdown file. Returns number of images generated."""
    fm = parse_frontmatter(md_path)
    raw = fm.get("image_prompt")
    if not raw:
        return 0

    prompts = raw if isinstance(raw, list) else [raw]
    paths = output_paths(md_path, len(prompts))

    print(f"\n{md_path.relative_to(CAMPAIGN_DIR)}  ({len(prompts)} prompt(s))")

    generated = 0
    for i, (prompt, out_path) in enumerate(zip(prompts, paths)):
        if i > 0:
            time.sleep(delay)
        if generate_one(client, prompt, out_path, model, force=force):
            generated += 1

    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate wiki artwork from frontmatter image_prompt fields")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="Markdown file(s) to process")
    parser.add_argument("--scan", choices=SCAN_DIRS.keys(), metavar="TYPE",
                        help=f"Scan all .md files in a wiki directory ({', '.join(SCAN_DIRS)})")
    parser.add_argument("--model", default="imagen-4.0-fast-generate-001",
                        help="Imagen model to use")
    parser.add_argument("--delay", type=float, default=6.0,
                        help="Seconds between API requests (default: 6)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing images")
    args = parser.parse_args()

    if not args.files and not args.scan:
        parser.error("Provide at least one FILE or use --scan TYPE")

    md_files: list[pathlib.Path] = []
    if args.scan:
        md_files.extend(sorted(SCAN_DIRS[args.scan].glob("*.md")))
    for f in args.files:
        p = pathlib.Path(f)
        if not p.is_absolute():
            p = CAMPAIGN_DIR / p
        md_files.append(p.resolve())

    client = genai.Client(api_key=os.environ["GOOGLE_KEY"])

    total = 0
    for md_path in md_files:
        total += process_file(md_path, client, args.model, args.delay, force=args.force)

    print(f"\nDone. {total} image(s) generated.")


if __name__ == "__main__":
    main()
